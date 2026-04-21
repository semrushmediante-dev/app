# 📱 ANALIZADOR DE SEGUIDORES CON INSTALOADER

## ✨ ¿QUÉ ES INSTALOADER?

**Instaloader** es una librería oficial de Python que:
- ✅ Obtiene datos de Instagram sin bloqueos
- ✅ Muy confiable
- ✅ Mantiene la sesión (más rápido)
- ✅ Soporta perfiles públicos Y privados
- ✅ Menos propenso a fallos que web scraping

---

## 🚀 INSTALACIÓN (PASO A PASO)

### **Requisito: Python instalado**

1. Descarga Python desde: https://www.python.org/downloads/
2. Instala normalmente
3. **IMPORTANTE**: Marca ✅ "Add Python to PATH" durante la instalación
4. Reinicia tu computadora

Verifica que esté instalado:
```powershell
python --version
```

---

### **Paso 1: Descargar archivos**

Descarga estos archivos en una carpeta `instagram-analyzer-python\`:
- `app.py` (Backend con Instaloader)
- `index.html` (Frontend)
- `requirements.txt` (Dependencias)
- `install.bat` (Script de instalación)
- `start.bat` (Script para ejecutar)

---

### **Paso 2: Instalar dependencias**

Opción A: **Script automático**
1. Doble clic en `install.bat`
2. Espera a que termine (1-2 minutos)
3. Verás: ✅ ¡Instalación completada!

Opción B: **Manual en PowerShell**
```powershell
cd C:\tu\carpeta\instagram-analyzer-python

python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

---

### **Paso 3: Ejecutar**

Opción A: **Doble clic en `start.bat`**

Opción B: **PowerShell**
```powershell
python app.py
```

Verás:
```
🚀 Servidor Flask con Instaloader
📊 Abre http://localhost:5000 en tu navegador
```

---

### **Paso 4: Abrir en navegador**

```
http://localhost:5000
```

---

## 🔐 USAR CON LOGIN (RECOMENDADO)

Para acceder a perfiles privados o tener mejor límite de rate:

1. Abre la app: `http://localhost:5000`
2. Aparecerá un botón "🔐 Login"
3. Ingresa tu usuario y contraseña de Instagram
4. ¡Listo! Ahora puedes scrapear perfiles privados

### ⚠️ NOTAS DE SEGURIDAD:

- Las credenciales se usan localmente, no se envían a servidores
- Instagram puede solicitar verificación la primera vez
- Usa una cuenta que no sea importante (Instaloader cuenta como app)

---

## 📋 CÓMO USAR LA APP

### **1. Importar CSV**
- Tab "CSV" → Sube tu archivo o pega datos
- Formato: `Usuario,Encargada,URL`

### **2. Obtener seguidores**
- Click "🔄 Actualizar" en cada cuenta
- La app obtiene automáticamente:
  - Seguidores
  - Following
  - Posts
  - Engagement Rate

### **3. Ver gráficos**
- Crecimiento en tiempo real
- Ranking de cuentas
- Análisis por encargada

### **4. Exportar datos**
- Click "📥 Exportar CSV"
- Descarga datos actualizados

---

## 📊 COLUMNAS QUE OBTIENE

| Columna | Descripción |
|---------|------------|
| Usuario | @username de Instagram |
| Encargada | Responsable de la cuenta |
| URL | Link al perfil |
| Seguidores | Número actual de seguidores |
| Following | Número de cuentas que sigue |
| Posts | Número de publicaciones |
| Engagement Rate (%) | following / followers * 100 |
| Última Actualización | Fecha del último scrape |

---

## ⚡ VENTAJAS vs NODE.JS

| Aspecto | Instaloader (Python) | Puppeteer (Node.js) |
|--------|---|---|
| **Fiabilidad** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Velocidad** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Tamaño descarga** | ~100 MB | ~600 MB |
| **Perfiles privados** | ✅ Con login | ❌ No |
| **Mantenimiento** | Librería oficial | Depende de web scraping |
| **Rate limits** | Menos problemas | Más bloqueos |

---

## ❌ SOLUCIÓN DE PROBLEMAS

### "ModuleNotFoundError: No module named 'flask'"
```powershell
pip install -r requirements.txt
```

### "Perfil no existe"
- Verifica que el usuario existe
- Intenta manualmente: `https://instagram.com/usuario`

### "Requiere login"
- El perfil es privado
- Haz login con tus credenciales (tab "Login")

### "Rate limit exceeded"
- Instagram limitó las solicitudes
- Espera 1 hora y vuelve a intentar

### "Error: no space left on device"
- Este problema NO ocurre con Python
- Instaloader pesa solo ~100 MB

---

## 🔍 VER LOGS EN CONSOLA

Los logs muestran exactamente qué sucede:

```
🔍 Obteniendo datos de @usuario...
✅ usuario: 5000 seguidores
```

Si algo falla, copias el error y me lo pasas.

---

## 📁 ESTRUCTURA DE CARPETAS

```
instagram-analyzer-python/
├── app.py              ← Backend (Instaloader)
├── index.html          ← Frontend
├── requirements.txt    ← Dependencias
├── install.bat         ← Instalar
├── start.bat           ← Ejecutar
├── data.json          ← Base de datos (se crea)
└── venv/              ← Entorno virtual (se crea)
```

---

## 🚀 PROXIMOS PASOS

1. ✅ Instala Python
2. ✅ Ejecuta `install.bat`
3. ✅ Ejecuta `start.bat`
4. ✅ Abre `http://localhost:5000`
5. ✅ Importa tu CSV
6. ✅ ¡Obten seguidores automáticamente!

---

¿Necesitas ayuda? Cuéntame en qué paso te atascas 👍
