# 🔐 USAR CON CREDENCIALES DE INSTAGRAM

## ⚠️ IMPORTANTE: SEGURIDAD

Antes de hacer login, lee esto:

### ✅ LO QUE ES SEGURO:
- Las credenciales se procesan **localmente** en tu PC
- NO se envían a servidores externos
- NO se guardan en bases de datos
- Solo se usan para autenticación con Instagram

### ❌ LO QUE NO DEBES HACER:
- **NO uses tu cuenta principal personal** (la que uses diariamente)
- **NO uses una cuenta de trabajo importante**
- **NO compartas tus credenciales** con otros

### 💡 RECOMENDACIÓN:
Crea una **cuenta secundaria de Instagram** solo para:
- Scraping de datos
- Gestión de negocio
- Análisis de competencia

---

## 🚀 CÓMO HACER LOGIN

### Paso 1: Abrir la app
```
http://localhost:5000
```

Verás una sección "🔐 Login en Instagram" al inicio.

### Paso 2: Ingresa credenciales
```
Usuario: tu_usuario_instagram
Contraseña: tu_contraseña
```

### Paso 3: Click "🔐 Hacer Login"

Espera 10-15 segundos mientras Instaloader se autentica.

### Paso 4: Confirmación
Verás: ✅ **Conectado como: @tu_usuario**

---

## ✨ BENEFICIOS CON LOGIN

| Función | Sin Login | Con Login |
|---------|-----------|----------|
| Perfiles públicos | ✅ | ✅ |
| Perfiles privados | ❌ | ✅ |
| Rate limit | 200 req/hora | 2000+ req/hora |
| Datos precisos | ⚠️ A veces bloqueado | ✅ Siempre preciso |
| Mejor velocidad | ⏱️ Lento | ⚡ Rápido |

---

## 🔍 QUÉ VES EN LOS LOGS

Cuando haces login, verás en PowerShell:

```
🔐 Intentando login como @tu_usuario...
✅ Login exitoso como @tu_usuario
```

Y en la app aparecerá el botón "🚪 Logout"

---

## 🎯 CASOS DE USO

### **1. Analizar cuentas públicas (SIN LOGIN)**
```
App abierta → Importar CSV → Actualizar cuentas
(Funciona sin credenciales)
```

### **2. Analizar cuentas privadas (CON LOGIN)**
```
App abierta → Login → Importar CSV → Actualizar cuentas
(Necesita credenciales)
```

### **3. Mejor rendimiento (CON LOGIN RECOMENDADO)**
```
Si actualizas muchas cuentas → Usa login
(Menos bloqueos de Instagram)
```

---

## ❓ PREGUNTAS FRECUENTES

### ¿Instagram me bloqueará por hacer scraping?
**Respuesta**: Con Instaloader es muy poco probable. Es una librería conocida y usada oficialmente por empresas.

### ¿Qué pasa si cambio mi contraseña?
**Respuesta**: La sesión se invalida. Haz logout y vuelve a hacer login.

### ¿Puedo usar credenciales de otra persona?
**Respuesta**: Sí, pero solo si tienes permiso. Legalmente es responsabilidad tuya.

### ¿Las credenciales quedan guardadas?
**Respuesta**: NO. Se usan solo para la sesión actual. Cuando cierras la app, se pierden.

### ¿Puedo usar la app sin credenciales?
**Respuesta**: SÍ. Funciona para perfiles públicos. El login es opcional.

---

## 🔒 BUENAS PRÁCTICAS

### 1. **Usa una cuenta secundaria**
```
Crea una cuenta especial para análisis
No uses tu cuenta personal
```

### 2. **No compartas credenciales**
```
Mantén el usuario/contraseña privado
No lo guardes en notas públicas
```

### 3. **Logout cuando termines**
```
Haz click en "🚪 Logout" antes de cerrar
Cierra la app correctamente
```

### 4. **Respeta los límites de Instagram**
```
No hagas scraping excesivo
Espera entre solicitudes (la app lo hace automáticamente)
Usa la app responsablemente
```

---

## 🆘 PROBLEMAS CON LOGIN

### "Error: Invalid credentials"
- Verifica que escribiste bien el usuario
- Verifica que escribiste bien la contraseña
- Asegúrate de que la cuenta existe

### "Error: Login required"
- Instagram bloqueó el acceso
- Intenta hacer login desde un navegador primero
- Resuelve cualquier verificación que Instagram pida

### "Error: Two-factor authentication"
- Instagram pide verificación de dos factores
- Desactívalo temporalmente en tu cuenta
- O crea una cuenta secundaria sin 2FA

### "Timeout"
- Instagram tardó mucho en responder
- Espera un minuto y vuelve a intentar
- Intenta desde otra red (WiFi o datos móviles)

---

## 📊 DESPUÉS DE LOGIN

Una vez conectado:

1. ✅ Importa tu CSV normalmente
2. ✅ Click "🔄 Actualizar" en cada cuenta
3. ✅ **Espera 5-10 segundos por cuenta**
4. ✅ Los datos se cargan automáticamente
5. ✅ Ve los gráficos y análisis

---

## 🚀 PRÓXIMOS PASOS

1. ✅ Inicia la app: `python app.py`
2. ✅ Abre: `http://localhost:5000`
3. ✅ Ingresa credenciales (opcional pero recomendado)
4. ✅ Importa tu CSV
5. ✅ Actualiza las cuentas
6. ✅ ¡Analiza los datos!

---

¿Necesitas ayuda? Cuéntame exactamente qué error ves 👍
