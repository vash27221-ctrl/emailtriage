FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY email_triage/ ./email_triage/
COPY scripts/ ./scripts/
COPY openenv.yaml .
COPY README.md .

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "scripts.rl_agent"]
