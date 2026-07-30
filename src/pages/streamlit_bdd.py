import streamlit as st
import pandas as pd

#CONFIGURACION GLOBLA
#st.set_page_config(
#    layout="wide", #ESPACIADO
#    page_title="Análisis de Sector Inmobiliario",
#    page_icon=("img\logo.png")
#)
@st.dialog("Información del Proyecto")
def mostrar_info():
    st.markdown("""
    ## Web Scraping

    El proceso de extracción fue desarrollado utilizando
    Python, Selenium y BeautifulSoup.

    Se obtuvieron aproximadamente **60 viviendas**.

    Posteriormente el portal inmobiliario activó un
    mecanismo de protección CAPTCHA que impidió continuar
    con la extracción automática.

    El proyecto fue diseñado para detener el proceso
    automáticamente al detectar dicho mecanismo,
    preservando los datos obtenidos y evitando vulnerar
    las políticas del sitio.
    """)

if st.button("ℹ Información del Proyecto"):
    mostrar_info()
#SIDER ---------------------------------------------------------------------------------------
st.sidebar.title("FILTROS")

cities = ["Guayaquil","Quito","Manta"]

with st.sidebar:
    ciudad_escojida = st.multiselect(
        label="Ciudades",
        options=cities,
        placeholder="Escoja la ciudad"
        )
    
  
    
#DATFRAME LOAD ---------------------------------------------------------------------------------------

#df = pd.read_csv("data/raw/plusvalia_70_raw.csv")
from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "raw" / "houses.sqlite3"


@st.cache_data
def cargar_datos():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"No existe la base SQLite: {DB_PATH}"
        )

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT
                ID,
                CITY,
                PRICE_USD,
                BEDROOMS,
                BATHROOMS,
                PARKING_SPOTS,
                CONSTRUCTION_AREA_SQM,
                TYPE,
                LATITUDE,
                LONGITUDE,
                LINK
            FROM houses
            WHERE LATITUDE IS NOT NULL
              AND LONGITUDE IS NOT NULL
            ORDER BY CITY, PRICE_USD
            """,
            conn,
        )

    return df


try:
    df = cargar_datos()
except Exception as error:
    st.error(f"No fue posible cargar los datos: {error}")
    st.stop()

if ciudad_escojida:
     df= df[df["CITY"].isin(ciudad_escojida)]
    
total_propiedades = len(df)

precio_promedio = df["PRICE_USD"].mean()

median_price = df["PRICE_USD"].median()

area_promedio = df["CONSTRUCTION_AREA_SQM"].mean()

max_price = int(df["PRICE_USD"].max())

#SIDER BAR 2 -------------------------------------------------------

with st.sidebar:
    min_val,max_val = st.slider(
        label="Rango de precios",
        min_value=0,
        max_value=max_price,
        value= (0, max_price),
        step=10000
        )
    
df = df[
    (df["PRICE_USD"] >= min_val) &
    (df["PRICE_USD"] <= max_val)
]
    
#PAGE

st.title("Análisis de Sector Inmobilario")

col1, col2, col3, col4 = st.columns(4) #Columnas realizadas

with col1:
    st.metric(
        label="Total de propiedades",
        value=total_propiedades
    )
    
    with col2:
        st.metric(
        label="Precio Promedio",
        value=f"${precio_promedio:,.2f}"
    )
        
    with col3:
        st.metric(
        label="Mediana de precio",
        value=f"${median_price:.2f}"
    )
        
    with col4:
        st.metric(
        label="Area promedio",
        value=f"{area_promedio:.2f}"
    )
           
#MAPA

col_map, col_df, = st.columns(2) #Columnas realizadas

# df = pd.DataFrame(
#     {
#         "latitude": [-2.19616],
#         "longitude": [-79.88621]
#     }
# )

with col_map:
    map_df = df.copy()

    map_df["LATITUDE"] = pd.to_numeric(
        map_df["LATITUDE"],
        errors="coerce",
    )

    map_df["LONGITUDE"] = pd.to_numeric(
        map_df["LONGITUDE"],
        errors="coerce",
    )

    map_df = map_df.dropna(
        subset=["LATITUDE", "LONGITUDE"]
    )

    if map_df.empty:
        st.warning(
            "No existen registros con coordenadas válidas."
        )
    else:
        st.map(
            map_df,
            latitude="LATITUDE",
            longitude="LONGITUDE",
            size=80,
        )

with col_df:
    st.dataframe(
        df,
        hide_index= False,
        column_config={
            "ID": None,
            "CITY": "Ciudad",
            "PRICE_USD": st.column_config.NumberColumn(
                label = "Precio",
                format="$ %d"
            ),
            "LINK": st.column_config.LinkColumn(
                label="Vinculo",
                display_text="Ver Imagen",
            ) 
        }
    )
    