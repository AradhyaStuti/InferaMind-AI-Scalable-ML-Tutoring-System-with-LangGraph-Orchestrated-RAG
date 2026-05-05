# RouteLM

LLM-based course assistant that routes questions before doing RAG. Instead of running retrieval on every input, a small classifier picks one of three paths: answer with sources, answer from the model's own knowledge, or just refuse. The LLM (Groq) and the embedder (Ollama) are hosted. Everything else (routing, retrieval, multi-corpus indexing, eval, reliability stuff, the React UI) I built myself.

Demo login: username `demo`, password set via `DEMO_USER_PASSWORD` (auto-seeded when `SEED_DEMO_USER=true`).

![Demo](docs/demo.gif)

## Why

I'd been using a few RAG-based course chatbots and they all had the same problem. Ask anything off-topic and they'd cheerfully return five "Sources" attached to a non-answer. The retrieval step had no idea whether the question even belonged in the corpus.

So three things kept happening:

1. Off-topic questions got fake citations. Retrieval returns *something* for any query, the LLM is told "answer from these", and you get a fluent answer pinned to chunks that have nothing to do with the question.
2. Things that *were* in scope but not in the corpus would either get refused, or the LLM would just answer from its priors anyway. No signal to the user that the citations were decorative.
3. With multiple courses, everything got dumped into one big bag of chunks, so a LangGraph question would sometimes pull noise from a finance dataset because the embedding neighbourhood was crowded.

The fix here is making routing a real first step, not a filter bolted on afterwards. Before any retrieval happens, a classifier picks between `course_related` (RAG), `course_related_general` (LLM-only), and `off_topic` (refuse). It's per-corpus, so when I added more courses they each got their own thresholds rather than fighting over a shared one.

The implementation is honestly not exciting. No agents, no fancy vector DB, no custom inference. Hosted LLM, hosted embeddings, FAISS, a LangGraph router, an LLM call wrapped in a circuit breaker. The work is in the architecture, not the model layer.

## What it covers

Three corpora, 350 chunks total:

| Course | Chunks | Topics |
|---|---|---|
| Andrew Ng - ML Specialization (Course 1) | 273 | supervised/unsupervised, regression, gradient descent, neural networks |
| GenAI, RAG & the LangChain stack | 37 | transformers, LLMs, RAG (theory + chunking + reranking + RAGAS), LangChain (LCEL, prompts, parsers, agents), LangGraph (state graphs, streaming, checkpoints), production stuff (observability, cost, reliability, safety) |
| Data Science with Python | 40 | Python, NumPy, pandas, matplotlib/seaborn, EDA, stats, scikit-learn, feature engineering, model evaluation, deployment |

The ML course is real Whisper transcripts of Andrew Ng's videos. The other two I wrote myself as study notes, and they double as the source for the assistant.

## How routing works

Each course in `data/courses.json` declares anchor phrases that describe what it covers. At startup these get embedded with `bge-m3`.

For each question:

1. Embed the question.
2. For each course, score = `max(cosine_sim(query, anchor) for anchor in course.anchors)`. Max over anchors, not centroid. That part matters and I'll explain why below.
3. Course with the highest score wins, and that score gets compared against that course's thresholds.

| score | path | example | result |
|---|---|---|---|
| `>= course_threshold` | `course_related` | "How do I use pandas groupby?" | filtered FAISS retrieval, grounded answer with citations |
| `>= general_threshold` | `course_related_general` | "Tell me about diffusion models" | no retrieval, LLM answers from its own knowledge with a "this isn't in my notes" preamble |
| `< general_threshold` | `off_topic` | "Who won the 2022 World Cup?" | fixed refusal message |

Defaults are around 0.58-0.60 / 0.50, calibrated for `bge-m3`. A different embedding model will need re-tuning.

## Architecture

![Architecture](docs/architecture.png)

```
React frontend
     ↓  (WebSocket / SSE)
FastAPI backend
     ↓
LangGraph (StateGraph)
   classify ─┬─> retrieve  ─┐
             ├─> direct     ├─> stream tokens (Groq / Ollama)
             └─> off_topic ─┘
     ↓
SQLite (auth + history)   ·   FAISS (350 chunks, 3 courses)
```

Each node is a Python function reading/writing a `TypedDict`. The conditional edge after `classify` is the whole point - it's why this is a graph and not a linear pipeline. Same compiled object handles all three paths without any `if/else` outside the router.

## Stuff I had to figure out

A few choices worth talking about.

Max-anchor instead of centroid. First version averaged all anchor embeddings into one centroid per course. Worked OK for the original ML course (19 anchors all about supervised learning) but completely fell apart when I added the GenAI course - 31 anchors spanning LLM internals, RAG, LangChain APIs, production concerns. The centroid landed in some meaningless midpoint and legit queries scored 0.48 alongside totally off-topic ones at 0.50. Switching to *max* over anchors fixed it. Real matches now hit 0.65-0.85, off-topic stays under 0.50, scores are clearly bimodal.

Per-course thresholds. Different corpora are differently "sharp". The ML course tolerates 0.60 fine. The GenAI corpus is broader and works better with 0.50 as the lower band. Forcing a single global threshold means one corpus is always compromising for the other.

WebSocket primary, SSE fallback. WS lets me push pipeline events (`classify -> retrieve -> generate`) on the same channel as the tokens, which is what powers the progress indicator in the UI. Some networks block WS upgrades though, so the client falls back to SSE. Both transports go through one `_prepare_turn` helper on the backend so I'm not maintaining two paths.

Circuit breaker. Three failures in a row opens the circuit for 30 seconds. Shared across the SSE handler, WS handler, and the title-generation thread, so if Groq goes down you don't get every request slowly timing out one by one. Half-open state lets one test request through after the cooldown.

Embeddings always Ollama, generation either. Generation needs to be fast and good, so Groq is the default. Embeddings need to be cheap and consistent across the routing layer and the corpus, so they always go through Ollama (`bge-m3`). If `GROQ_API_KEY` isn't set, generation falls back to Ollama too. Classifier never breaks.

## Stack

- Backend: FastAPI, Pydantic, SQLite (WAL mode)
- Frontend: React + Vite (built bundle is served by FastAPI in production)
- Orchestration: LangGraph (3-node conditional StateGraph)
- LLM: Groq (`llama-3.3-70b-versatile`) by default, Ollama (`llama3.2`) as fallback
- Embeddings: `bge-m3` via Ollama, indexed in FAISS
- Auth: JWT + bcrypt
- Streaming: WebSocket primary, SSE fallback
- Tests: pytest (36) + Vitest (7)
- CI/CD: Docker + GitHub Actions

## Reliability

- Circuit breaker on the LLM (3 fail -> 30s cooldown -> half-open)
- Retry with exponential backoff (2 attempts) on transient errors
- WS -> SSE fallback in the client
- Rate limits via slowapi: 5/min register, 10/min login, 20/min chat
- Title generation runs in a background thread so the first token isn't blocked

## Eval

`backend/rag/evaluation.py` has four RAGAS-style metrics implemented locally (no API):

- Context precision - fraction of retrieved chunks that are actually relevant
- Context recall - fraction of the ground-truth answer that's covered by the retrieved chunks
- Faithfulness - fraction of answer sentences supported by the retrieved context
- Answer relevancy - cosine similarity between question and answer embeddings

Each in `[0, 1]`, plus a `ragas_score` aggregate. Quick run on a real query:

```
Q: "What is linear regression?"
{ context_precision: 1.0, faithfulness: 1.0, answer_relevancy: 0.637, ragas_score: 0.879 }
```

Mostly useful for catching regressions when I change prompts or thresholds.

## Results

18 hand-picked queries across all four expected categories:

| Category | Queries | Correctly classified | Notes |
|---|---|---|---|
| ML Course 1 | 3 | 3 / 3 | gradient descent, supervised learning, overfitting |
| GenAI / RAG | 4 | 4 / 4 | RAG, self-attention, LangGraph, RAG eval |
| DS / Python | 8 | 8 / 8 | groupby, broadcasting, train_test_split, missing data, pipelines, RF vs XGBoost, encoding, precision/recall |
| Off-topic | 3 | 3 / 3 | World Cup, baking, capital of France |
| Total | 18 | 18 / 18 | |

Live end-to-end with real Groq inference:

| Query | Course | Sources | Gen time | Outcome |
|---|---|---|---|---|
| "How do I use pandas groupby and what are common aggregations?" | ds-python-libraries | 5 | 1.77 s | grounded answer, syntax example |
| "What is RAG and why use it?" | genai-rag-langchain | 5 | 1.25 s | grounded answer, lists 3 problems it solves |
| "What is gradient descent?" | ml-andrew-ng-c1 | 5 | 1.07 s | LLM noted gaps in retrieved excerpts honestly |

Tests: 36 backend, 7 frontend, all passing. ESLint clean.

## Plain RAG vs RouteLM

The whole pitch of the routing layer is that plain RAG misbehaves on off-topic input. Easy claim to make, I wanted to actually verify it.

Ran [`scripts/compare_baseline.py`](scripts/compare_baseline.py) on 10 queries (4 on-topic, 6 deliberately off-topic) through two paths against the same Groq model (`llama-3.3-70b-versatile`):

- Plain RAG: top-5 retrieval over the full 350-chunk index (no course filter), straight into the same RAG prompt RouteLM uses. No router, no refusal logic.
- RouteLM: full pipeline, classify then either course-filtered retrieve, direct LLM, or canned refusal.

Raw output: [`eval/baseline_comparison.json`](eval/baseline_comparison.json). Headline numbers:

| Metric | Plain RAG | RouteLM |
|---|---|---|
| Off-topic queries that returned source citations | 6 / 6 | 0 / 6 |
| Off-topic queries that triggered an LLM call | 6 / 6 | 0 / 6 |
| Off-topic "leak rate" (>200 chars + citations) | 100% | 0% |
| On-topic queries answered substantively | 4 / 4 | 4 / 4 |
| Avg latency on off-topic | ~1.1 s | ~0.48 s |

On-topic queries: tied, both work. The whole gap is on the off-topic side.

Few things I noticed reading the actual outputs:

- Groq's `llama-3.3-70b` is well-aligned, so it doesn't fully hallucinate on off-topic queries. It says stuff like "the retrieved excerpts don't cover the 2022 World Cup, they appear to be about machine learning..." which is honest, but it's still 400-900 chars of LLM output explaining what it can't help with. RouteLM returns a single fixed 202-char refusal in <500ms with no LLM call at all.
- Plain RAG always returns 5 source chunks even for off-topic. The UI would render those as "Sources: 5 chunks" attached to the non-answer. That's the bad kind of leak because at a glance it looks grounded.
- Plain RAG also burns the full retrieval + LLM call on every off-topic question. RouteLM short-circuits at the router. Across 6 off-topic queries that's roughly 3.6s of wasted Groq compute and 30 wasted FAISS lookups.

Catching off-topic at the router is just the cheapest place to do it.

To re-run:

```bash
python scripts/compare_baseline.py
```

## Limitations

Stuff I didn't get to.

- The classifier is just a max-anchor scorer, not a trained model. It's fast and predictable but it'll get edge cases wrong. A small LLM-based classifier or a learned encoder fine-tuned on routing decisions would do better, at the cost of a heavier startup.
- No reranking. Retrieval is single-stage bi-encoder. A cross-encoder reranker (BGE-Reranker probably) on top 20 -> top 5 would help faithfulness for the GenAI/DS corpora where chunks are longer.
- No hybrid search. Pure dense. For exact API-name matches like `pd.merge` or `LangGraph.compile`, BM25 fused with the dense scores would help.
- Corpus is hardcoded as JSON files. Re-ingestion is a script, not a live operation. A real product would need an admin endpoint that lets you upload + re-embed without restarting.
- No course selector in the UI. Routing is fully automatic, which is fine most of the time but ambiguous queries that span multiple courses don't have an override option.
- No fine-tuning. All behaviour is from prompts + routing + retrieval. A fine-tuned tutor would probably improve answer quality but for a one-person project the effort isn't worth it yet.

## Setup

1. Pull the embedding model

```bash
ollama pull bge-m3
```

If you also want local generation:

```bash
ollama pull llama3.2
```

2. Backend deps

```bash
python -m venv venv
pip install -r requirements.txt
```

3. `.env` at the repo root, copy [.env.example](.env.example) and fill in:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_key
JWT_SECRET=your_long_random_string
```

`JWT_SECRET` is technically optional but sessions don't survive a restart without it.

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

4. Build the frontend

```bash
cd frontend
npm install
npm run build
```

5. Run

```bash
ollama serve                                   # terminal 1
python -m uvicorn backend.main:app --reload    # terminal 2
```

Open `http://localhost:8000`. FastAPI serves the React build from `frontend/dist`, so no separate frontend dev server unless you're actively working on the UI (then `npm run dev` in `frontend/`).

## Docker

```bash
docker compose up
```

Brings up Ollama + the app together. After first start: `docker compose exec ollama ollama pull bge-m3`. Compose treats `JWT_SECRET` as required.

## Deploy

[`render.yaml`](render.yaml) is a Render blueprint, apply from the dashboard or via `render blueprint launch`.

Set in the Render dashboard (not in repo):
- `GROQ_API_KEY`
- `DEMO_USER_PASSWORD` (for the seeded `demo` user)

`JWT_SECRET` is auto-generated by Render. With `SEED_DEMO_USER=true` the app idempotently creates a demo user on every boot so reviewers don't have to register.

One thing on plans: `bge-m3` needs around 1.5GB RAM, free tier doesn't fit. Standard ($7) is the floor; Pro ($25) gives breathing room. To run on the free tier you'd need to swap embeddings to a hosted provider (Cohere, Voyage), which is a small change in [`backend/rag/embeddings.py`](backend/rag/embeddings.py).

## Observability (optional)

Whole app is built on LangChain runnables, so [LangSmith](https://smith.langchain.com/) tracing works with two env vars:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=routelm
```

Every classify/retrieve/generate call shows up as a trace tree. Useful when debugging routing decisions or comparing latency.

## API

| | |
|---|---|
| `POST /api/auth/register` | create account, returns JWT |
| `POST /api/auth/login` | returns JWT |
| `POST /api/chat` | SSE stream: pipeline events + tokens |
| `WS   /api/chat/ws` | same stream over WS (client tries this first) |
| `GET/POST/PATCH/DELETE /api/conversations` | CRUD + rename |
| `GET /api/health` | status, chunk count, breaker state |

## Tests

```bash
pytest tests/             # backend, 36 tests
cd frontend && npm test   # frontend, 7 tests (Vitest)
```

Tests marked `@requires_embeddings` skip when Ollama isn't reachable or `embeddings.joblib` doesn't exist, so CI stays green without a model.

## Adding a new course

Pipeline is course-agnostic, three steps:

1. Register in `data/courses.json`:

```json
"my-course-id": {
  "name": "My Course",
  "short": "Mine",
  "course_threshold": 0.60,
  "general_threshold": 0.50,
  "anchors": ["topic one", "topic two", ...]
}
```

Anchors should be 10-30 phrases a student in that course would naturally use. They get embedded once at startup.

2. Drop the chunks into a JSON file shaped like `jsons.json`:

```json
{ "chunks": [
  {"number": "01", "title": "Module name", "start": 0, "end": 90, "text": "..."},
  ...
]}
```

3. Embed and merge:

```bash
cd data
python preprocess_json.py --course my-course-id --input my_chunks.json
```

By default this merges into the existing `embeddings.joblib`. Pass `--replace` to overwrite all rows for that course id (useful when re-ingesting). Restart picks it up.

Each retrieved chunk carries its `course_id` so the UI can show which course a citation came from.

## Layout

```
backend/
  main.py              FastAPI app + SPA serving
  config.py            env-driven settings
  rag/
    graph.py           LangGraph: classify → retrieve / direct / off_topic
    embeddings.py      FAISS + LRU cache
    generator.py       LLM, prompts, circuit breaker, streaming
    evaluation.py      RAGAS-style metrics
    courses.py         course registry loader
  routes/              chat (SSE + WS), auth, conversations
  auth/security.py     JWT + bcrypt
  db/store.py          SQLite store
frontend/
  src/api/client.js    WS-with-SSE-fallback chat client
  src/hooks/           useAuth, useChat, useKeyboardShortcuts, useToast
  src/components/      UI (Sidebar, ChatWindow, MessageBubble, SourceCard, Toast, ...)
data/
  courses.json         course registry (anchors + thresholds)
  embeddings.joblib    pre-computed; produced by preprocess_json.py
  jsons.json           ML course raw transcript chunks
  genai_rag_chunks.json    GenAI / RAG / LangChain corpus
  ds_python_chunks.json    Python data science corpus
  preprocess_json.py   builds embeddings.joblib from chunks
  mp3_to_json.py       Whisper transcription script
scripts/               one-off scripts (baseline_comparison)
eval/                  baseline comparison results
tests/                 pytest suite
docs/                  architecture diagram, demo gif
render.yaml            Render deployment blueprint
```

## Re-generating from raw audio

If you swap the videos or the embedding model:

```bash
cd data
python preprocess_json.py            # rebuild embeddings.joblib from jsons.json
```

To rebuild `jsons.json` from raw audio (`data/audios/*.mp3`), run `python mp3_to_json.py` first. It uses Whisper `large-v2`, which honestly needs a GPU.

## Things I'd build next

If this had a v2:

- Reranker between FAISS and the LLM (BGE-Reranker probably)
- Hybrid search (BM25 + dense, RRF)
- Live ingestion endpoint, upload PDF/video then transcribe, embed, index without restarting
- Per-message RAGAS scoring logged into the DB, with a quality dashboard
- A small LLM as a tiebreaker when two courses are within 0.02 of each other on the routing score
- Source previews, hover a citation to see the full chunk and a deep link into the source video at the right timestamp

## Author

Aradhya Stuti, final-year major project. MIT licensed, see [LICENSE](LICENSE).

If you're reading this for review, the most useful files to look at first are [`backend/rag/graph.py`](backend/rag/graph.py) (router), [`backend/rag/courses.py`](backend/rag/courses.py) + [`data/courses.json`](data/courses.json) (registry), [`backend/rag/generator.py`](backend/rag/generator.py) (prompts + breaker), and [`backend/routes/chat.py`](backend/routes/chat.py) (SSE/WS handlers).
