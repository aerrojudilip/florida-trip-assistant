# RAG Knowledge Assistant

A Streamlit app that builds a personal knowledge base from **YouTube videos** and
**website articles**, then answers questions grounded in that content using a
Retrieval-Augmented Generation (RAG) pipeline — with source citations.

## 1. Architecture

```
┌─────────────────────────────── Streamlit UI ───────────────────────────────┐
│  app.py (Home + provider config)                                           │
│  pages/1_Add_Sources.py   pages/2_Ask_Questions.py   pages/3_View_Sources.py│
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
- **yt-dlp + youtube-transcript-api** — yt-dlp pulls rich metadata (title, channel, duration, chapters); youtube-transcript-api pulls the actual transcript text. Both support routing through a proxy, which matters because YouTube sometimes rate-limits or blocks a host's IP outright (the library raises `IpBlocked`/`RequestBlocked` in that case — common on free cloud hosts, see [Limitations](#9-limitations-of-the-free-deployment)).
- **trafilatura** — purpose-built boilerplate/ad/nav removal for web articles (much cleaner than a hand-rolled BeautifulSoup scraper), with a BeautifulSoup fallback if it comes back empty.
- **cloudscraper** — many sites sit behind a Cloudflare-style bot challenge that blocks plain `requests` calls with a 403 even with realistic browser headers. cloudscraper solves that challenge (the same thing your browser's JS already does) so ordinary public articles you can view yourself still get scraped automatically.
- **Paste Content fallback** — for the smaller set of sites protected by something cloudscraper can't solve (CAPTCHA-gated, advanced bot management), the app lets you paste content you've already opened in your own browser — it's indexed through the exact same chunk→embed→store pipeline as a scraped page.

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
├── app.py                          # Home page + sidebar provider/model config
├── pages/
│   ├── 1_Add_Sources.py            # Submit YouTube/website links or paste content
│   ├── 2_Ask_Questions.py          # Chat interface over the knowledge base
│   └── 3_View_Sources.py           # List + delete indexed sources
├── core/
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
├── .env.example
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

Copy `.env.example` to `.env` and fill in at least one LLM provider's key:

```
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

DEFAULT_LLM_PROVIDER=openai          # or gemini
DEFAULT_EMBEDDING_PROVIDER=openai    # or gemini

# Optional — only needed if YouTube blocks your host's IP (common on free cloud hosts)
YT_PROXY_URL=http://user:pass@proxy-host:port
```

You only need the key(s) for the provider(s) you plan to use. The sidebar shows a ✅/❌
status for each provider so you can tell at a glance whether a key is configured.

## 7. Steps to run locally

```bash
# 1. Create a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
copy .env.example .env         # Windows
# cp .env.example .env         # macOS/Linux
# then edit .env with your API keys

# 4. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`. Go to **Add Sources** to add a YouTube link or
website URL, then **Ask Questions** to query your knowledge base.

## 8. Steps to deploy on a free hosting platform

**Recommended: Streamlit Community Cloud** (share.streamlit.io) — built for exactly this
kind of app, free tier, deploys directly from a GitHub repo.

1. Push this project to a **public** (or private, on your own GitHub account) GitHub repo. Make sure `.env` and `data/` are NOT committed (already in `.gitignore`).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **New app**, select your repo/branch, and set the main file path to `app.py`.
4. Before deploying (or after, in **App settings → Secrets**), paste your secrets in TOML format — this is the cloud equivalent of your `.env` file:
   ```toml
   OPENAI_API_KEY = "sk-..."
   GOOGLE_API_KEY = "..."
   DEFAULT_LLM_PROVIDER = "openai"
   DEFAULT_EMBEDDING_PROVIDER = "openai"
   YT_PROXY_URL = "http://user:pass@proxy-host:port"
   ```
   (`core/config.py`'s `get_api_key` checks `st.secrets` automatically, no code changes needed.)
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
- **YouTube blocks datacenter IPs.** Cloud hosts share IP ranges YouTube actively blocks
  for both `yt-dlp` metadata scraping and transcript fetches, so ingestion that works
  locally can fail once deployed. This app supports routing both through a proxy via
  `YT_PROXY_URL` (e.g. a residential proxy from a provider like Webshare) — set it before
  relying on YouTube ingestion in production.
- **App sleeps on inactivity.** Streamlit Community Cloud apps go to sleep after ~a
  few days with no traffic and take ~30-60s to wake on the next visit.
- **Resource limits.** Free tier caps CPU/RAM (roughly 1 vCPU / 1 GB) and concurrent
  users. Large ingested sources or many simultaneous questions can be slow or OOM.
- **No built-in auth.** Anyone with the URL can add sources, ask questions, and consume
  your API quota/spend. Keep the URL private or add auth (see improvements below) before
  sharing broadly.
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
