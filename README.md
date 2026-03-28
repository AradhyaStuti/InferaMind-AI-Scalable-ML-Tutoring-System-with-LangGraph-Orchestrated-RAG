<p align="center">
  <img src="banner.svg" alt="InferaMind AI Banner" width="100%"/>
</p>

<h1 align="center">InferaMind AI: Scalable ML Tutoring System with LangChain, LangGraph & RAG Pipelines</h1>

<p align="center">
  A full-stack Retrieval-Augmented Generation teaching assistant for Andrew Ng's Machine Learning Specialization Course 1.<br/>
  Built with <b>React</b>, <b>FastAPI</b>, <b>LangChain</b>, <b>LangGraph</b>, and <b>Ollama</b> — fully local, no external APIs.<br/>
  Features an <b>embeddings-based query classifier</b>, <b>RAGAS evaluation metrics</b>, and a <b>4-job CI/CD pipeline</b>.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/LangChain-1.2-green?logo=chainlink&logoColor=white" alt="LangChain"/>
  <img src="https://img.shields.io/badge/LangGraph-1.1-purple?logo=chainlink&logoColor=white" alt="LangGraph"/>
  <img src="https://img.shields.io/badge/RAGAS-eval-orange?logo=checkmarx&logoColor=white" alt="RAGAS"/>
  <img src="https://img.shields.io/badge/Ollama-local_LLM-blueviolet?logo=llama&logoColor=white" alt="Ollama"/>
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker"/>
</p>

---

## Architecture

```
                    +-------------------+
                    |   React Frontend  |
                    |   (Vite + React)  |
                    +--------+----------+
                             |
                      REST + SSE Streaming
                             |
                    +--------+----------+
                    |  FastAPI Backend   |
                    |                   |
                    |  +-------------+  |
                    |  | LangGraph   |  |
                    |  | RAG Pipeline|  |
                    |  | - Classify  |  |  <- Embeddings-based (cosine sim to course centroid)
                    |  | - Retrieve  |  |  <- FAISS + BGE-M3 semantic search
                    |  | - Generate  |  |  <- LLaMA 3.2 via Ollama
                    |  +------+------+  |
                    |         |         |
                    |  +------+------+  |
                    |  |   RAGAS     |  |  <- Evaluation: precision, recall, faithfulness
                    |  |   Metrics   |  |
                    |  +-------------+  |
                    |                   |
                    +----+----+----+----+
                         |         |
                  +------+--+  +---+------+
                  | Ollama  |  | SQLite   |
                  | bge-m3  |  | Chat DB  |
                  | llama3.2|  | Auth DB  |
                  +---------+  +----------+
```

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Frontend   | React 19, Vite, Lucide Icons, React Markdown |
| Backend    | FastAPI, Uvicorn, Pydantic          |
| AI/ML      | LangChain, LangGraph, Ollama (LLaMA 3.2), BGE-M3 embeddings |
| RAG        | LangGraph state machine, FAISS, cosine similarity, scikit-learn |
| Classifier | Embeddings-based cosine similarity to course centroid (replaces keyword matching) |
| Evaluation | RAGAS-style metrics — context precision, context recall, faithfulness, answer relevancy |
| Auth       | JWT (python-jose), bcrypt, HTTPBearer |
| Database   | SQLite (conversations + user auth)  |
| Streaming  | Server-Sent Events (SSE)            |
| Testing    | pytest (backend), Vitest (frontend), 40+ tests |
| DevOps     | Docker, GitHub Actions CI/CD (4-job pipeline: lint, test, build, Docker) |

## Features

- **LangGraph RAG Pipeline** — stateful graph: classify -> retrieve -> generate with off-topic filtering
- **Embeddings-based Classifier** — cosine similarity to a course centroid vector replaces brittle keyword matching
- **RAGAS Evaluation Metrics** — context precision, context recall, faithfulness, and answer relevancy scored per response
- **Real-time Streaming** — token-by-token response streaming via SSE
- **Circuit Breaker + Retry** — exponential backoff with circuit breaker pattern for LLM resilience
- **JWT Authentication** — user registration, login, and protected endpoints
- **Conversation History** — persistent chat sessions stored in SQLite
- **Source Citations** — every response shows exact video timestamps with similarity scores
- **Modern UI** — dark-themed React chat interface with sidebar, typing indicators, and suggested questions
- **Fully Local** — no external APIs, everything runs on your machine via Ollama
- **Full Test Suite** — 40+ tests across backend (pytest) and frontend (Vitest), wired into CI
- **Docker Ready** — multi-stage Dockerfile + docker-compose with GPU support

## Project Structure

```
InferaMind-AI/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration
│   ├── auth/
│   │   └── security.py      # JWT auth, user registration, login
│   ├── rag/
│   │   ├── embeddings.py    # Embedding service & similarity search
│   │   ├── evaluation.py    # RAGAS metrics (precision, recall, faithfulness, relevancy)
│   │   ├── generator.py     # LLM prompt building & streaming
│   │   └── graph.py         # LangGraph RAG state machine + embeddings classifier
│   ├── routes/
│   │   ├── auth.py          # Auth endpoints (register/login)
│   │   ├── chat.py          # POST /api/chat (streaming)
│   │   └── conversations.py # CRUD conversation endpoints
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   └── db/
│       └── store.py         # SQLite conversation storage
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Root component
│   │   ├── styles.css       # Global styles
│   │   ├── api/client.js    # API client with streaming
│   │   ├── hooks/useChat.js # Chat state management hook
│   │   └── components/
│   │       ├── Sidebar.jsx       # Conversation list
│   │       ├── ChatWindow.jsx    # Main chat area
│   │       ├── MessageBubble.jsx # Message rendering + markdown
│   │       ├── SourceCard.jsx    # RAG source citations
│   │       ├── InputArea.jsx     # Message input
│   │       └── WelcomeScreen.jsx # Landing page with suggestions
│   ├── index.html
│   └── vite.config.js
├── data/
│   ├── jsons.json           # Video transcript chunks
│   ├── embeddings.joblib    # Pre-computed embeddings
│   ├── preprocess_json.py   # Script to generate embeddings
│   └── mp3_to_json.py       # Script to transcribe audio
├── tests/
│   ├── test_auth.py         # Auth endpoint tests
│   ├── test_chat.py         # Chat endpoint tests
│   ├── test_conversations.py
│   ├── test_edge_cases.py
│   ├── test_evaluation.py   # RAGAS evaluation metric tests
│   ├── test_health.py
│   └── test_rag.py          # RAG pipeline + classifier tests
├── .github/workflows/       # CI/CD pipelines
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Full stack orchestration
└── requirements.txt
```

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com) installed and running

### 1. Install Ollama models
```bash
ollama pull bge-m3
ollama pull llama3.2
```

### 2. Backend setup
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1     # Windows
# source venv/bin/activate      # Mac/Linux

pip install -r requirements.txt
```

### 3. Generate embeddings (first time only)
```bash
cd data
python preprocess_json.py
cd ..
```

### 4. Frontend setup
```bash
cd frontend
npm install
npm run build
cd ..
```

### 5. Run the app
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

### Development mode (hot reload)
```bash
# Terminal 1 - Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend && npm run dev
```
Frontend dev server runs on http://localhost:3000 and proxies API calls to the backend.

### Docker
```bash
docker compose up --build
```

## API Endpoints

| Method | Endpoint                             | Auth | Description                    |
|--------|--------------------------------------|------|--------------------------------|
| POST   | `/api/auth/register`                 | No   | Register a new user            |
| POST   | `/api/auth/login`                    | No   | Login and get JWT token        |
| POST   | `/api/chat`                          | Yes  | Send message, get streaming response |
| GET    | `/api/conversations`                 | Yes  | List all conversations         |
| POST   | `/api/conversations`                 | Yes  | Create new conversation        |
| GET    | `/api/conversations/:id/messages`    | Yes  | Get messages for a conversation|
| PATCH  | `/api/conversations/:id`             | Yes  | Rename conversation            |
| DELETE | `/api/conversations/:id`             | Yes  | Delete conversation            |
| GET    | `/api/health`                        | No   | Health check                   |

## How the RAG Pipeline Works

```
START -> [Classify] --course_related--> [Retrieve] -> END
              |
              +--off_topic--> [Off-Topic Handler] -> END
```

1. **User asks a question** via the chat UI
2. **Classification** — embeddings-based classifier computes cosine similarity between the query vector and a pre-computed course centroid (mean of 19 anchor phrases like "gradient descent", "linear regression", etc.). If similarity >= 0.35, the query is course-related; otherwise off-topic
3. **Retrieval** — BGE-M3 embeddings + FAISS inner-product search finds the top-K relevant transcript chunks
4. **Augmentation** — retrieved chunks + conversation history are injected into the prompt
5. **Generation** — LLaMA 3.2 generates a response via circuit breaker + retry, streamed token-by-token to the UI
6. **Storage** — both the question and response are saved to SQLite for conversation continuity

## RAGAS Evaluation Metrics

The pipeline includes a built-in evaluation framework (`backend/rag/evaluation.py`) implementing four RAGAS-style metrics:

| Metric | What it measures | How it works |
|--------|-----------------|--------------|
| **Context Precision** | Are retrieved chunks relevant? | Fraction of top-K chunks with cosine sim >= 0.40 to the question |
| **Context Recall** | Does context cover the ground truth? | Fraction of ground-truth sentences semantically matched by at least one chunk |
| **Faithfulness** | Is the answer grounded in context? | Fraction of answer sentences semantically supported by retrieved chunks |
| **Answer Relevancy** | Does the answer address the question? | Cosine similarity between question and answer embeddings |

All metrics return a float in [0, 1]. The aggregate `ragas_score` is the mean of all available metrics.
