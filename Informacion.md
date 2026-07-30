# Documentacion tomada del curso Diplomado
# Proyecto de implementación

# 📚 Documentación Completa del Proyecto — Predicción Inmobiliaria

> **Curso:** EELA — Módulo Fundamentos de Ciencia de Datos  
> **Objetivo:** Predecir el precio de venta de inmuebles en Ecuador usando Machine Learning  
> **Fecha:** Julio 2025

---

## 🗂️ Índice

1. [Arquitectura General del Proyecto](#1-arquitectura-general-del-proyecto)
2. [`plusvalia_procesado.csv` — Dataset Procesado](#2-plusvalia_procesadocsv--dataset-procesado)
3. [`modelo_inmobiliario.pkl` — Modelo Entrenado](#3-modelo_inmobiliariopkl--modelo-entrenado)
4. [`ejercicio_eela.py` — Notebook de Entrenamiento](#4-ejercicio_eelapy--notebook-de-entrenamiento)
5. [`api_avanzada.py` — API Versión Avanzada](#5-api_avanzadapy--api-versión-avanzada)
6. [Comparativa de las 3 APIs](#6-comparativa-de-las-3-apis)
7. [Guía de Instalación y Ejecución](#7-guía-de-instalación-y-ejecución)
8. [Ejemplos de Peticiones](#8-ejemplos-de-peticiones)
9. [Conceptos Clave para Aprender](#9-conceptos-clave-para-aprender)

---

## 1. Arquitectura General del Proyecto

```
proyecto-prediccion-casas/
├── api
├──── api_avanzada.py                ← FastAPI versión 3: producción
├──assets
├──── Portada_ML.png
├── data
├──── processed
├─────── plusvalia_procesado.csv        ← Datos limpios: 7,459 inmuebles
├──── raw
├─────── houses.csv
├─────── houses.sqlite3
├─────── plantilla_batch.csv
├─────── plusvalia_filtered.csv         ← Datos bruto: 7,459 inmuebles
├─────── test_100_propiedades.csv
├── models
├─────── modelo_inmobiliario.pkl      ← Modelo entrenado (~53 MB)
├── notebooks
├─────── ejercicio_eela.py              ← Script de entrenamiento (Google Colab)
│                                       EDA → limpieza → One-Hot → Regresión
│                                       → Random Forest → exportación
├─────── entrenamiento.ipynb            ← Script de entrenamiento (Google Colab)
│                                       EDA → limpieza → One-Hot → Regresión
│                                       → Random Forest → exportación
├── scraping
├─────── scraper_plusvalia.py           → craping a plusvalia.com
├── src
├─────── pages
├────────── streamlit_bdd.py            → Analisis inmobiliario Base de datos SQLITE3
├─────── app.py                         → Inicial de streamlit
├─────── home.py                        → home
├─────── infomodelo.py                  → informacion entrenamiento modelo
├─────── streamlit_casas.py             → Prediccion precio de casas
├── Informacion.md                      → Informativo proyecto
├── README.md                           → Pasos de instalación
├──requirements.txt                     → Programas necesario para funcionamiento



```

**Flujo de datos:**

```
[plusvalia_filtered.csv]
         │
         ▼
[ejercicio_eela.py]  ── limpieza, EDA, preprocesamiento ──►  [plusvalia_procesado.csv]
         │                                                          │
         │  train_test_split + entrenamiento                        │
         ▼                                                          │
[RandomForestRegressor]                                             │
         │                                                          │
         ▼                                                          │
[modelo_inmobiliario.pkl] ◄─── (carga) ─── [api_*.py] ───►  API REST
                                                      POST /predict
                                                      ───►  precio_usd
```

---

## 2. `plusvalia_procesado.csv` — Dataset Procesado

### 📊 Estadísticas Generales

| Métrica               | Valor                          |
|-----------------------|--------------------------------|
| Filas                 | 7,459                          |
| Columnas              | 10                             |
| Sin valores nulos     | ✅ 0 nulos en todas las columnas |
| Sin duplicados        | ✅ Ya eliminados               |

### 📋 Diccionario de Columnas

| # | Columna                | Tipo    | Descripción |
|---|------------------------|---------|-------------|
| 1 | `PRICE_USD`           | float   | **Variable objetivo** — Precio en USD (ya limpio) |
| 2 | `BEDROOMS`            | int     | Número de habitaciones |
| 3 | `BATHROOMS`           | int     | Número de baños |
| 4 | `PARKING_SPOTS`       | int     | Plazas de estacionamiento |
| 5 | `CONSTRUCTION_AREA_SQM` | float | Área construida en m² |
| 6 | `LATITUDE`            | float   | Latitud (coordenada geográfica) |
| 7 | `LONGITUDE`           | float   | Longitud (coordenada geográfica) |
| 8 | `CITY_Guayaquil`      | int     | 1 = Guayaquil, 0 = no (One-Hot Encoding) |
| 9 | `CITY_Manta`          | int     | 1 = Manta, 0 = no |
|10 | `CITY_Quito`          | int     | 1 = Quito, 0 = no |

### 📈 Estadísticas Descriptivas

```
PRICE_USD:         min =     680 USD   | max = 1,600,000 USD   | media = 338,434 USD
CONSTRUCTION_AREA: min =      40 m²   | max = 5,000 m²       | media = 515 m²
BEDROOMS:          min =       1      | max = 12              | media = 3.9
BATHROOMS:         min =       1      | max = 10              | media = 3.5
PARKING_SPOTS:     min =       1      | max = 10              | media = 2.6
LATITUDE:          min = -2.2682      | max = 0.0461
LONGITUDE:         min = -80.7895     | max = -78.3084
```

### 🏙️ Distribución por Ciudad

| Ciudad    | Registros | Porcentaje |
|-----------|-----------|------------|
| Quito     | 4,551     | 61.0%      |
| Guayaquil | 2,670     | 35.8%      |
| Manta     | 238       | 3.2%       |

> ⚠️ **Desequilibrio de clases:** Manta tiene muy pocos datos (~3%). Esto puede hacer que las predicciones para Manta sean menos fiables.

### 🔄 Preprocesamiento Aplicado

1. **Eliminación de columnas irrelevantes:** `ID`, `LINK` (identificadores sin valor predictivo)
2. **Eliminación de filas duplicadas**
3. **Filtrado de precios irreales:** PRICE_USD < 100 USD eliminados
4. **Capping (Winsorización) al percentil 99:** Los valores extremos de `PRICE_USD`, `BEDROOMS`, `BATHROOMS`, `PARKING_SPOTS` y `CONSTRUCTION_AREA_SQM` se limitan al valor del percentil 99
5. **One-Hot Encoding:** La columna `CITY` (con valores "Quito", "Guayaquil", "Manta") se convierte en 3 columnas binarias

---

## 3. `modelo_inmobiliario.pkl` — Modelo Entrenado

### 🧠 Ficha Técnica

| Característica        | Valor                                |
|-----------------------|--------------------------------------|
| Algoritmo             | `RandomForestRegressor` (scikit-learn) |
| `n_estimators`        | 100 árboles                          |
| `random_state`        | 42 (reproducible)                    |
| Características       | 9 features                           |
| Entrenado con         | 100% del dataset (7,459 registros)   |
| Lenguaje              | Python + joblib (serialización)      |

### 📊 Métricas de Evaluación

> Las métricas se obtuvieron con un split 80/20 (`test_size=0.2`, `random_state=42`).

| Métrica | Regresión Lineal | Random Forest | Mejora |
|---------|-----------------|---------------|--------|
| **R²** (coef. determinación) | 0.4940 (49.4%) | **0.7962 (79.6%)** | +61% |
| **RMSE** (error medio) | $220,124 USD | **$139,736 USD** | -36.5% |

> **¿Qué significa R² = 0.796?**  
> El modelo explica el **79.6% de la variabilidad** de los precios. No es perfecto pero es un muy buen resultado para un modelo no-paramétrico. El 20.4% restante se debe a factores no capturados (calidad de acabados, vista, antigüedad, etc.).

### 🔍 Importancia de Características

| # | Feature                  | Importancia | Interpretación |
|---|--------------------------|-------------|----------------|
| 1 | `CONSTRUCTION_AREA_SQM`  | **~61.3%**  | El tamaño es el factor más determinante |
| 2 | `LATITUDE`               | **~16.6%**  | Ubicación geográfica (microzonas dentro de la ciudad) |
| 3 | `LONGITUDE`              | **~11.3%**  | Complementa la latitud para localización precisa |
| 4 | `BATHROOMS`              | **~6.0%**   | Más relevante que las habitaciones |
| 5 | `PARKING_SPOTS`          | **~1.5%**   | Impacta menos de lo esperado |
| 6 | `BEDROOMS`               | **~1.2%**   | El modelo dice "no tan importante" |
| 7 | `CITY_Manta`             | **~0.8%**   | Manta tiene poco peso (pocos datos) |
| 8 | `CITY_Guayaquil`         | **~0.7%**   | Ciudad con peso bajo |
| 9 | `CITY_Quito`             | **~0.6%**   | Similar a las otras ciudades |

> **Interpretación:** El modelo aprendió que la ubicación exacta (lat/lon) es mucho más informativa que la ciudad en sí. Esto es lógico: dentro de Quito hay zonas caras y zonas baratas, y las coordenadas capturan esa variación.

---

## 4. `entrenamiento.py` — Notebook de Entrenamiento

### 🎯 Objetivo del Script

Script originalmente escrito en **Google Colab** que ejecuta el pipeline completo de ciencia de datos: desde la exploración hasta la exportación del modelo.

### 📐 Estructura (470 líneas)

```
┌─────────────────────────────────────────────────┐
│ FASE 1: EDA (Análisis Exploratorio de Datos)    │
├─────────────────────────────────────────────────┤
│  • Carga del CSV original                       │
│  • .info(), .describe(), .isnull().sum()        │
│  • Boxplots de outliers (antes y después)       │
│  • Explicación teórica de percentil 99          │
│  • Histograma de PRICE_USD                      │
│  • Scatter plot: PRICE vs CONSTRUCTION_AREA     │
│  • Heatmap de correlaciones                     │
│  • Conclusiones del EDA                         │
├─────────────────────────────────────────────────┤
│ FASE 2: Preprocesamiento                        │
├─────────────────────────────────────────────────┤
│  • Drop de columnas ID y LINK                   │
│  • Filtrado PRICE_USD > 100                     │
│  • Capping al percentil 99                      │
│  • One-Hot Encoding de CITY                     │
│  • Exportación a plusvalia_procesado.csv        │
├─────────────────────────────────────────────────┤
│ FASE 3: Modelado                                │
├─────────────────────────────────────────────────┤
│  • Regresión Lineal (baseline)                  │
│  • Train/test split (80/20)                     │
│  • Métricas: MSE, R², RMSE                      │
│  • Coeficientes ordenados por impacto           │
├─────────────────────────────────────────────────┤
│ FASE 4: Random Forest                           │
├─────────────────────────────────────────────────┤
│  • RandomForestRegressor(n_estimators=200)      │
│  • Comparativa de métricas vs Regresión Lineal  │
│  • Feature importance + gráfico de barras        │
│  • Entrenamiento FINAL con 100% de datos        │
│  • Exportación a modelo_inmobiliario.pkl         │
│  • Prueba de predicción individual              │
└─────────────────────────────────────────────────┘
```

### 🧪 Celda de Prueba Final

El script incluye una celda de validación con una propiedad de ejemplo en Quito:

| Atributo | Valor |
|----------|-------|
| Habitaciones | 3 |
| Baños | 2 |
| Parqueaderos | 2 |
| Área | 200 m² |
| Coordenadas | Lat -0.18, Lon -78.48 (Quito centro) |

> El modelo entrega una predicción en USD para esta propiedad.

### 📦 Dependencias del Script

| Librería      | Propósito |
|---------------|-----------|
| `pandas`      | Manipulación de datos |
| `numpy`       | Operaciones numéricas |
| `matplotlib`  | Gráficos (boxplots, histogramas, heatmaps) |
| `seaborn`     | Gráficos estadísticos |
| `scikit-learn` | Modelado (LinearRegression, RandomForest, OneHotEncoder, train_test_split, métricas) |
| `joblib`      | Serialización del modelo (.pkl) |

---


## 5. `api_avanzada.py` — API Versión Avanzada

### 🎯 Propósito

Versión lista para **producción** real. Añade configuración por entorno (12-factor app), middleware, batch prediction, lifespan, CORS y errores estructurados RFC 7807.

### 📐 Arquitectura

```
api_v3_avanzada.py (14 KB ~ 320 líneas)
│
├── class Settings                            ← Config desde variables de entorno
│
├── Lifespan (async context manager)          ← Carga/descarga del modelo
│   ├── startup: joblib.load() + metadatos
│   └── shutdown: model = None
│
├── Middleware
│   ├── CORSMiddleware                        ← Permite peticiones cross-origin
│   └── log_requests (custom middleware)      ← Log de cada request + X-Response-Time
│
├── Modelos Pydantic
│   ├── PropiedadInput  (+ model_validator)   ← Validación de una ciudad
│   ├── PropiedadOutput
│   ├── ErrorDetail (RFC 7807)                ← Errores estructurados
│   ├── BatchInput                            ← Entrada batch (lista de propiedades)
│   └── BatchOutput                           ← Salida batch con métricas
│
├── GET /                                      ← Índice
├── GET /health                                ← {status, modelo_cargado, timestamp}
├── GET /model-info                            ← Metadatos completos del modelo
├── GET /features                              ← Lista de features
├── POST /predict                              ← Predicción individual
├── POST /predict/batch                        ← Predicción masiva (hasta 100)
│
└── Exception handlers                         ← Manejo global de errores
    ├── http_exception_handler
    └── global_exception_handler
```

### 🆕 Novedades Respecto a v2 (y v1)

#### 1. Configuración por Entorno (12-Factor App)

```python
class Settings:
    model_path: str = os.getenv("MODEL_PATH", "modelo_inmobiliario.pkl")
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "info").lower()
    cors_origins: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    max_batch_size: int = int(os.getenv("MAX_BATCH_SIZE", "100"))
```

**¿Por qué variables de entorno?**
- **No hardcodear:** En producción el puerto puede ser 80, el modelo puede estar en `/app/modelos/forest.pkl`.
- **Seguridad:** No pones configuraciones sensibles en el código.
- **Despliegue:** Un mismo código se comporta distinto en dev/staging/prod cambiando solo `.env`.

```bash
# Ejemplo de uso:
export MODEL_PATH=/ruta/alternativa/modelo.pkl
export API_PORT=8080
export MAX_BATCH_SIZE=200
uvicorn api_avanzada:app
```

#### 2. Lifespan (Carga y Descarga Controlada)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, model_info
    model, model_info = cargar_modelo()   # ← Antes de recibir peticiones
    yield                                 # ← La app está viva
    model = None                          # ← Al apagar el servidor
    logger.info("API detenida.")

app = FastAPI(..., lifespan=lifespan)
```

**Alternativa a `lifespan`:**
- v1 y v2 cargan el modelo como variable global (se ejecuta en `import`). Funciona, pero:
  - No puedes hacer tareas asíncronas de setup.
  - No hay "cleanup" controlado al apagar.
  - Si la carga falla, no puedes devolver un error amigable.

**Lifespan** es el mecanismo oficial de FastAPI para eventos de inicio/cierre.

#### 3. CORS Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**¿Qué es CORS?** (Cross-Origin Resource Sharing)

Si tu frontend está en `https://miapp.com` y tu API en `https://api.miapp.com`, el navegador bloquea las peticiones (por seguridad). CORS le dice al navegador: "esta API acepta peticiones desde estos orígenes".

#### 4. Middleware de Logging Personalizado

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)     # ← Ejecuta el endpoint
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s -> %s (%.1f ms)", ...)
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
    return response
```

**¿Qué hace?**
- Mide cuánto tarda CADA petición.
- Añade la cabecera `X-Response-Time-Ms` a todas las respuestas.
- Log automático sin tener que poner `logger.info(...)` en cada endpoint.

#### 5. Validación con `model_validator`

```python
@model_validator(mode="after")
def validar_una_ciudad(self):
    ciudades = [self.city_guayaquil, self.city_manta, self.city_quito]
    if sum(ciudades) != 1:
        raise ValueError(
            f"Exactamente una ciudad debe ser 1. Recibido: Guayaquil={self.city_guayaquil}, ...")
    return self
```

**Diferencia con v2:**
- v2 valida la ciudad en el endpoint (lógica de negocio mezclada con el endpoint).
- v3 valida en el modelo Pydantic (separación de responsabilidades).
- Si otro endpoint usa `PropiedadInput`, la validación se aplica automáticamente.

#### 6. Batch Prediction

```python
@app.post("/predict/batch", response_model=BatchOutput)
async def predict_batch(batch: BatchInput):
    # ...
    df = pd.DataFrame(rows, columns=FEATURES)   # N filas en vez de 1
    preds = model.predict(df).tolist()           # N predicciones de una sola vez
    # ...
```

**¿Por qué batch?**
- `model.predict()` sobre un array de N filas es mucho más rápido que N llamadas individuales (el modelo vectoriza internamente).
- Un solo round-trip HTTP para múltiples predicciones.
- Ideal para valuación de carteras inmobiliarias.

#### 7. Errores Estructurados (RFC 7807)

```python
class ErrorDetail(BaseModel):
    type: str          # URI del tipo de error
    title: str         # Título legible
    status: int        # Código HTTP
    detail: str        # Descripción
    instance: str      # URL que generó el error

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorDetail(
            status=exc.status_code,
            detail=str(exc.detail),
            instance=str(request.url),
        ).model_dump(),
    )
```

**Respuesta de error ejemplo:**
```json
{
    "type": "about:blank",
    "title": "Error de validación",
    "status": 422,
    "detail": "Exactamente una ciudad debe ser 1...",
    "instance": "http://localhost:8000/predict"
}
```

**Ventaja sobre `{"error": "..."}`:**
- Es un estándar (RFC 7807 = Problem Details for HTTP APIs).
- El campo `type` permite que el cliente automatice la reacción al error.
- El campo `instance` ayuda al debugging ("¿en qué endpoint falló?").

#### 8. Endpoint `/model-info`

```python
@app.get("/model-info")
def model_info_endpoint():
    return {
        "tipo": "RandomForestRegressor",
        "n_estimators": 100,
        "n_features_in_": 9,
        "tiempo_carga_ms": 342.15,
        "cargado_en": "2025-07-05T13:01:00",
        "importancias": [...],
    }
```

**Utilidad en producción:**
- Monitorización: ¿el modelo que está sirviendo es el esperado?
- Auditoría: ¿cuándo se cargó? ¿cuánto tardó?
- Debugging: si hay drift, revisas qué features pesaban más.

---

## 6. Comparativa de las 3 APIs

| Característica | v1 Mínima | v2 Intermedia | v3 Avanzada |
|---|---|---|---|
| **Líneas** | ~70 | ~170 | ~320 |
| **Pydantic** | ❌ | ✅ (input + output) | ✅ (input, output, batch, errores) |
| **Validación de rangos** | ❌ | ✅ (`ge=1, le=20`) | ✅ (+ `model_validator`) |
| **Validación de ciudad única** | ❌ | ✅ (en endpoint) | ✅ (en modelo Pydantic) |
| **Logging** | ❌ | ✅ (básico) | ✅ (estructurado + middleware) |
| **CORS** | ❌ | ❌ | ✅ (configurable) |
| **Manejo de errores** | ❌ (traceback) | ✅ (HTTPException) | ✅ (RFC 7807 + handlers globales) |
| **Configuración** | Hardcodeada | Hardcodeada | ✅ (variables de entorno) |
| **Lifespan** | ❌ (global) | ❌ (global) | ✅ (async context manager) |
| **Batch prediction** | ❌ | ❌ | ✅ (hasta 100) |
| **Endpoint /model-info** | ❌ | ❌ | ✅ (metadatos completos) |
| **Endpoint /features** | ❌ | ✅ (básico) | ✅ (con n_features_in_) |
| **Documentación Swagger** | Mínima | Buena | Excelente |
| **Lista para producción** | ❌ | ⚠️ | ✅ |

---

## 7. Guía de Instalación y Ejecución

### 📦 Requisitos Previos

- Python 3.11+ instalado
- pip (gestor de paquetes)

### 🔧 Instalación de Dependencias

```bash
# Opción 1: Instalación mínima (todas las versiones comparten las mismas dependencias)
pip install fastapi uvicorn joblib pandas scikit-learn

# Opción 2: Usando un entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
# Intalacion requirements
pip install -r requirements.txt

pip install fastapi uvicorn joblib pandas scikit-learn
```

### 🚀 Ejecución

```bash
# Navegar a la carpeta del proyecto
cd "api"

# ── (Avanzada) ───────────────────────────────────────────
# Con defaults:
python api/api_avanzada.py

# Con variables de entorno personalizadas:
MODEL_PATH=.models/modelo_inmobiliario.pkl API_PORT=8080 LOG_LEVEL=debug uvicorn api_avanzada:app
```

> El flag `--reload` solo para desarrollo: reinicia el servidor automáticamente al cambiar el código.




### 🧪 Verificar que Funciona

```bash
# Health check (todas las versiones)
curl http://localhost:8000/health

# Documentación interactiva (abre en el navegador)
# http://localhost:8000/docs
```

---

## 8. Ejemplos de Peticiones


### — Batch prediction

```bash
curl -X POST http://localhost:8000/predict/batch \
  -H "Content-Type: application/json" \
  -d '{
    "propiedades": [
      {
        "bedrooms": 3, "bathrooms": 2, "parking_spots": 2,
        "area_m2": 200.0, "lat": -0.18, "lon": -78.48,
        "city_guayaquil": 0, "city_manta": 0, "city_quito": 1
      },
      {
        "bedrooms": 4, "bathrooms": 3, "parking_spots": 2,
        "area_m2": 350.0, "lat": -2.19, "lon": -79.89,
        "city_guayaquil": 1, "city_manta": 0, "city_quito": 0
      }
    ]
  }'
```

### Respuesta típica

```json
{
  "precio_usd": 287452.63,
  "modelo": "Random Forest",
  "version_api": "3.0.0"
}
```

### Error típico (v3)

```json
{
  "type": "about:blank",
  "title": "Error de validación",
  "status": 422,
  "detail": "Exactamente una ciudad debe ser 1 (las demás 0). Recibido: Guayaquil=0, Manta=0, Quito=0",
  "instance": "http://localhost:8000/predict"
}
```

---
## 9. Streamlit
### -----Streamlit---

Streamlit run src/streamlit_app.py

### 🧪 Verificar que Funciona

```bash

curl http://localhost:8501

```

## 10. Conceptos Clave para Aprender

### 🧠 Machine Learning

| Concepto | Definición | Dónde se aplica |
|----------|-----------|-----------------|
| **Random Forest** | Ensemble de árboles de decisión. Cada árbol vota y se promedia. | `modelo_inmobiliario.pkl` |
| **n_estimators** | Número de árboles en el bosque. Más árboles = más robusto pero más lento. | `RandomForestRegressor(n_estimators=100)` |
| **One-Hot Encoding** | Convertir variable categórica en columnas binarias (0/1). | Columna `CITY` → 3 columnas |
| **Winsorización (capping)** | Limitar valores extremos al percentil 99. | `df[col].clip(upper=percentil_99)` |
| **R²** | Coeficiente de determinación: qué % de la variabilidad explica el modelo. | 0.796 = 79.6% |
| **RMSE** | Error promedio en las mismas unidades que la variable objetivo (USD). | $139,736 USD |
| **Feature Importance** | Qué variables pesan más en la decisión del modelo. | `rf.feature_importances_` |
| **Train/Test Split** | Dividir datos en entrenamiento (80%) y prueba (20%) para evaluar sin hacer trampa. | `train_test_split(test_size=0.2)` |
| **Overfitting** | El modelo "memoriza" en vez de "aprender". Se detecta comparando train vs test. | Random Forest lo mitiga con muchos árboles |

### 🌐 FastAPI

| Concepto | Definición | Dónde se aplica |
|----------|-----------|-----------------|
| **Decorador `@app.get()`** | Registra una función como manejador de una ruta HTTP. | Todos los endpoints |
| **Pydantic `BaseModel`** | Clase que valida/parsea datos automáticamente. | `PropiedadInput`, `PropiedadOutput` |
| **`Query(...)`** | Declara un parámetro de query string. `...` = obligatorio. | v1 `/predict` |
| **`Field(ge=1, le=20)`** | Validación de rango. `ge` = greater-or-equal, `le` = less-or-equal. | `PropiedadInput` |
| **`HTTPException`** | Lanza una excepción que FastAPI convierte en respuesta HTTP con código de error. | Validación de ciudad |
| **`response_model`** | Filtra y valida la respuesta automáticamente. | `@app.post(..., response_model=PropiedadOutput)` |
| **Middleware** | Código que se ejecuta antes/después de cada petición. | `log_requests`, `CORSMiddleware` |
| **Lifespan** | Eventos de inicio/cierre de la aplicación. | `@asynccontextmanager` |
| **CORS** | Política de seguridad que controla qué orígenes pueden llamar a la API desde un navegador. | `CORSMiddleware` |
| **`/docs`** | Swagger UI generado automáticamente por FastAPI. | Navegador → `http://localhost:8000/docs` |

### 🐍 Python General

| Concepto | Definición | Dónde se aplica |
|----------|-----------|-----------------|
| **`joblib.load()`** | Deserializa un objeto Python desde un archivo binario. | Carga del modelo |
| **`pd.DataFrame()`** | Estructura tabular de pandas. | Construcción de la entrada para el modelo |
| **`os.getenv()`** | Lee variables de entorno del sistema operativo. | `Settings` en v3 |
| **`if __name__ == "__main__"`** | Bloque que solo se ejecuta si el script es el punto de entrada (no si se importa). | Entry point de cada API |
| **`async/await`** | Programa funciones que no bloquean el hilo principal (concurrencia). | Endpoints en v2 y v3 |
| **`try/except`** | Captura errores sin que el programa se detenga. | Carga del modelo en v2/v3 |

---

## 📝 Resumen 
Este proyecto tomado a partir de las clases recibidas de diplomado incorporación de en un solo proyecto

