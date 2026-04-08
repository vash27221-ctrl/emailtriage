FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Copy everything needed
COPY requirements.txt .
COPY email_triage/ ./email-triage-env/email_triage/
COPY scripts/ ./email-triage-env/scripts/
COPY openenv.yaml .
COPY README.md .

# Copy inference.py from repo root into container root
COPY ../inference.py .

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

CMD ["python", "inference.py"]
