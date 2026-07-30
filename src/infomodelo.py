import streamlit as st
import requests
# Cliente HTTP para consumir la API v3.
import pandas as pd
# pandas: para leer CSVs subidos por el usuario y mostrar tablas.
# ── 5. FUNCIONES AUXILIARES ─────────────────────────────────────────────
# Definimos funciones reutilizables para evitar código duplicado.

def conectar_api(endpoint: str, method: str = "GET", json_data: dict = None, timeout: int = 15):
    """
    Llama a un endpoint de la API y maneja errores comunes.

    Args:
        endpoint:   ruta del endpoint (ej: "/health", "/predict").
        method:     método HTTP ("GET" o "POST").
        json_data:  datos a enviar en el body (solo para POST).
        timeout:    segundos máximos de espera.

    Returns:
        Tupla (success: bool, data: dict | str, status_code: int).
        - success=True  → data contiene el JSON de respuesta.
        - success=False → data contiene el mensaje de error.
    """
    url = f"{st.session_state.get('api_url', 'http://localhost:8000')}{endpoint}"
    # Obtenemos la URL de la sesión (configurable en sidebar).
    # .get() con default por si aún no se inicializó.

    try:
        if method == "GET":
            resp = requests.get(url, timeout=timeout)
        else:
            resp = requests.post(url, json=json_data, timeout=timeout)

        if resp.status_code == 200:
            return True, resp.json(), 200
        else:
            # La API devolvió un error (422, 500, 503, etc.).
            try:
                error_data = resp.json()
            except Exception:
                error_data = {"detail": resp.text}
            return False, error_data, resp.status_code

    except requests.exceptions.ConnectionError:
        return False, "No se pudo conectar con la API. ¿Está corriendo?", 0
    except requests.exceptions.Timeout:
        return False, "La API tardó demasiado en responder (timeout).", 0
    except Exception as e:
        return False, f"Error inesperado: {str(e)}", 0

with st.sidebar:

    st.subheader("🔌 Diagnóstico")

    # Llama al health check de la API para verificar conectividad.
        
    if st.button("📊 Cargar info del modelo", use_container_width=True):
        # Carga /model-info y /features en paralelo.
        with st.spinner("Cargando..."):
            ok1, data1, _ = conectar_api("/model-info")
            ok2, data2, _ = conectar_api("/features")

            if ok1:
                st.session_state["model_info"] = data1
                st.success("✅ Model info cargado")
            else:
                st.error(f"❌ /model-info: {data1}")

            if ok2:
                st.session_state["features_list"] = data2
                st.success("✅ Features cargadas")
            else:
                st.error(f"❌ /features: {data2}")

    st.divider()
    st.caption("Streamlit — Avanzada - Modelo")
    st.caption("API — Batch")



st.title("ℹ️ Información del Modelo")

    # ── Si no se cargó desde la sidebar, mostrar instrucción ────────────
if st.session_state["model_info"] is None:
        st.info("ℹ️ Usa **📊 Cargar info del modelo** en la barra lateral para ver los detalles.")
else:
        info = st.session_state["model_info"]

        # ── Tarjetas de resumen ──────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Algoritmo", info.get("tipo", "N/A"))
        with c2:
            st.metric("Árboles", info.get("n_estimators", "N/A"))
        with c3:
            st.metric("Features", info.get("n_features_in_", "N/A"))
        with c4:
            st.metric("Carga (ms)", info.get("tiempo_carga_ms", "N/A"))

        # ── Fecha de carga ──────────────────────────────────────────────
        st.caption(f"Modelo cargado: {info.get('cargado_en', 'N/A')}")

        st.divider()

        # ── Importancias ─────────────────────────────────────────────────
        st.subheader("📊 Importancia de Variables")

        if "importancias" in info:
            # Crear DataFrame ordenado por importancia descendente.
            df_imp = pd.DataFrame(info["importancias"])
            df_imp = df_imp.sort_values("importancia", ascending=True)
            # ascending=True: para que el gráfico de barras horizontales
            # muestre la más importante arriba (Streamlit invierte el eje Y).

            # ── Gráfico de barras ────────────────────────────────────────
            st.bar_chart(
                df_imp.set_index("feature")["importancia"],
                # set_index("feature"): el eje Y muestra nombres de variables.
                # ["importancia"]: la longitud de las barras.

                use_container_width=True,
                horizontal=True,
                # Barras horizontales: más legible con nombres largos de variables.

                x_label="Importancia relativa",
                y_label="Variable",
            )

            # ── Tabla detallada ──────────────────────────────────────────
            with st.expander("📋 Ver tabla de importancias", expanded=False):
                st.dataframe(
                    info["importancias"],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "feature": "Variable",
                        "importancia": st.column_config.ProgressColumn(
                            "Importancia",
                            format="%.4f",
                            min_value=0,
                            max_value=1,
                        ),
                    },
                )

        st.divider()

        # ── Interpretación ───────────────────────────────────────────────
        st.subheader("💡 ¿Cómo interpretar esto?")
        st.markdown("""
        | Variable | Peso | Interpretación |
        |----------|------|----------------|
        | **CONSTRUCTION_AREA_SQM** | ~61% | El tamaño es el factor más determinante del precio. |
        | **LATITUDE + LONGITUDE** | ~28% | La ubicación exacta (barrio/zona) pesa más que la ciudad. |
        | **BATHROOMS** | ~6% | Los baños son más relevantes que las habitaciones para el modelo. |
        | **PARKING_SPOTS** | ~1.5% | Impacto bajo: probablemente correlacionado con el área. |
        | **BEDROOMS** | ~1.2% | Sorprendentemente bajo: el área ya captura el tamaño. |
        | **CITY_\*** | ~2% total | Las coordenadas ya capturan la ubicación mejor que la ciudad. |
        """)

        st.info(
            "💡 **Dato curioso:** El modelo aprendió solo con latitud y longitud "
            "que dentro de una misma ciudad hay zonas caras y baratas. "
            "Por eso las columnas de ciudad (`CITY_*`) tienen poco peso."
        )