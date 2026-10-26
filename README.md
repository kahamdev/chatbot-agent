# Chatbot agent

A small chat API. One FastAPI service runs a short LangGraph workflow with two read-only tools: arithmetic, and search over notes that ship with the app.

The default model is local and does not call a provider. It follows a few visible rules so the project runs without an API key. Set `MODEL_PROVIDER=openai` when you want a hosted model. The graph, tool allowlist, and limits stay the same.

## What a request does

1. The API checks the body size, the API key (when auth is on), and the rate limit.
2. `validate_input` rejects an empty or oversized message.
3. `assistant` calls the model with a fixed system prompt.
4. If the model asks for a tool, `tools` runs it only when the name is on the allowlist.
5. The model may run again to use the tool result. The loop stops at `MAX_TOOL_CALLS`.
6. `finalize` returns the answer text. The response is truncated to the output budget.

```text
validate_input -> assistant -> tools -> assistant -> finalize
```

Conversation memory uses an in-process checkpointer. The saved thread key is `user_id:thread_id`. A thread id is not proof of identity.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
cp .env.example .env
uv run uvicorn chatbot_agent.main:app --host 127.0.0.1 --port 8000
```

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Health checks: `GET /health` and `GET /ready`.

## Call the API

Auth is off in the sample `.env`, which is a single local user. Do not expose that process beyond your machine.

```bash
curl -s http://127.0.0.1:8000/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message": "What is (2 + 3) * 4?"}'
```

```bash
curl -s http://127.0.0.1:8000/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message": "Which tools are available?"}'
```

Send the returned `thread_id` on the next turn to continue that conversation.

With auth enabled, create a long random token in `API_KEYS` as `token:user_id` and send `Authorization: Bearer <token>`.

## Tests

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run python scripts/run_evaluations.py
```

## Configuration

See `.env.example`. Production startup refuses to boot unless auth is on, CORS origins are explicit, and trusted hosts are explicit. Docs are disabled in production.

`MODEL_PROVIDER=local` needs no key. `MODEL_PROVIDER=openai` needs `MODEL_API_KEY` and a real `MODEL_NAME`.

LangSmith tracing is off unless `LANGSMITH_TRACING=true` and a key are set. The app forces LangChain's default tracer off and sends traces only through a client that redacts common key shapes. Leave tracing off until you have reviewed the LangSmith project retention settings.

## Security boundaries

- Tools are the two functions in `src/chatbot_agent/tools/registry.py`. There is no shell, SQL, or HTTP tool.
- The calculator walks a syntax tree. It allows `+ - * /` and parentheses. It does not call `eval`.
- Knowledge search reads a fixed list in code. The query is not a path.
- Request bodies over 64 KiB are rejected before they are parsed.
- Errors returned to clients use a fixed message. Stack traces and secrets are not included.
- Logs record the method, path, status, latency, user id, and request id. They do not record the message body or the `Authorization` header.
- API keys are compared by SHA-256 digest. They are `SecretStr` values and are not copied into the environment by the tracing setup.

## Limitations

- Checkpoints, rate limits, and thread ownership live in this process. They reset on restart and are not shared across workers.
- The local model is a deterministic stand-in, not a classifier that makes a hosted model safe. Hosted-model safety here is the allowlist, the step cap, and the prompt. It can still phrase an answer badly.
- There is no write tool, so there is no approval step. Add approval before any tool that changes data or sends a message.
- `TOOL_TIMEOUT_SECONDS` is reserved. The built-in tools are in-process and reject oversized input instead.
- Streaming is not implemented.
- A durable database is not implemented. `CHECKPOINT_BACKEND` accepts only `memory`.

## Docs

- [Architecture](docs/architecture.md)
- [Threat model](docs/threat-model.md)
- [Evaluation plan](docs/evaluation-plan.md)
- [Development plan](chatbot-plan.md)

## Docker

```bash
docker compose up --build
```

The published port is bound to `127.0.0.1:8000`. The container still listens on `0.0.0.0` inside its network namespace.
