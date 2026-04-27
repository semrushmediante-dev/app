FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para Playwright
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    apt-transport-https \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libgconf-2-4 \
    libgdk-pixbuf1.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libharfbuzz0b \
    libice6 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libsm6 \
    libxss1 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxinerama1 \
    libxrandr2 \
    libxrender1 \
    libxshmfence1 \
    libxkbcommon0 \
    libxslt1.1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Playwright y descargar navegadores
RUN pip install --no-cache-dir playwright && \
    playwright install chromium

# Copiar aplicación
COPY app.py .
COPY index.html .
COPY indexInstagram.html .
COPY indexHosting.html . 2>/dev/null || true

EXPOSE 10000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --timeout 120 app:app"]