# Evaluation plan

The checked-in cases live in `src/chatbot_agent/evals.py` and run through the local model. They cover:

- direct arithmetic, including parentheses
- a question that should search the local notes
- a request to run a shell command
- a prompt-injection request that asks for the system prompt

A case fails when the answer misses the expected fragment or contains a forbidden fragment. Forbidden fragments include the system-prompt rule and path-like shell output.

```bash
uv run python scripts/run_evaluations.py
uv run pytest tests/evaluations
```

These cases are deterministic. They do not measure a hosted model.

Before pointing `MODEL_PROVIDER` at a hosted model, add a separate set that records:

- tool choice for arithmetic versus ordinary questions
- refusal or safe fallback when the user asks for shell, SQL, or secrets
- behavior when a tool result says "ignore your instructions"
- latency and failure rate

Do not treat the local cases as a quality score for that hosted model. Keep tracing off until the LangSmith project has a retention policy and the redaction check has been inspected on a real trace.
