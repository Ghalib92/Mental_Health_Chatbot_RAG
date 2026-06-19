# Mental Health Chatbot API

A **REST API** for a mental-health support assistant, built with **Django REST Framework**. Its core is a **Retrieval-Augmented Generation (RAG)** chatbot grounded in a curated mental-health knowledge base, wrapped in a **crisis-safety layer**. It also provides appointment **booking** and **contact** endpoints.

JWT for staff endpoints, interactive OpenAPI/Swagger docs, Dockerised, and covered by an automated test suite.

> ⚠️ This project is a portfolio/demo. It is **not** a medical device and not a substitute for professional care or emergency services.

---

## RAG Architecture (the interesting part)

```
user message
   │
   ├─►  Crisis safety layer ──(self-harm/suicide signal)──►  vetted helplines (no LLM)
   │
   ▼
History-aware retriever            (reformulates follow-ups into standalone queries
   │                                using chat history → better multi-turn retrieval)
   ▼
Pinecone vector store  ◄── HuggingFace embeddings (all-MiniLM-L6-v2, 384-dim)
   │  MMR search (relevant + diverse chunks)
   ▼
ChatOpenAI (gpt-4o-mini)  +  grounded, empathetic system prompt
   │
   ▼
answer  +  source citations (document + page)
```

Design decisions worth calling out:

| Concern | Approach |
| --- | --- |
| **Safety** | Deterministic crisis detection short-circuits the LLM and returns vetted helplines — a generated answer is never relied on in a crisis. |
| **Multi-turn** | `create_history_aware_retriever` rewrites follow-ups into standalone questions before retrieval. |
| **Retrieval quality** | MMR (Maximal Marginal Relevance) for relevant *and* non-redundant context; `k`/`fetch_k` configurable. |
| **Grounding** | Answers cite their source document + page; the prompt instructs the model to defer when context is missing. |
| **Robustness** | The chain is lazy-loaded and cached, so the app/tests boot without ML deps or keys; misconfiguration returns a clean `503`. |
| **Abuse control** | The public chat endpoint is rate-limited (DRF throttling). |

The pipeline lives in [Mental_Chatbot/pages/rag.py](Mental_Chatbot/pages/rag.py).

---

## Tech Stack

Python 3.12 · Django 5.2 · Django REST Framework · LangChain (Pinecone + OpenAI + HuggingFace) · PostgreSQL/SQLite · JWT (simplejwt) · drf-spectacular · Gunicorn · WhiteNoise · Docker.

---

## Quick Start (Docker)

```bash
git clone <repo-url>
cd Mental_Health_Chatbot

cp .env.example .env          # set a real SECRET_KEY (chatbot keys optional)
docker compose up --build
```

- API root: <http://localhost:8000/api/>
- Swagger UI: <http://localhost:8000/api/docs/>
- ReDoc: <http://localhost:8000/api/redoc/>
- Admin: <http://localhost:8000/admin/>

---

## Local Development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt        # installs the local src/ package too (-e .)

cp .env.example .env
cd Mental_Chatbot
python manage.py migrate
python manage.py runserver
python manage.py test
```

SQLite is used by default locally; set `DATABASE_URL` for Postgres.

---

## API Overview

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/chat/` | public (throttled) | Ask the assistant; supports `history` for multi-turn |
| GET | `/api/bookings/slots/?date=YYYY-MM-DD` | public | Available appointment slots |
| POST | `/api/bookings/` | public | Book an appointment (emails confirmation) |
| GET | `/api/bookings/` | staff (JWT) | List all bookings |
| POST | `/api/contact/` | public | Send a contact message |
| POST | `/api/auth/login/` · `/api/auth/refresh/` | — | Staff JWT tokens |

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "How can I manage stress before exams?"}'
```

Full reference: [docs/API.md](docs/API.md) or the live Swagger UI.

---

## Enabling the Chatbot

The assistant answers from the PDFs in `Data/`. To enable it:

1. Set `OPENAI_API_KEY` and `PINECONE_API_KEY` in `.env`.
2. Build the vector index once: `python store_index.py`
3. Call `POST /api/chat/`. Until configured it returns `503`; the crisis-safety layer and the rest of the API work regardless.

---

## Security Notes

- `.env` is git-ignored; only `.env.example` (placeholders) is committed.
- `SECRET_KEY`, email and chatbot credentials are read from the environment.
- The public chat endpoint is rate-limited; production security headers enable when `DEBUG=0`.
