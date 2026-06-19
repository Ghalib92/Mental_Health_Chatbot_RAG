# API Reference

Base URL: `http://localhost:8000/api/`

JSON request/response bodies. Staff-only endpoints require an
`Authorization: Bearer <access-token>` header. Interactive docs: `/api/docs/`.

---

## Chat

`POST /chat/` (public, rate-limited)

```json
{
  "message": "I've been feeling overwhelmed lately, any tips?",
  "history": [
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello, how are you feeling today?"}
  ]
}
```

`history` is optional; include prior turns for multi-turn context.

**200 OK**

```json
{
  "answer": "It's understandable to feel overwhelmed. Try breaking tasks into small steps and practising slow breathing; if this persists, consider booking a consultation.",
  "sources": [
    {"source": "mental health WHO.pdf", "page": 12},
    {"source": "MHGuidebook-EBookDownload.pdf", "page": 4}
  ],
  "crisis": false
}
```

**Crisis response** — if the message signals self-harm or suicide, the LLM is
bypassed and vetted resources are returned:

```json
{
  "answer": "I'm really sorry you're feeling this way... please contact one of the resources below right now — you are not alone.",
  "sources": [],
  "crisis": true,
  "resources": [
    {"name": "US – 988 Suicide & Crisis Lifeline", "contact": "Call or text 988"},
    {"name": "Kenya – Befrienders Kenya", "contact": "+254 722 178 177"}
  ]
}
```

**Other statuses**

| Status | Meaning |
| --- | --- |
| 400 | Empty/invalid message |
| 429 | Rate limit exceeded |
| 502 | Upstream model/retrieval failure |
| 503 | Chatbot not configured (missing keys / index) |

---

## Bookings

### Available slots

`GET /bookings/slots/?date=2026-07-01`

```json
{
  "date": "2026-07-01",
  "available_slots": [
    {"time": "08:00", "label": "8:00 AM"},
    {"time": "10:00", "label": "10:00 AM"}
  ]
}
```

### Create a booking

`POST /bookings/` (public)

```json
{ "email": "user@example.com", "date": "2026-07-01", "time": "10:00" }
```

**201 Created** → the booking. A confirmation email is sent. Past dates and
already-booked slots are rejected with **400**.

### List bookings

`GET /bookings/` — **staff only** (JWT). Returns all bookings (paginated).

---

## Contact

`POST /contact/` (public)

```json
{ "name": "Sam", "email": "sam@example.com", "subject": "Question", "message": "..." }
```

**200 OK** → `{ "detail": "Your message was sent successfully." }`

---

## Staff authentication

`POST /auth/login/` with `{ "username", "password" }` (a Django staff/superuser)
→ `{ access, refresh }`. Use the `access` token as a Bearer token for
`GET /bookings/`. Refresh via `POST /auth/refresh/`.
