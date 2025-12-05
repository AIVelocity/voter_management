# Use official Python image
FROM python:3.10-slim

# Avoid .pyc clutter & force buffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy full project
COPY . .

# Expose port
EXPOSE 8086

# Gunicorn command for production
CMD ["gunicorn", "application.wsgi:application", "--bind", "0.0.0.0:8086", "--workers", "3", "--threads", "2", "--timeout", "120"]