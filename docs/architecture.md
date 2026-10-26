# Architecture

The process is one FastAPI app. Route handlers validate the JSON body and call `ChatService`. The service owns thread ids and runs the LangGraph workflow.

```text
Client
  -> request id, body limit, CORS, access log, security headers
  -> auth and rate limit
  -> ChatService
       -> thread owner check
       -> LangGraph
            validate_input
            assistant (LangChain chat model)
            tools (allowlist only)
            finalize
       -> MemorySaver checkpoint, key = user_id:thread_id
  -> JSON answer
```

State is three fields:

- `messages`: the conversation, including the system prompt once it is first added
- `tool_calls_used`: count for this user turn, reset to 0 on every request
- `blocked`: set when input is rejected or a tool name is not allowed

`MAX_GRAPH_STEPS` must be at least `MAX_TOOL_CALLS * 2 + 4`. Startup fails closed when the step budget could cut off a normal tool round.

The model is built in `agent/model.py`. `local` is a small rule set: an arithmetic span becomes `calculator`, a keyword overlap becomes `knowledge_search`, and anything else gets a short help reply. `openai` uses `init_chat_model` with the same tools and the same graph.

Tracing is not the default LangChain tracer. When it is enabled, the service wraps one invoke in a LangSmith client whose anonymizer redacts common API-key shapes.
