import streamlit as st



st.set_page_config(
    page_title="Sistema inmobiliario",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)



pagina_home = st.Page(
    "home.py",
    title="HOME",
    icon="🏠",
    default=True,
)

pagina_prediccion = st.Page(
    "streamlit_casas.py",
    title="Predicción de viviendas",
    icon="💰",    
)

pagina_bdd = st.Page(
    "pages/streamlit_bdd.py",
    title="Scraping - Base de datos",
    icon="🗄️",
)
pagina_modelo = st.Page(
    "infomodelo.py",
    title="Información del modelo",
    icon="🤖",
)
pagina_seleccionada = st.navigation(
    [
        pagina_home,
        pagina_bdd,
        pagina_prediccion,
        pagina_modelo,
    ],
    position="top",
)

pagina_seleccionada.run()