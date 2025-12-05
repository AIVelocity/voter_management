# Use official Python image
FROM python:3.10-slim

# Environment settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy full project
COPY . .

# Expose application port
EXPOSE 8086

# ---------------------------
# PRODUCTION START COMMAND
# ---------------------------
# Gunicorn for ~15 users (≈4 workers + 2 threads)
CMD ["gunicorn", "voter_management_sys.wsgi:application", \
     "--bind", "0.0.0.0:8086", \
     "--workers", "4", \
     "--threads", "2", \
     "--timeout", "120"]