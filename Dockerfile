# ChameleonNet Container Image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (build-essential, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase
COPY . .

# Expose honeypot & dashboard ports
EXPOSE 2222 8080 8500

# Run entrypoint
CMD ["python", "main.py"]
