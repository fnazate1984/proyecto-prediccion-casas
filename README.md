# Instalación

## 1. Clonar el repositorio

```bash
git clone https://github.com/usuario/proyecto-prediccion-casas.git
cd proyecto-prediccion-casas
```

## 2. Crear el entorno virtual

```bash
python -m venv .venv
```

## 3. Activar el entorno virtual

### Windows

```powershell
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

## 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

## 5. Configurar variables de entorno

Copiar el archivo `.env.example` a `.env`.

## 6. Iniciar la API (FastAPI)

```bash
python -m uvicorn api.api_avanzada:app --reload
```

La API estará disponible en:

```
http://127.0.0.1:8000
```

Documentación:

```
http://127.0.0.1:8000/docs
```

## 7. Iniciar la aplicación Streamlit

**En una segunda terminal**, con el entorno virtual activado:

```bash
streamlit run src/app.py
```

La aplicación estará disponible en:

```
http://localhost:8501
```