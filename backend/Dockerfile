# Use official Python image
FROM python:3.10-slim

# Env settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Accept variables
ARG DB_NAME
ARG DB_USER
ARG DB_PASSWORD
ARG DB_HOST
ARG DB_PORT
ARG ALLOWED_HOSTS
ARG WP_ACCESS_TOKEN
ARG WP_VERIFY_TOKEN
ARG MESSAGE_URL
ARG UPLOAD_URL

# Export variables inside container
ENV DB_NAME=$DB_NAME
ENV DB_USER=$DB_USER
ENV DB_PASSWORD=$DB_PASSWORD
ENV DB_HOST=$DB_HOST
ENV DB_PORT=$DB_PORT
ENV ALLOWED_HOSTS=$ALLOWED_HOSTS
ENV WP_ACCESS_TOKEN=$WP_ACCESS_TOKEN
ENV WP_VERIFY_TOKEN=$WP_VERIFY_TOKEN
ENV MESSAGE_URL=$MESSAGE_URL
ENV UPLOAD_URL=$UPLOAD_URL

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8086

CMD ["gunicorn", "voter_mang_sys.wsgi:application", \
     "--bind", "0.0.0.0:8086", \
     "--workers", "4", \
     "--threads", "2", \
     "--timeout", "120"]
 