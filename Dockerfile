# 1. Imagen base con Playwright y Python
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# 2. Crear usuario de seguridad para no usar 'root'
RUN useradd -m appuser
WORKDIR /app

# 3. Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ... después de pip install ...
RUN playwright install --with-deps chromium

# 4. Copiar archivos y dar permisos al usuario
COPY --chown=appuser:appuser . .

# 5. Cambiar al usuario seguro
USER appuser

# 6. Abrir puerto
EXPOSE 7860

# 7. Ejecutar con Gunicorn (Servidor Pro) en lugar de Python directo
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app", "--workers", "2", "--timeout", "120"]