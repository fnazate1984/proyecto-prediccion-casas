import streamlit as st

st.title("🏠 Sistema de Predicción Inmobiliaria")

col1, col2 = st.columns([1,1])

with col1:
    
    #st.title("Sistema Inteligente de Predicción de Viviendas")
        st.markdown("""
                Sistema Inteligente de Predicción de Precios de Viviendas.
    
                Seleccione una opción del menú de la parte superior.
    
                - 🗄️    Scraping - Base de datos
                - 💰    Predicción de viviendas
                - 🤖    Información del Modelo
                """)
        st.markdown("""
<div style="
    background-color:#f8f9fa;
    border-left:6px solid #1f77b4;
    padding:18px;
    border-radius:10px;
    margin-top:20px;
    box-shadow:0px 2px 8px rgba(0,0,0,0.08);
">

<h3 style="margin-bottom:8px;">👨‍🎓 Autor del Proyecto</h3>

<b>Estudiante:</b><br>
<span style="font-size:20px;color:#0d47a1;font-weight:bold;">
Luis Francisco Nazate Maldonado
</span>

<br><br>

<b>Diplomado:</b><br>
<span style="font-size:18px;color:#444;">
Python Full Stack de Cero a Avanzado
</span>

</div>
""", unsafe_allow_html=True)
        
with col2:
    st.image("assets/Portada_ML.png", width=520)