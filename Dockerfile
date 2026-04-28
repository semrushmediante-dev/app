FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py app_whisper.py index.html indexInstagram.html indexWhisper.html ./

CMD gunicorn --bind 0.0.0.0:${PORT:-10000} --timeout 600 --workers 1 --threads 4 app:app
