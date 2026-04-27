FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY app.py .
COPY index.html .
COPY indexInstagram.html .
COPY indexHosting.html . 2>/dev/null || true

EXPOSE 10000

CMD ["sh", "-c", "python app.py"]