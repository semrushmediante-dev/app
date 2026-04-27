FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

RUN useradd -m appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ESTA LÍNEA ES VITAL:
RUN playwright install --with-deps chromium

COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 10000

CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app", "--workers", "2", "--timeout", "120"]