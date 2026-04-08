FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

COPY email-triage-env/requirements.txt .
COPY email-triage-env/email_triage/ ./email-triage-env/email_triage/
COPY inference.py .
COPY app.py .
COPY server/ ./server/
COPY pyproject.toml .

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
