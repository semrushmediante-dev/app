# Usa la imagen oficial de Playwright que ya trae Python y los navegadores instalados
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Directorio de trabajo
WORKDIR /app

# Copiar e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de la aplicación
COPY . .

# Exponer el puerto que usa Flask
EXPOSE 7860

# Comando para arrancar la app
CMD ["python", "app.py"]
