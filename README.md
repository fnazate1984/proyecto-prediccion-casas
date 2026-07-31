# Instalación

## 1. Clonar el repositorio

```bash
git clone https://github.com/fnazate1984/proyecto-prediccion-casas.git
cd proyecto-prediccion-casas
```

## 2. Crear el entorno virtual

> **Requisito:** Tener instalado **Python 3.11**.

Verifique la versión instalada:

```bash
python --version
```

Debe mostrar un resultado similar a:

```text
Python 3.11.x
```

Crear el entorno virtual con Python 3.11:

```bash
python3.11 -m venv .venv
```

En Windows, si el comando anterior no está disponible:

```bash
py -3.11 -m venv .venv
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