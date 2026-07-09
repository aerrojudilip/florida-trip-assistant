# RAG Knowledge Assistant

A Streamlit app that builds a personal knowledge base from **YouTube videos** and
**website articles**, then answers questions grounded in that content using a
Retrieval-Augmented Generation (RAG) pipeline — with source citations.

## 1. Architecture

```
┌─────────────────────────────── Streamlit UI ───────────────────────────────┐
│  app.py (st.navigation — picks the page list below by auth state)          │
│  🔒 Admin (needs APP_PASSWORD): Home · Add Sources · View Sources          │
│  🌐 Public: Ask Questions                                                  │
└──────────────┬───────────────────────┬──────────────────────┬──────────────┘
               │                       │                      │
               ▼                       ▼                      ▼
     core/ingestion/*        core/rag/pipeline.py     core/metadata/store.py
   (YouTube / website              (orchestrates            (JSON file:
    → cleaned Markdown)         chunk→embed→store→          title, url, type,
                                  retrieve→answer)           file path, date)
               │                       │
               ▼                       ▼
     data/markdown/*.md      core/rag/{chunking,embeddings,vector_store,llm}.py
      (knowledge files)                │
                                        ▼
                              data/chroma_db/ (ChromaDB
                               persistent vector store)
                                        │
                                        ▼
                          OpenAI or Gemini (embeddings + LLM,
                           selected in the sidebar)
```

**Why these choices:**
- **Streamlit** — one Python codebase gives you the UI, no separate frontend, and deploys for free on Streamlit Community Cloud.
- **LangChain** — standardizes the embeddings/LLM/vector-store interfaces so swapping OpenAI ↔ Gemini is a one-line change.
- **ChromaDB** — an embedded, file-based vector database. No server to run or pay for.
- **yt-dlp (primary) + youtube-transcript-api (fallback)** for YouTube — yt-dlp pulls rich metadata (title, channel, duration, chapters) *and* is now the primary transcript source too: it downloads the actual caption track (human-written if available, else auto-generated) and we parse the VTT into plain text. This matters because `youtube-transcript-api`'s cookie support is currently disabled upstream, so once YouTube starts showing "sign in to confirm you're not a bot" or blocking a host's IP for transcript requests (`IpBlocked`/`RequestBlocked` — happens on home IPs too, not just cloud hosts), that library has no way past it, while yt-dlp does via `YT_COOKIES_FILE`/`YT_COOKIES_FROM_BROWSER`. `youtube-transcript-api` (with optional proxy) only kicks in if a video has no captions at all. See [Limitations](#9-limitations-of-the-free-deployment).
- **trafilatura** — purpose-built boilerplate/ad/nav removal for web articles (much cleaner than a hand-rolled BeautifulSoup scraper), with a BeautifulSoup fallback if it comes back empty.
- **cloudscraper** — many sites sit behind a Cloudflare-style bot challenge that blocks plain `requests` calls with a 403 even with realistic browser headers. cloudscraper solves that challenge (the same thing your browser's JS already does) so ordinary public articles you can view yourself still get scraped automatically.
- **Paste Content fallback** — for the smaller set of sites protected by something cloudscraper can't solve (CAPTCHA-gated, advanced bot management), the app lets you paste content you've already opened in your own browser — it's indexed through the exact same chunk→embed→store pipeline as a scraped page.
- **Password-gated admin pages** — Home, Add Sources, and View Sources require `APP_PASSWORD`; Ask Questions stays public. Built with `st.navigation`/`st.Page` so the gated pages aren't just content-blocked, they're not even listed in the sidebar until you log in (see `core/auth.py`).

## 2. RAG workflow explanation

**Ingestion (Add Sources page):**
1. User submits a YouTube URL, a website URL, or pastes content manually (for sites that block scraping).
2. `core/ingestion/youtube_ingest.py`, `web_ingest.py`, or `manual_ingest.py` extracts and cleans the content.
3. `core/ingestion/markdown_writer.py` writes it to `data/markdown/<slug>-<id>.md`.
4. `core/metadata/store.py` records title, source URL, type, file path, and date added in `data/metadata.json`.
5. `core/rag/chunking.py` splits the Markdown into ~1000-character overlapping chunks.
6. `core/rag/embeddings.py` embeds each chunk (OpenAI or Gemini, per your sidebar config).
7. `core/rag/vector_store.py` stores the embeddings + chunk text + metadata (`source_id`, `title`, `source_url`, `file_path`) in ChromaDB.

**Question answering (Ask Questions page):**
1. User asks a question.
2. The question is embedded with the same provider used for ingestion.
3. ChromaDB similarity search returns the top-k most relevant chunks.
4. Those chunks are concatenated into a context block and sent to the selected LLM (OpenAI or Gemini) along with the question, in a prompt that instructs the model to answer **only** from the given context and to say so if it can't.
5. The answer is shown along with a de-duplicated list of source links/filenames pulled from the retrieved chunks' metadata.

## 3. Folder structure

```
DW_1/
├── app.py                          # Entry point: st.navigation picks the page list by auth state
├── app_pages/
│   ├── home.py                     # 🔒 Sidebar provider/model config + log out
│   ├── add_sources.py              # 🔒 Submit YouTube/website links or paste content
│   ├── ask_questions.py            # 🌐 Public chat interface over the knowledge base
│   ├── view_sources.py             # 🔒 List + delete indexed sources
│   └── admin_login.py              # Password entry (shown to unauthenticated visitors)
├── core/
│   ├── auth.py                     # Session-based password gate (compares against APP_PASSWORD)
│   ├── config.py                   # Env vars, provider/model registry, app config persistence
│   ├── exceptions.py                # Custom error types
│   ├── ingestion/
│   │   ├── youtube_ingest.py       # yt-dlp metadata + transcript extraction/cleaning
│   │   ├── web_ingest.py           # HTML fetch + readability extraction (trafilatura)
│   │   ├── manual_ingest.py        # Fallback: user-pasted content for blocked sites
│   │   └── markdown_writer.py      # Slugified filename + Markdown file writer
│   ├── metadata/
│   │   └── store.py                # JSON-backed source metadata store
│   └── rag/
│       ├── chunking.py             # Markdown → overlapping text chunks
│       ├── embeddings.py           # OpenAI / Gemini embedding function factory
│       ├── vector_store.py         # Chroma persistent store: add/search/delete
│       ├── llm.py                  # OpenAI / Gemini chat model factory
│       └── pipeline.py             # Orchestrates ingest_source / answer_question / delete_source
├── data/                            # Created at runtime (gitignored)
│   ├── markdown/                   # Extracted knowledge as .md files
│   ├── chroma_db/                  # Persistent vector store
│   ├── metadata.json               # Source metadata
│   └── app_config.json             # Saved LLM/embedding provider choice
├── .streamlit/
│   ├── config.toml                 # Theme
│   └── secrets.toml.example        # Template for cloud secrets
├── requirements.txt
├── setEnv.env.example               # Template — copy to setEnv.env and fill in real values
└── .gitignore
```

## 4. Required Python libraries

See [requirements.txt](requirements.txt):

```
streamlit, langchain, langchain-core, langchain-text-splitters,
langchain-openai, langchain-google-genai, langchain-chroma, chromadb,
youtube-transcript-api, yt-dlp, trafilatura, cloudscraper, beautifulsoup4, requests, python-dotenv
```

## 5. Full working code

All code lives in this repo under `app.py`, `pages/`, and `core/` (listed above) — every file
is complete and runnable, not a snippet. Key entry points to read first if you want to
understand the system: [core/rag/pipeline.py](core/rag/pipeline.py) (the orchestration logic)
and [core/config.py](core/config.py) (provider/model configuration).

## 6. Environment variable setup

Copy `setEnv.env.example` to `setEnv.env` and fill in at least one LLM provider's key
(this is the file `core/config.py` loads locally — see `load_dotenv(BASE_DIR / "setEnv.env")`;
a legacy `.env` is still loaded as a fallback if you have one from before):

```
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

DEFAULT_LLM_PROVIDER=openai          # or gemini
DEFAULT_EMBEDDING_PROVIDER=openai    # or gemini

# Optional — fixes "Sign in to confirm you're not a bot" and, as a side effect, most
# transcript-blocked errors too (yt-dlp's own caption fetch is tried before the proxy
# path below). Use a throwaway Google account, not your main one:
YT_COOKIES_FILE=path/to/cookies.txt
# Or, for local runs only, with the browser CLOSED (an open browser locks its cookie db):
# YT_COOKIES_FROM_BROWSER=firefox

# Optional — only relevant for videos with no captions at all, where youtube-transcript-api
# is used instead of yt-dlp. Proxies rarely help here in practice (see README limitations) —
# only a genuine rotating residential pool works, not free/trial/static proxy tiers:
# WEBSHARE_PROXY_USERNAME=your-webshare-username
# WEBSHARE_PROXY_PASSWORD=your-webshare-password
# YT_PROXY_URL=http://user:pass@proxy-host:port

# Required to unlock Home, Add Sources, and View Sources (Ask Questions stays public)
APP_PASSWORD=choose-a-real-secret-here
```

You only need the key(s) for the provider(s) you plan to use. The sidebar shows a ✅/❌
status for each provider so you can tell at a glance whether a key is configured.
`setEnv.env` is gitignored — never commit it.

## 7. Steps to run locally

```bash
# 1. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
copy setEnv.env.example setEnv.env   # Windows
# cp setEnv.env.example setEnv.env   # macOS/Linux
# then edit setEnv.env with your API keys and a real APP_PASSWORD

# 4. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`. Only **Ask Questions** and **Admin Login** are
visible at first — enter your `APP_PASSWORD` on the Admin Login page to reveal **Home**,
**Add Sources**, and **View Sources** in the sidebar.

## 8. Steps to deploy on a free hosting platform

**Recommended: Streamlit Community Cloud** (share.streamlit.io) — built for exactly this
kind of app, free tier, deploys directly from a GitHub repo.

1. Push this project to a **public** (or private, on your own GitHub account) GitHub repo. Make sure `setEnv.env`/`.env` are NOT committed (already in `.gitignore`); `data/` is fine to commit if you want the deploy to start pre-loaded with your local knowledge base.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **New app**, select your repo/branch, and set the main file path to `app.py`.
4. Before deploying (or after, in **App settings → Secrets**), paste your secrets in TOML format — this is the cloud equivalent of `setEnv.env`:
   ```toml
   OPENAI_API_KEY = "sk-..."
   GOOGLE_API_KEY = "..."
   DEFAULT_LLM_PROVIDER = "openai"
   DEFAULT_EMBEDDING_PROVIDER = "openai"
   APP_PASSWORD = "choose-a-real-secret-here"
   ```
   (`core/config.py`'s `get_api_key`/`get_app_password` check `st.secrets` automatically, no code changes needed.) `YT_COOKIES_FROM_BROWSER` won't work here — there's no browser on a cloud host. If YouTube ingestion needs cookies on the deployed app, you'd need to get a `cookies.txt`'s contents into a file the app can read (e.g. commit it privately or write it from a secret at startup) — think carefully before putting a personal Google account's session cookies in a shared/deployed app.
5. Click **Deploy**. The first build installs `requirements.txt` and takes a few minutes.
6. Your app is live at `https://<your-app-name>.streamlit.app`.

**Alternative: Hugging Face Spaces** (huggingface.co/spaces) — also free, supports
Streamlit natively (choose the "Streamlit" SDK when creating a Space), and secrets are
set under **Settings → Repository secrets**. Useful if you want a longer-lived container
than Streamlit Cloud's sleep-on-inactivity behavior, though storage is equally ephemeral.

## 9. Limitations of the free deployment

- **Ephemeral storage.** Streamlit Community Cloud (and HF Spaces free tier) do not
  guarantee persistent disk. `data/markdown`, `data/chroma_db`, and `metadata.json` can be
  wiped on redeploy, restart after inactivity, or container recycling. Treat the hosted
  app as a demo, not a durable knowledge store — re-add your sources after a reset, or
  see improvement #2 below for a permanent fix.
- **YouTube anti-bot measures.** Two independent checks can block YouTube ingestion:
  - **"Sign in to confirm you're not a bot"** — hits `yt-dlp`'s metadata/subtitle fetch.
    Fix with `YT_COOKIES_FILE` (path to a cookies.txt exported from a logged-in browser —
    works on cloud hosts too) or `YT_COOKIES_FROM_BROWSER` (browser name; local runs only,
    since there's no browser to read from on a headless host, and the browser must be
    **closed** — an open Chrome/Edge locks its cookie database and yt-dlp can't read it).
    Use a throwaway/secondary Google account, not your main one — automated requests
    carry a small risk of the account being flagged.
  - **`IpBlocked`/`RequestBlocked`** on `youtube-transcript-api` — this only matters if a
    video has *no* captions at all (yt-dlp's own caption download is tried first and
    doesn't hit this). Proxies are a weak fix here: we tested 10 static datacenter
    proxies and a Bright Data zone, and YouTube/Bright Data blocked every one — only a
    genuine rotating **residential** proxy pool works, and even Bright Data gates YouTube
    access behind a KYC process. `WEBSHARE_PROXY_USERNAME`/`PASSWORD` or `YT_PROXY_URL`
    are wired up if you have working residential proxy credentials, but don't count on a
    free/trial proxy tier to solve this.
- **App sleeps on inactivity.** Streamlit Community Cloud apps go to sleep after ~a
  few days with no traffic and take ~30-60s to wake on the next visit.
- **Resource limits.** Free tier caps CPU/RAM (roughly 1 vCPU / 1 GB) and concurrent
  users. Large ingested sources or many simultaneous questions can be slow or OOM.
- **Lightweight auth only.** `APP_PASSWORD` gates Home/Add Sources/View Sources behind a
  single shared password stored in `st.session_state` — fine for keeping casual visitors
  out of admin functions, but it's not per-user auth, has no rate limiting or lockout, and
  Ask Questions itself is intentionally public (so anyone with the URL can query the
  knowledge base and consume your LLM API quota). For real multi-user auth, see
  improvements below.
- **Single-writer JSON metadata store.** Fine for one user; concurrent writers could race.

## 10. Suggestions to improve the app later

- **User login** — add `streamlit-authenticator` or a proper OAuth flow so each user has
  their own sources/history, and to stop anonymous visitors from burning your API quota.
- **Persistent cloud storage** — swap local ChromaDB + JSON metadata for a hosted vector
  DB (e.g. free tiers of Qdrant Cloud, Pinecone, or Supabase's `pgvector`) and a small
  Postgres/SQLite-on-Turso metadata table, so content survives redeploys.
- **Document upload** — extend `core/ingestion/` with a PDF/DOCX/TXT ingester (e.g.
  `pypdf`, `python-docx`) reusing the same chunk→embed→store pipeline.
- **Chat history persistence** — currently chat history lives only in
  `st.session_state` (lost on refresh); persist it per-user alongside the metadata store.
- **Streaming answers** — swap `llm.invoke()` for `llm.stream()` in `pipeline.py` and
  render tokens incrementally in the Ask Questions page for a snappier feel.
- **Re-ingest / refresh a source** — currently a URL must be deleted before re-adding;
  add an explicit "refresh" action that re-scrapes and re-embeds in place.
- **Hybrid/reranked retrieval** — add a keyword (BM25) pass alongside vector search, or
  a reranker, for better recall on short or keyword-heavy questions.

## Attribution

The proxy-based YouTube ingestion technique (to work around YouTube blocking datacenter
IPs on cloud hosts) and the use of `yt-dlp` for richer video metadata were inspired by
[ZeroXClem/Youtube-to-Markdown](https://github.com/ZeroXClem/Youtube-to-Markdown) (MIT
licensed).
