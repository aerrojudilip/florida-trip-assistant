from __future__ import annotations

import re
from datetime import datetime, timezone

import yt_dlp
from youtube_transcript_api import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)

from core.config import get_youtube_cookie_options, get_youtube_proxy_config, get_youtube_proxy_url
from core.exceptions import EmptyContentError, InvalidLinkError, TranscriptUnavailableError

YOUTUBE_ID_PATTERNS = [
    r"(?:v=|/videos/|embed/|youtu\.be/|/v/|/e/|watch\?v=)([A-Za-z0-9_-]{11})",
]


def extract_video_id(url: str) -> str:
    for pattern in YOUTUBE_ID_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise InvalidLinkError(f"Could not find a YouTube video ID in: {url}")


def format_duration(seconds: int | None) -> str | None:
    if not seconds:
        return None
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_timestamp(seconds: float | None) -> str:
    return format_duration(int(seconds or 0)) or "0:00"


def fetch_video_metadata(video_id: str) -> dict:
    """Fetch title, channel, duration, publish date, and chapters via yt-dlp.

    yt-dlp scrapes the same YouTube pages a browser would, which is more resilient
    and far richer than the lightweight oEmbed endpoint (adds channel/duration/chapters).
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    proxy_url = get_youtube_proxy_url()
    if proxy_url:
        ydl_opts["proxy"] = proxy_url
    ydl_opts.update(get_youtube_cookie_options())

    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(watch_url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        message = str(exc)
        if "Sign in to confirm" in message or "not a bot" in message:
            raise InvalidLinkError(
                f"YouTube is requiring sign-in verification for video {video_id}. Set "
                f"YT_COOKIES_FILE (a cookies.txt exported from a logged-in browser) or, "
                f"for local runs, YT_COOKIES_FROM_BROWSER (e.g. 'chrome') and retry."
            ) from exc
        raise InvalidLinkError(f"Could not fetch metadata for video {video_id}: {exc}") from exc

    upload_date = info.get("upload_date")
    if upload_date and len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"

    chapters = [
        {"title": chapter.get("title", "Untitled"), "start_time": chapter.get("start_time", 0)}
        for chapter in (info.get("chapters") or [])
    ]

    return {
        "title": info.get("title") or video_id,
        "channel": info.get("uploader") or info.get("channel"),
        "duration": format_duration(info.get("duration")),
        "upload_date": upload_date,
        "chapters": chapters,
    }


def fetch_transcript(video_id: str) -> str:
    # A proxy (see get_youtube_proxy_config) is optional but useful on hosts YouTube has
    # rate-limited or blocked — the library raises IpBlocked/RequestBlocked in that case.
    api = YouTubeTranscriptApi(proxy_config=get_youtube_proxy_config())
    try:
        transcript = api.fetch(video_id)
    except TranscriptsDisabled as exc:
        raise TranscriptUnavailableError(f"Transcripts are disabled for video {video_id}.") from exc
    except NoTranscriptFound as exc:
        raise TranscriptUnavailableError(f"No transcript found for video {video_id}.") from exc
    except VideoUnavailable as exc:
        raise InvalidLinkError(f"Video {video_id} is unavailable.") from exc
    except (IpBlocked, RequestBlocked) as exc:
        raise TranscriptUnavailableError(
            f"YouTube blocked the transcript request for {video_id} (this host's IP is "
            f"rate-limited/blocked). Set YT_PROXY_URL to a working proxy and retry."
        ) from exc
    except Exception as exc:  # noqa: BLE001 - surface any other API failure clearly
        raise TranscriptUnavailableError(f"Failed to fetch transcript for {video_id}: {exc}") from exc

    return " ".join(snippet.text.strip() for snippet in transcript.snippets if snippet.text.strip())


def clean_transcript(text: str, sentences_per_paragraph: int = 5) -> str:
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    sentences = re.split(r"(?<=[.!?])\s+", text)
    paragraphs = [
        " ".join(sentences[i : i + sentences_per_paragraph])
        for i in range(0, len(sentences), sentences_per_paragraph)
    ]
    return "\n\n".join(p for p in paragraphs if p)


def ingest_youtube(url: str) -> dict:
    video_id = extract_video_id(url)
    metadata = fetch_video_metadata(video_id)
    raw_transcript = fetch_transcript(video_id)
    cleaned = clean_transcript(raw_transcript)

    if not cleaned:
        raise EmptyContentError(f"Transcript for {url} was empty after cleaning.")

    title = metadata["title"]
    header_lines = [f"# {title}", "", f"Source: {url}"]
    if metadata.get("channel"):
        header_lines.append(f"Channel: {metadata['channel']}")
    if metadata.get("duration"):
        header_lines.append(f"Duration: {metadata['duration']}")
    if metadata.get("upload_date"):
        header_lines.append(f"Published: {metadata['upload_date']}")
    header_lines.append(f"Retrieved: {datetime.now(timezone.utc).isoformat()}")

    sections = ["\n".join(header_lines)]

    if metadata.get("chapters"):
        chapter_lines = [
            f"- {format_timestamp(chapter['start_time'])} {chapter['title']}"
            for chapter in metadata["chapters"]
        ]
        sections.append("## Chapters\n\n" + "\n".join(chapter_lines))

    sections.append(f"## Transcript\n\n{cleaned}")

    markdown = "\n\n".join(sections) + "\n"

    return {
        "title": title,
        "source_url": url,
        "source_type": "youtube",
        "content": markdown,
    }
