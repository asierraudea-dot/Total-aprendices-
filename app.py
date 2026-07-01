import streamlit as st
import pandas as pd
import requests
import time
import io

# =========================
# CONFIGURACIÓN DE PÁGINA
# =========================
st.set_page_config(
    page_title="Predicción de Formación",
    page_icon="🎓",
    layout="wide"
)

# =========================
# SECRETS STREAMLIT
# =========================
DATAROBOT_API_KEY = st.secrets["DATAROBOT_API_KEY"]
DATAROBOT_DEPLOYMENT_ID = st.secrets["DATAROBOT_DEPLOYMENT_ID"]
DATAROBOT_HOST = st.secrets["DATAROBOT_HOST"].rstrip("/")

BATCH_PREDICTIONS_URL = f"{DATAROBOT_HOST}/api/v2/batchPredictions/"

HEADERS = {
    "Authorization": f"Bearer {DATAROBOT_API_KEY}",
    "Content-Type": "application/json"
}

# =========================
# ESTILOS
# =========================
st.markdown("""
<style>
.main-title {
    font-size: 42px;
    font-weight: 800;
    color: #1E3A8A;
}
.subtitle {
    font-size: 18px;
    color: #475569;
}
.card {
    background-color: #F8FAFC;
    padding: 20px;
    border-radius: 18px;
    border: 1px solid #E2E8F0;
}
.metric-card {
    background-color: #EFF6FF;
    padding: 18px;
    border-radius: 16px;
    text-align: center;
}
.stButton>button {
    width: 100%;
    border-radius: 12px;
    height: 3em;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# =========================
# FUNCIONES
# =========================
def generar_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def ejecutar_prediccion_batch(df):
    csv_data = generar_csv(df)

    payload = {
        "deploymentId": DATAROBOT_DEPLOYMENT_ID,
        "passthroughColumnsSet": "all"
    }

    response = requests.post(
        BATCH_PREDICTIONS_URL,
        headers=HEADERS,
        json=payload
    )

    if response.status_code not in [200, 201, 202]:
        raise Exception(f"Error creando predicción batch: {response.text}")

    job = response.json()
    upload_url = job["links"]["csvUpload"]
    job_url = job["links"]["self"]
    download_url = job["links"]["download"]

    upload_response = requests.put(
        upload_url,
        headers={
            "Authorization": f"Bearer {DATAROBOT_API_KEY}",
            "Content-Type": "text/csv"
        },
        data=csv_data
    )

    if upload_response.status_code not in [200, 201, 202, 204]:
        raise Exception(f"Error subiendo CSV: {upload_response.text}")

    progress_bar = st.progress(0)
    status_text = st.empty()

    while True:
        status_response = requests.get(
            job_url,
            headers={"Authorization": f"Bearer {DATAROBOT_API_KEY}"}
        )

        if status_response.status_code != 200:
            raise Exception(f"Error consultando estado: {status_response.text}")

        status_data = status_response.json()
        status = status_data.get("status")

        porcentaje = int(float(status_data.get("percentageCompleted", 0)))
        progress_bar.progress(min(porcentaje, 100))
        status_text.info(f"Estado de predicción: {status} - {porcentaje}%")

        if status == "COMPLETED":
            break

        if status in ["FAILED", "ABORTED"]:
            raise Exception(f"La predicción falló. Estado: {status}")

        time.sleep(3)

    result_response = requests.get(
        download_url,
        headers={"Authorization": f"Bearer {DATAROBOT_API_KEY}"}
    )

    if result_response.status_code != 200:
        raise Exception(f"Error descargando resultados: {result_response.text}")

    return pd.read_csv(io.StringIO(result_response.text))


# =========================
# ENCABEZADO
# =========================
st.markdown('<div class="main-title">🎓 Predicción de Programas de Formación</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Aplicación conectada a DataRobot para realizar predicciones usando variables institucionales.</div>', unsafe_allow_html=True)

st.divider()

# =========================
# SIDEBAR
# =========================
st.sidebar.title("⚙️ Panel de control")
modo = st.sidebar.radio(
    "Selecciona el modo de predicción",
    ["📝 Predicción manual", "📂 Predicción por archivo CSV"]
)

st.sidebar.info("Las credenciales se cargan desde Streamlit Secrets.")

# =========================
# MODO MANUAL
# =========================
if modo == "📝 Predicción manual":

    st.subheader("📝 Ingreso manual de datos")

    with st.form("formulario_prediccion"):
        col1, col2, col3 = st.columns(3)

        with col1:
            NOMBRE_MUNICIPIO_CURSO = st.selectbox(
                "Municipio del curso",
                [
                    "MEDELLÍN", "BELLO", "ITAGÜÍ", "ENVIGADO", "SABANETA",
                    "RIONEGRO", "COPACABANA", "CALDAS", "LA ESTRELLA",
                    "APARTADÓ", "TURBO", "OTRO"
                ]
            )

            NOMBRE_PROGRAMA_ESPECIAL = st.selectbox(
                "Programa especial",
                [
                    "NINGUNO", "JÓVENES", "MUJERES", "VÍCTIMAS", "EMPRENDIMIENTO",
                    "RURAL", "TIC", "INCLUSIÓN", "EMPRESARIAL", "CONVENIO",
                    "BILINGÜISMO", "OTRO"
                ]
            )

            NOMBRE_PROGRAMA_FORMACION = st.text_input(
                "Nombre del programa de formación",
                "Técnico en programación de software"
            )

            NOMBRE_RESPONSABLE = st.text_input(
                "Nombre del responsable",
                "Responsable del programa"
            )

        with col2:
            NIVEL_FORMACION = st.selectbox(
                "Nivel de formación",
                ["TÉCNICO", "TECNÓLOGO", "OPERARIO", "AUXILIAR"]
            )

            CODIGO_CONVENIO = st.text_input(
                "Código convenio",
                "0"
            )

            IDENTIFICADOR_FICHA = st.number_input(
                "Identificador ficha",
                min_value=0,
                value=2955059,
                step=1
            )

            FECHA_INICIO_FICHA = st.date_input(
                "Fecha inicio ficha"
            )

        with col3:
            FECHA_TERMINACION_FICHA = st.date_input(
                "Fecha terminación ficha"
            )

            NOMBRE_NUEVO_SECTOR = st.selectbox(
                "Nuevo sector",
                [
                    "TECNOLOGÍA", "INDUSTRIA", "SERVICIOS", "COMERCIO",
                    "AGROPECUARIO", "SALUD", "EDUCACIÓN", "CONSTRUCCIÓN",
                    "TURISMO", "ENERGÍA", "TRANSPORTE", "OTRO"
                ]
            )

            DURACION_PROGRAMA = st.number_input(
                "Duración del programa",
                min_value=0,
                value=48,
                step=1
            )

            TOTAL_APRENDICES = st.number_input(
                "Total aprendices",
                min_value=0,
                value=22,
                step=1
            )

        col4, col5 = st.columns(2)

        with col4:
            SECTOR_PRODUCTIVO = st.text_input(
                "Sector productivo",
                "TECNOLOGÍA"
            )

        with col5:
            AÑO = st.number_input(
                "Año",
                min_value=2000,
                max_value=2100,
                value=2026,
                step=1
            )

        enviar = st.form_submit_button("🚀 Realizar predicción")

    if enviar:
        datos = pd.DataFrame([{
            "NOMBRE_MUNICIPIO_CURSO": NOMBRE_MUNICIPIO_CURSO,
            "NOMBRE_PROGRAMA_ESPECIAL": NOMBRE_PROGRAMA_ESPECIAL,
            "NOMBRE_PROGRAMA_FORMACION": NOMBRE_PROGRAMA_FORMACION,
            "NOMBRE_RESPONSABLE": NOMBRE_RESPONSABLE,
            "NIVEL_FORMACION": NIVEL_FORMACION,
            "CODIGO_CONVENIO": CODIGO_CONVENIO,
            "IDENTIFICADOR_FICHA": IDENTIFICADOR_FICHA,
            "FECHA_INICIO_FICHA": str(FECHA_INICIO_FICHA),
            "FECHA_TERMINACION_FICHA": str(FECHA_TERMINACION_FICHA),
            "NOMBRE_NUEVO_SECTOR": NOMBRE_NUEVO_SECTOR,
            "DURACION_PROGRAMA": DURACION_PROGRAMA,
            "TOTAL_APRENDICES": TOTAL_APRENDICES,
            "SECTOR PRODUCTIVO": SECTOR_PRODUCTIVO,
            "AÑO": AÑO
        }])

        st.subheader("📌 Datos enviados al modelo")
        st.dataframe(datos, use_container_width=True)

        try:
            with st.spinner("Consultando modelo en DataRobot..."):
                resultado = ejecutar_prediccion_batch(datos)

            st.success("✅ Predicción realizada correctamente")
            st.subheader("📊 Resultado")
            st.dataframe(resultado, use_container_width=True)

            st.download_button(
                "⬇️ Descargar resultado",
                data=resultado.to_csv(index=False).encode("utf-8"),
                file_name="resultado_prediccion.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error(f"❌ Error en la predicción: {e}")


# =========================
# MODO CSV
# =========================
else:
    st.subheader("📂 Predicción por archivo CSV")

    st.markdown("""
    El archivo debe contener estas columnas:

    `NOMBRE_MUNICIPIO_CURSO`, `NOMBRE_PROGRAMA_ESPECIAL`, `NOMBRE_PROGRAMA_FORMACION`,
    `NOMBRE_RESPONSABLE`, `NIVEL_FORMACION`, `CODIGO_CONVENIO`, `IDENTIFICADOR_FICHA`,
    `FECHA_INICIO_FICHA`, `FECHA_TERMINACION_FICHA`, `NOMBRE_NUEVO_SECTOR`,
    `DURACION_PROGRAMA`, `TOTAL_APRENDICES`, `SECTOR PRODUCTIVO`, `AÑO`
    """)

    archivo = st.file_uploader(
        "Sube tu archivo CSV",
        type=["csv"]
    )

    if archivo is not None:
        df = pd.read_csv(archivo)

        st.subheader("👀 Vista previa del archivo")
        st.dataframe(df.head(), use_container_width=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Filas", df.shape[0])

        with col2:
            st.metric("Columnas", df.shape[1])

        with col3:
            st.metric("Valores perdidos", int(df.isnull().sum().sum()))

        if st.button("🚀 Ejecutar predicción del archivo"):
            try:
                with st.spinner("Procesando archivo en DataRobot..."):
                    resultado = ejecutar_prediccion_batch(df)

                st.success("✅ Predicción finalizada correctamente")
                st.subheader("📊 Resultados")
                st.dataframe(resultado, use_container_width=True)

                st.download_button(
                    "⬇️ Descargar predicciones",
                    data=resultado.to_csv(index=False).encode("utf-8"),
                    file_name="predicciones_datarobot.csv",
                    mime="text/csv"
                )

            except Exception as e:
                st.error(f"❌ Error procesando archivo: {e}")
