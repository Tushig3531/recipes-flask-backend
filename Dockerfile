FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT 8080

CMD exec gunicorn --bind :$PORT app:app
