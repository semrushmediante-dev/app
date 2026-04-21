# 🚀 ACTUALIZACIÓN: PUPPETEER (Web Scraping Mejorado)

## ¿QUÉ CAMBIÓ?

Ahora usamos **Puppeteer** en lugar de axios simple:

✅ **Simula un navegador real** - Instagram no lo detecta fácilmente
✅ **Más confiable** - Intenta Puppeteer si axios falla
✅ **Mejor manejo de errores** - Mensajes claros en consola
✅ **Reutiliza navegador** - Es más eficiente

---

## 📋 PASOS PARA INSTALAR

### **Opción 1: Script automático (RECOMENDADO)**

1. Descarga los archivos actualizados:
   - `package.json` (actualizado)
   - `server.js` (actualizado con Puppeteer)
   - `start-puppeteer.bat` (NUEVO)

2. Reemplaza los archivos en tu carpeta `instagram-analyzer/`

3. **Doble clic en `start-puppeteer.bat`**

4. Espera a que se instale Puppeteer (puede tardar 2-3 minutos)

5. Cuando veas "🚀 Servidor corriendo en http://localhost:3000" → abre esa URL

### **Opción 2: Manual en PowerShell**

```powershell
# 1. Navega a tu carpeta
cd C:\instagram-analyzer

# 2. Borra la carpeta node_modules (para que reinstale todo)
rmdir /s /q node_modules

# 3. Instala las nuevas dependencias
npm install

# 4. Inicia el servidor
npm start
```

---

## ⚠️ NOTA IMPORTANTE: DESCARGA DE PUPPETEER

La primera vez que instales Puppeteer, descargará **~300-400 MB** de Chromium.

- **Primera instalación**: 2-5 minutos
- **Siguientes veces**: inicia inmediatamente

---

## 🔄 CÓMO FUNCIONA AHORA

### **Flujo de obtención de datos:**

1. **Intenta con Axios** (rápido, 1-2 segundos)
   - Si funciona → ¡Listo!
   - Si falla → pasa al siguiente

2. **Intenta con Puppeteer** (más lento, 5-10 segundos)
   - Abre un navegador real
   - Carga la página de Instagram
   - Extrae los datos del HTML
   - Si funciona → ¡Excelente!

3. **Si ambos fallan:**
   - Te ofrece actualizar manualmente
   - Puedes ingresar los seguidores por popup

---

## 📊 CÓMO USAR

### **Importar CSV y obtener datos:**

1. Abre `http://localhost:3000`

2. Importa tu `ListaCuentasInstagram_-_Hoja_1.csv`

3. Click en **"🔄 Actualizar"** para cada cuenta

4. En la consola verás algo como:

```
📱 Obteniendo datos de @clinica_javier_miranda...
🔍 Intentando con axios para @clinica_javier_miranda...
⏳ Axios no funcionó, intentando con Puppeteer...
🔍 Scrapeando @clinica_javier_miranda con Puppeteer...
✅ @clinica_javier_miranda: 3245 seguidores obtenidos
```

---

## 🎯 VENTAJAS DE PUPPETEER

| Axios Simple | Puppeteer |
|---|---|
| ❌ Instagram lo bloquea | ✅ Simula navegador real |
| ❌ No ejecuta JavaScript | ✅ Ejecuta JS dinámico |
| ✅ Rápido | ⏱️ Más lento pero confiable |
| ❌ A veces falla | ✅ Mejor tasa de éxito |

---

## ⚙️ PROBLEMAS COMUNES

### "Puppeteer tardó mucho en instalarse"
→ Normal, descarga 400MB. Usa una conexión buena.

### "Error: cannot find module puppeteer"
→ La instalación no completó. Ejecuta:
```powershell
npm install puppeteer puppeteer-extra puppeteer-extra-plugin-stealth
```

### "Puppeteer abre y cierra una ventana"
→ ¡Funciona! No es un error, es el navegador headless de Puppeteer.

### "Sigue sin obtener datos de Instagram"
→ Instagram puede estar bloqueando. Usa actualización manual.

---

## 📝 LOGS EN CONSOLA

Ahora verás mensajes más detallados:

```
📱 Obteniendo datos de @usuario...
🔍 Intentando con axios para @usuario...
⚠️ Axios falló para @usuario: Error message
⏳ Axios no funcionó, intentando con Puppeteer...
🚀 Iniciando navegador Puppeteer...
🔍 Scrapeando @usuario con Puppeteer...
✅ @usuario: 5000 seguidores obtenidos
```

---

## 🔍 PARA DEBUG

Si no funciona, mira los logs:

1. Abre PowerShell en tu carpeta
2. Ejecuta `npm start`
3. Mira los mensajes de error exactos
4. Cuéntame qué dice

---

¡Con Puppeteer tienes **mucha más chance** de obtener los seguidores automáticamente! 🎉
