"""Keyword search over a fixed set of notes shipped with the app.

The query is not a file path, URL, or database statement. Nothing is read
from disk at request time.
"""

import re
from dataclasses import dataclass

_MAX_QUERY = 200
_STOP_WORDS = {
    "that",
    "this",
    "with",
    "from",
    "what",
    "which",
    "when",
    "where",
    "have",
    "your",
    "about",
    "does",
    "into",
}


@dataclass(frozen=True)
class Article:
    title: str
    text: str


ARTICLES: tuple[Article, ...] = (
    Article(
        "Approved tools",
        "The approved tools are calculator and knowledge_search. Both tools are read-only.",
    ),
    Article(
        "Safety limits",
        "The agent does not run shell commands, database queries, or network fetches.",
    ),
    Article(
        "Request limits",
        "Each request has a maximum size, a tool-call limit, and a rate limit.",
    ),
    Article(
        "Conversations",
        "A thread id continues one conversation. It does not grant access to another user.",
    ),
)


def search_knowledge(query: str) -> str:
    if not isinstance(query, str):
        return "Query must be text."
    cleaned = " ".join(query.split())
    if not cleaned or len(cleaned) > _MAX_QUERY:
        return "Query is empty or too long."
    words = _words(cleaned)
    ranked = [
        (article, len(words & _words(f"{article.title} {article.text}"))) for article in ARTICLES
    ]
    matches = [article for article, score in ranked if score > 0]
    if not matches:
        return "No matching notes in the local knowledge base."
    lines = ["Reference data from the local knowledge base:"]
    lines.extend(f"- {article.title}: {article.text}" for article in matches[:3])
    text = "\n".join(lines)
    if len(text) <= 1000:
        return text
    return text[:1000].rstrip() + "..."


def has_knowledge_match(query: str) -> bool:
    words = _words(query)
    if not words:
        return False
    return any(words & _words(f"{article.title} {article.text}") for article in ARTICLES)


def _words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if len(word) >= 4 and word not in _STOP_WORDS
    }
