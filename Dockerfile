FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright ya está instalado en la imagen base mcr.microsoft.com/playwright/python
# Solo necesitamos descargar el navegador si no está
RUN playwright install chromium 2>/dev/null || true

# Copiar aplicación
COPY app.py .
COPY index.html .
COPY indexInstagram.html .

EXPOSE 10000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --timeout 120 app:app"]