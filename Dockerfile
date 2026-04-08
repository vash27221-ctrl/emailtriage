FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY email-triage-env/requirements.txt .
COPY email-triage-env/email_triage/ ./email-triage-env/email_triage/
COPY email-triage-env/scripts/ ./email-triage-env/scripts/
COPY inference.py .

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

# Required env vars — set at runtime via docker run -e or HF Space secrets
# API_BASE_URL has a default in inference.py
# MODEL_NAME has a default in inference.py
# HF_TOKEN must be provided at runtime

CMD ["python", "inference.py"]
