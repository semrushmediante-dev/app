FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegador Chromium
RUN playwright install chromium

# Copiar TODO el contenido del proyecto (HTMLs, scripts, etc.)
COPY . .

# Comando para ejecutar con Gunicorn (especificando app:app)
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--workers", "1", "--threads", "8", "--timeout", "120", "app:app"]