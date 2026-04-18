
## RouteLM — ML Tutor with LangGraph & RAG

RouteLM is a full-stack ML tutoring assistant built around a simple idea:

> Not every question should go through RAG.

Instead of always retrieving context, the system first decides *how* to answer — whether from course videos, from general ML knowledge, or not at all.

It’s built using **React, FastAPI, LangGraph, LangChain, Groq, and Ollama**, and focuses on clean system design rather than just demoing RAG.

---

##  What makes it different?

Most RAG systems directly retrieve context for every query.

RouteLM introduces a decision step before that:

* If the question is **covered in course videos** → use retrieval
* If it's **ML-related but not in videos** → answer using the LLM’s own knowledge
* If it’s **not ML-related** → reject it

This is implemented using **embedding-based routing with cosine similarity**.

---

##  Quick summary

RouteLM is a RAG-based ML tutor with a 3-way routing system. It uses Groq for LLM responses and Ollama for embeddings. Answers come either from FAISS-retrieved video transcripts or directly from the LLM. Includes evaluation metrics, authentication, streaming, and CI/CD.

---

##  Why Groq + Ollama?

This setup is intentional:

* **Groq** → used for generating responses

  * Provides fast inference for large models
* **Ollama** → used for embeddings

  * Handles semantic search and query routing locally

If a Groq API key is not available, the system falls back to Ollama for generation as well.

---

##  Architecture (Simplified)

```
React Frontend
     ↓
FastAPI Backend
     ↓
LangGraph Pipeline
   - Classify (routing)
   - Retrieve (FAISS + embeddings)
   - Direct answer (LLM)
   - Generate response
     ↓
SQLite + Evaluation Metrics
```

---

##  Tech Stack

* **Frontend:** React, Vite
* **Backend:** FastAPI, Pydantic
* **LLM:** Groq / Ollama
* **Embeddings:** BGE-M3 (Ollama) + FAISS
* **Orchestration:** LangGraph
* **Evaluation:** RAG-style metrics (precision, recall, faithfulness, relevancy)
* **Auth:** JWT + bcrypt
* **Database:** SQLite
* **Streaming:** SSE + WebSocket
* **Testing:** pytest (unit + integration tests)
* **DevOps:** Docker + GitHub Actions

---

##  Features

* 3-way query routing (retrieval vs direct answer vs rejection)
* Provider-agnostic LLM setup (Groq ↔ Ollama)
* Retrieval from video transcripts with timestamps
* Direct ML knowledge responses when retrieval isn’t applicable
* Built-in evaluation metrics for response quality
* Real-time streaming responses
* Retry handling for LLM failures
* JWT-based authentication
* Persistent conversation storage
* Test coverage across core modules
* Docker-based setup

---

##  Project Structure

```
backend/
  ├── rag/              # pipeline, embeddings, evaluation
  ├── routes/           # API endpoints
  ├── auth/             # authentication
  ├── db/               # storage
frontend/
  ├── components/       # UI
  ├── hooks/            # state management
data/
  ├── transcripts + embeddings
tests/
  ├── unit + integration tests
```

---


##  Setup

### 1. Install models

```bash
ollama pull bge-m3
ollama pull llama3.2
```

### 2. Backend

```bash
python -m venv venv
pip install -r requirements.txt
```

### 3. Environment

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_key
```

### 4. Generate embeddings

```bash
cd data
python preprocess_json.py
```

### 5. Frontend

```bash
cd frontend
npm install
npm run build
```

### 6. Run the app

```bash
ollama serve
python -m uvicorn backend.main:app --reload
```

---

##  How it works

```
START
  ↓
Classify
  ├── course_related → Retrieve → Answer from videos
  ├── course_related_general → Direct LLM answer
  └── off_topic → Reject
```

Routing is based on **embedding similarity with tuned thresholds**.

---

##  API Overview

* `/api/chat` → chat with streaming
* `/api/auth/*` → login / register
* `/api/conversations` → chat history
* `/api/health` → system status

---

##  Evaluation

Each response is evaluated using:

* Context Precision
* Context Recall
* Faithfulness
* Answer Relevancy

Scores range between 0 and 1.

---

##  Testing

```bash
pytest -v
```

Includes both unit and integration tests (integration tests depend on Ollama).

---

##  Final note

This project focuses on a practical question:

**when should a system use retrieval, and when should it not?**

That design decision is what shapes the overall system.
