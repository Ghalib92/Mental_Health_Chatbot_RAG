"""
Retrieval-Augmented Generation pipeline for the mental-health assistant.

Design notes (what makes this "proper" RAG rather than a toy):

* Lazy + cached  - the chain is built on first use, so the Django app and its
  tests boot without the heavy ML deps or API keys. Misconfiguration surfaces
  as ChatbotUnavailable -> a clean HTTP 503.
* Chat model     - uses ChatOpenAI (gpt-4o-mini) instead of the legacy
  completion endpoint.
* History-aware  - follow-up questions are reformulated into standalone queries
  using the conversation history before retrieval (create_history_aware_retriever).
* MMR retrieval  - Maximal Marginal Relevance returns relevant *and* diverse
  chunks, reducing near-duplicate context.
* Citations      - the source document + page of every retrieved chunk is
  returned alongside the answer.
* Safety first   - a crisis check short-circuits the LLM and returns vetted
  helpline resources for self-harm / suicide signals. This is a mental-health
  product; deterministic safety beats a generated answer.
"""

import re
from functools import lru_cache

from django.conf import settings


class ChatbotUnavailable(Exception):
    """Raised when the RAG chain cannot be built (missing keys or deps)."""


# --------------------------------------------------------------------------- #
# Crisis / safety layer
# --------------------------------------------------------------------------- #
_CRISIS_PATTERNS = [
    r"\bkill (myself|me)\b",
    r"\b(suicide|suicidal)\b",
    r"\bend (my|it all|my life)\b",
    r"\b(want|going) to die\b",
    r"\bself[\s-]?harm\b",
    r"\b(hurt|harm)(ing)? myself\b",
    r"\bno reason to live\b",
    r"\bcan'?t go on\b",
]
_CRISIS_RE = re.compile("|".join(_CRISIS_PATTERNS), re.IGNORECASE)

CRISIS_RESOURCES = [
    {"name": "Emergency services", "contact": "Call your local emergency number immediately"},
    {"name": "US – 988 Suicide & Crisis Lifeline", "contact": "Call or text 988"},
    {"name": "UK & ROI – Samaritans", "contact": "Call 116 123"},
    {"name": "Kenya – Befrienders Kenya", "contact": "+254 722 178 177"},
    {"name": "International directory", "contact": "https://findahelpline.com"},
]

CRISIS_MESSAGE = (
    "I'm really sorry you're feeling this way, and I'm glad you reached out. "
    "I'm not able to help with a crisis, but you deserve immediate support from "
    "a trained person. Please contact one of the resources below right now — you "
    "are not alone."
)


def detect_crisis(message: str) -> bool:
    return bool(_CRISIS_RE.search(message or ""))


# --------------------------------------------------------------------------- #
# RAG chain (lazy, cached)
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _build_chain():
    if not settings.OPENAI_API_KEY or not settings.PINECONE_API_KEY:
        raise ChatbotUnavailable(
            "Chatbot is not configured. Set OPENAI_API_KEY and PINECONE_API_KEY, "
            "and build the index with `python store_index.py`."
        )

    try:
        import os

        from langchain.chains import (
            create_history_aware_retriever,
            create_retrieval_chain,
        )
        from langchain.chains.combine_documents import create_stuff_documents_chain
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_openai import ChatOpenAI
        from langchain_pinecone import PineconeVectorStore

        from src.helper import download_hugging_face_embeddings
        from src.prompt import contextualize_q_system_prompt, system_prompt
    except ImportError as exc:  # pragma: no cover - optional ML deps
        raise ChatbotUnavailable(f"Chatbot dependencies are not installed: {exc}") from exc

    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
    os.environ["PINECONE_API_KEY"] = settings.PINECONE_API_KEY

    embeddings = download_hugging_face_embeddings()
    docsearch = PineconeVectorStore.from_existing_index(
        index_name=settings.PINECONE_INDEX_NAME,
        embedding=embeddings,
    )
    retriever = docsearch.as_retriever(
        search_type="mmr",
        search_kwargs={"k": settings.RAG_RETRIEVER_K, "fetch_k": settings.RAG_FETCH_K},
    )

    llm = ChatOpenAI(model=settings.OPENAI_CHAT_MODEL, temperature=0.3, max_tokens=500)

    contextualize_prompt = ChatPromptTemplate.from_messages([
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_prompt
    )

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    qa_chain = create_stuff_documents_chain(llm, qa_prompt)
    return create_retrieval_chain(history_aware_retriever, qa_chain)


def _to_messages(history):
    """Convert [{'role': 'user'|'assistant', 'content': ...}] to LC messages."""
    from langchain_core.messages import AIMessage, HumanMessage

    messages = []
    for turn in history or []:
        role, content = turn.get("role"), turn.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role in ("assistant", "ai", "bot"):
            messages.append(AIMessage(content=content))
    return messages


def _format_sources(documents):
    seen, sources = set(), []
    for doc in documents:
        meta = doc.metadata or {}
        source = meta.get("source", "knowledge base")
        page = meta.get("page")
        key = (source, page)
        if key in seen:
            continue
        seen.add(key)
        sources.append({"source": source.split("/")[-1], "page": page})
    return sources


def answer_question(message: str, history=None) -> dict:
    """
    Answer a user message. Returns:
        {"answer": str, "sources": list, "crisis": bool}

    Crisis messages short-circuit the LLM and return vetted helpline resources.
    """
    if detect_crisis(message):
        return {
            "answer": CRISIS_MESSAGE,
            "sources": [],
            "crisis": True,
            "resources": CRISIS_RESOURCES,
        }

    chain = _build_chain()
    result = chain.invoke({"input": message, "chat_history": _to_messages(history)})
    return {
        "answer": result["answer"],
        "sources": _format_sources(result.get("context", [])),
        "crisis": False,
    }


def reset_cache():
    """Clear the cached chain (used in tests after changing settings)."""
    _build_chain.cache_clear()
