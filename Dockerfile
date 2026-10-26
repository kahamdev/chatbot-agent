FROM python:3.12-slim

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

USER appuser

EXPOSE 8000

# Bind on all interfaces inside the container. The process default outside
# Docker is 127.0.0.1. Proxy headers stay off unless the edge is configured.
CMD ["uvicorn", "chatbot_agent.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
