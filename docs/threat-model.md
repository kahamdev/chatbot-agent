# Threat model

## Assets

- Provider and LangSmith API keys
- Conversation text in the checkpointer
- The ability to run only the two approved tools
- Availability of the API process

## Trust boundaries

- The caller is untrusted. Message text, thread ids, and headers are data.
- Tool results and knowledge notes are untrusted data inside the prompt. They are not instructions and they are not credentials.
- The system prompt is the only instruction channel.
- The model output chooses a tool name and arguments. It does not choose a Python function, a file path, or a URL. The tools node ignores names that are not in the registry.

## Controls

| Threat | Control |
| --- | --- |
| Stolen thread id | Owner map returns 403. Checkpoints are stored under `user_id:thread_id`. |
| Guessed or short API key | Production requires auth and keys of at least 32 characters. Comparison uses SHA-256 digests. |
| Huge body | `Content-Length` is required and capped at 64 KiB before the body is parsed. |
| Tool abuse or code execution | Allowlist of two read-only tools. Calculator uses an AST and rejects `**`, names, and calls. |
| Prompt injection | No shell, SQL, or HTTP tool exists to abuse. The local model quotes tool text instead of obeying it. A hosted model can still be persuaded to say something unsafe. |
| Secret in a log or trace | Bodies and the Authorization header are not logged. The default tracer is forced off. Opt-in traces pass through a redacting client. |
| Stack trace leaked to the client | Handlers return a fixed message and a request id. |
| Unauthenticated production deploy | Startup fails when `APP_ENV=production` and auth, trusted hosts, or CORS are loose. |
| Runaway tool loop | Tool-call cap and graph step cap. |

## Residual risk

- Rate limits and thread ownership are per process. Several workers do not share them.
- Memory checkpoints are lost on restart. A later database must store the owner with the thread, or the user prefix alone is the isolation boundary.
- A hosted model can ignore the system prompt. Keep tools read-only until an approval step exists.
- Redaction catches common key shapes. It is not a complete PII filter. Review the LangSmith project before enabling tracing.
- `BaseHTTPMiddleware` buffers a request that has already passed the size check. The size check itself does not read the body.
