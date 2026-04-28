import streamlit as st
import requests
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Monitoreo de Hosting", page_icon="🌐")

st.title("🌐 Monitoreo de Hosting Masivo")
st.write("Sube un CSV o pega las URLs para verificar su estado.")

# 1. Entrada de datos: Archivo o Texto
uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])
text_input = st.text_area("O pega las URLs aquí (una por línea):", height=150)

urls = []
if uploaded_file:
    df_input = pd.read_csv(uploaded_file, header=None)
    urls = df_input[0].tolist()
elif text_input:
    urls = [u.strip() for u in text_input.split('\n') if u.strip()]

if st.button("Iniciar Monitoreo"):
    if not urls:
        st.warning("Introduce algunas URLs primero.")
    else:
        resultados = []
        progreso = st.progress(0)
        
        for i, url in enumerate(urls):
            # Limpieza básica
            url_destino = url if url.startswith(('http://', 'https://')) else 'https://' + url
            
            try:
                res = requests.get(url_destino, timeout=10, verify=False)
                estado = "✅ EN LÍNEA" if res.status_code == 200 else f"⚠️ ERROR {res.status_code}"
                code = res.status_code
            except:
                estado = "❌ CAÍDA / ERROR"
                code = "N/A"
            
            resultados.append({
                "URL de Acceso": url_destino,
                "Estado": estado,
                "Código": code,
                "Fecha/Hora": datetime.now().strftime('%d/%m/%Y %H:%M')
            })
            progreso.progress((i + 1) / len(urls))

        # Mostrar tabla de resultados
        df_res = pd.DataFrame(resultados)
        st.table(df_res) # O st.dataframe(df_res) para que sea interactiva