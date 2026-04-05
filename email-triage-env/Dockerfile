FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY requirements.txt .
COPY email_triage/ ./email_triage/
COPY scripts/ ./scripts/
COPY hf_spaces_app.py .
COPY openenv.yaml .
COPY README.md .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

# For HF Spaces - run the app that demonstrates the environment
CMD ["python", "hf_spaces_app.py"]
