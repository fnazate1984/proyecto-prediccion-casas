"""
SCRAPER DE PROPIEDADES DE PLUSVALÍA
===================================

Este programa obtiene propiedades de Quito, Guayaquil y Manta, guarda los
resultados en SQLite y exporta dos archivos CSV: uno bruto y otro procesado.

FLUJO GENERAL
-------------
1. Configura ciudades, rutas y objetivos.
2. Abre Chrome con Selenium.
3. Detecta Cloudflare o CAPTCHA.
4. Recorre las ciudades de forma intercalada.
5. Analiza las tarjetas con BeautifulSoup.
6. Extrae precio, área, dormitorios, baños y parqueaderos.
7. Guarda cada registro en SQLite evitando duplicados.
8. Guarda el progreso por ciudad para reanudar.
9. Exporta CSV bruto y CSV limpio.
10. Guarda capturas y HTML de diagnóstico cuando ocurre un problema.

ARCHIVOS GENERADOS
------------------
data/raw/plusvalia_70_balanceado.sqlite3
data/raw/plusvalia_70_balanceado_raw.csv
data/processed/plusvalia_70_balanceado_limpio.csv
"""


from __future__ import annotations

import random
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By


# ============================================================
# 1. CONFIGURACIÓN GENERAL
# ============================================================
BASE_URL = "https://www.plusvalia.com"

SEARCH_URLS = {
    "Manta": "https://www.plusvalia.com/venta/casas/manabi/manta",
}

TARGET_RECORDS = 20
TARGET_BY_CITY = {"Manta": 20}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROFILE_DIR = PROJECT_ROOT / "chrome_profile_plusvalia_70"
DIAGNOSTIC_DIR = RAW_DIR / "diagnosticos_plusvalia_70"

DB_PATH = RAW_DIR / "plusvalia_70.sqlite3"
RAW_CSV = RAW_DIR / "plusvalia_70_raw.csv"
CLEAN_CSV = PROCESSED_DIR / "plusvalia_70_limpio.csv"

MAX_PAGES_PER_CITY = 4
CAPTCHA_WAIT_SECONDS = 200
MIN_DELAY = 12
MAX_DELAY = 20

# Coordenada central aproximada de Manta.
# Se usa solamente como respaldo cuando la tarjeta no contiene coordenadas reales.
CITY_COORDINATES = {
    "Manta": {
        "latitude": -0.9677,
        "longitude": -80.7089,
    },
}

# Pequeña variación visual para evitar que todos los puntos se superpongan.
# Estas coordenadas son aproximadas, no representan la ubicación exacta.
COORDINATE_JITTER = 0.025


# ============================================================
# 2. LIMPIEZA Y CONVERSIÓN DE DATOS
# ============================================================
def clean_text(value) -> str:
    """Normaliza texto eliminando espacios repetidos y valores nulos."""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def now_text() -> str:
    """Devuelve la fecha y hora actual en formato de texto."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def canonical_property_url(url: str) -> str:
    """Normaliza la URL de una propiedad y elimina parámetros para evitar duplicados."""
    absolute = urljoin(BASE_URL, clean_text(url))
    parsed = urlparse(absolute)
    return urlunparse(parsed._replace(query="", fragment="")).rstrip("/")


def navigation_url(url: str) -> str:
    """Normaliza una URL de navegación conservando la paginación."""
    absolute = urljoin(BASE_URL, clean_text(url))
    parsed = urlparse(absolute)
    return urlunparse(parsed._replace(fragment="")).rstrip("/")


def parse_number(value):
    """Convierte textos numéricos con punto o coma en valores float."""
    text = clean_text(value)
    match = re.search(r"[\d.,]+", text)
    if not match:
        return None

    raw = match.group(0)

    if "." in raw and "," in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    elif raw.count(",") > 1:
        raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")

    try:
        return float(raw)
    except ValueError:
        return None


def regex_number(text: str, patterns: list[str]):
    """Busca y convierte el primer número que coincida con los patrones recibidos."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return parse_number(match.group(1))
    return None


# ============================================================
# 3. NAVEGADOR, CLOUDFLARE Y DIAGNÓSTICOS
# ============================================================
def create_driver():
    """Crea y configura Chrome con un perfil persistente de Selenium."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    options = ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--remote-debugging-port=0")
    options.add_argument("--lang=es-EC")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(90)
    return driver


BLOCK_TEXTS = (
    "verifica que tú eres un ser humano",
    "verifica que tu eres un ser humano",
    "verifica que eres humano",
    "cloudflare",
    "ray id:",
    "captcha",
    "checking your browser",
    "servicio de seguridad para protegerse contra bots",
)


def is_blocked(driver) -> bool:
    """Detecta si la página contiene Cloudflare, CAPTCHA u otro bloqueo."""
    try:
        content = " ".join(
            [
                clean_text(driver.title).lower(),
                clean_text(driver.current_url).lower(),
                clean_text(driver.find_element(By.TAG_NAME, "body").text).lower(),
                clean_text(driver.page_source[:150000]).lower(),
            ]
        )
    except WebDriverException:
        return True

    return any(token in content for token in BLOCK_TEXTS)


def wait_for_access(driver, label: str) -> bool:
    """Espera a que el usuario complete la verificación y aparezca el listado real."""
    if not is_blocked(driver):
        return True

    print("\nCloudflare está verificando la sesión.")
    print("Espera hasta que aparezca el listado real.")

    started = time.time()

    while time.time() - started < CAPTCHA_WAIT_SECONDS:
        if not is_blocked(driver):
            print("Verificación superada.")
            time.sleep(6)
            return not is_blocked(driver)

        elapsed = int(time.time() - started)
        if elapsed % 15 in (0, 1):
            print(f"Esperando... {elapsed}/{CAPTCHA_WAIT_SECONDS} segundos")

        time.sleep(2)

    save_diagnostic(driver, label)
    return False


def save_diagnostic(driver, label: str):
    """Guarda una captura PNG y el HTML para revisar errores o cambios del sitio."""
    DIAGNOSTIC_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", label)

    png = DIAGNOSTIC_DIR / f"{safe}_{stamp}.png"
    html = DIAGNOSTIC_DIR / f"{safe}_{stamp}.html"

    try:
        driver.save_screenshot(str(png))
        html.write_text(driver.page_source, encoding="utf-8")
    except Exception:
        pass

    print(f"Diagnóstico guardado en: {DIAGNOSTIC_DIR}")


def scroll_page(driver):
    """Desplaza la página para activar la carga de contenido dinámico."""
    last_height = 0

    for _ in range(8):
        try:
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(1.5)
            height = driver.execute_script("return document.body.scrollHeight")

            if height == last_height:
                break

            last_height = height
        except WebDriverException:
            break

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)


# ============================================================
# 4. SQLITE Y CONTROL DE PROGRESO
# ============================================================
def initialize_db(conn):
    """Crea las tablas properties y crawl_state en SQLite."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS properties (
            url TEXT PRIMARY KEY,
            city TEXT,
            title TEXT,
            location TEXT,
            price_text TEXT,
            price_usd REAL,
            area_text TEXT,
            construction_area_sqm REAL,
            bedrooms REAL,
            bathrooms REAL,
            parking_spots REAL,
            latitude REAL,
            longitude REAL,
            coordinate_source TEXT,
            page_number INTEGER,
            scraped_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS crawl_state (
            city TEXT PRIMARY KEY,
            next_page INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT
        )
        """
    )

    for city in SEARCH_URLS:
        conn.execute(
            """
            INSERT OR IGNORE INTO crawl_state(city, next_page, updated_at)
            VALUES (?, 1, ?)
            """,
            (city, now_text()),
        )

    # Migración sencilla para bases SQLite creadas con versiones anteriores.
    existing_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(properties)").fetchall()
    }

    required_columns = {
        "latitude": "REAL",
        "longitude": "REAL",
        "coordinate_source": "TEXT",
    }

    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            conn.execute(
                f"ALTER TABLE properties ADD COLUMN {column_name} {column_type}"
            )

    conn.commit()


def db_count(conn) -> int:
    """Devuelve el número total de propiedades guardadas."""
    return conn.execute("SELECT COUNT(*) FROM properties").fetchone()[0]


def get_next_page_number(conn, city: str) -> int:
    """Consulta la próxima página pendiente de una ciudad."""
    row = conn.execute(
        "SELECT next_page FROM crawl_state WHERE city = ?",
        (city,),
    ).fetchone()
    return int(row[0]) if row else 1


def update_progress(conn, city: str, next_page: int):
    """Guarda la próxima página que deberá procesarse."""
    conn.execute(
        """
        UPDATE crawl_state
        SET next_page = ?, updated_at = ?
        WHERE city = ?
        """,
        (next_page, now_text(), city),
    )
    conn.commit()


# ============================================================
# 5. EXTRACCIÓN DE TARJETAS
# ============================================================
def looks_like_property_url(url: str) -> bool:
    """Verifica si una URL parece pertenecer a una propiedad."""
    parsed = urlparse(url)
    tail = parsed.path.rstrip("/").split("/")[-1].lower()

    if "plusvalia.com" not in parsed.netloc.lower():
        return False

    return tail.endswith(".html") or bool(re.search(r"\d{5,}", tail))


def extract_url(card):
    """Extrae el enlace principal de una tarjeta de inmueble."""
    for anchor in card.select("a[href]"):
        url = canonical_property_url(anchor.get("href", ""))

        if looks_like_property_url(url):
            return url

    return None


def card_score(card) -> int:
    """Puntúa un bloque HTML para determinar si parece una tarjeta de propiedad."""
    text = clean_text(card.get_text(" ", strip=True))
    score = 0

    if re.search(r"(?:USD|US\$|\$)\s*[\d.,]+", text, re.IGNORECASE):
        score += 3
    if re.search(r"\d+\s*m(?:²|2)", text, re.IGNORECASE):
        score += 2
    if card.select_one("a[href]"):
        score += 1

    return score


def find_cards(soup):
    """Prueba varios selectores CSS, elige el mejor y elimina tarjetas duplicadas."""
    selectors = [
        "[data-qa*='posting']",
        "[data-id]",
        "article",
        "div[class*='posting']",
        "div[class*='card']",
        "li[class*='card']",
        "div[class*='property']",
    ]

    best = []
    best_selector = None

    for selector in selectors:
        candidates = soup.select(selector)
        valid = [card for card in candidates if card_score(card) >= 5]

        print(
            f"Selector {selector}: "
            f"{len(candidates)} candidatos, {len(valid)} válidos"
        )

        if len(valid) > len(best):
            best = valid
            best_selector = selector

    if best_selector:
        print(f"Selector elegido: {best_selector}")

    unique = []
    seen = set()

    for card in best:
        url = extract_url(card)
        if url and url not in seen:
            seen.add(url)
            unique.append(card)

    return unique


def first_text(card, selectors):
    """Devuelve el primer texto encontrado entre varios selectores CSS."""
    for selector in selectors:
        element = card.select_one(selector)
        if element:
            value = clean_text(element.get_text(" ", strip=True))
            if value:
                return value
    return None


def extract_coordinates(card, city: str):
    """
    Intenta extraer LATITUDE y LONGITUDE desde la tarjeta HTML.

    Estrategias:
    1. Atributos HTML frecuentes: data-lat, data-lng, data-latitude,
       data-longitude.
    2. Texto o scripts incluidos dentro de la tarjeta.
    3. Si no existen coordenadas reales, usa el centro aproximado de Manta
       con una pequeña variación para visualizar los puntos en el mapa.

    Retorna:
        tuple(latitude, longitude, coordinate_source)
    """

    # 1. Buscar atributos HTML en la tarjeta y sus descendientes.
    elements = [card] + card.select("*")

    lat_attrs = ("data-lat", "data-latitude", "lat", "latitude")
    lon_attrs = (
        "data-lng",
        "data-lon",
        "data-longitude",
        "lng",
        "lon",
        "longitude",
    )

    for element in elements:
        latitude = None
        longitude = None

        for attr in lat_attrs:
            if element.has_attr(attr):
                latitude = parse_number(element.get(attr))
                if latitude is not None:
                    break

        for attr in lon_attrs:
            if element.has_attr(attr):
                longitude = parse_number(element.get(attr))
                if longitude is not None:
                    break

        if latitude is not None and longitude is not None:
            if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                return latitude, longitude, "html_attribute"

    # 2. Buscar coordenadas dentro del HTML de la tarjeta.
    card_html = str(card)

    lat_patterns = [
        r'["\']latitude["\']\s*[:=]\s*["\']?(-?\d+(?:\.\d+)?)',
        r'["\']lat["\']\s*[:=]\s*["\']?(-?\d+(?:\.\d+)?)',
    ]
    lon_patterns = [
        r'["\']longitude["\']\s*[:=]\s*["\']?(-?\d+(?:\.\d+)?)',
        r'["\']lng["\']\s*[:=]\s*["\']?(-?\d+(?:\.\d+)?)',
        r'["\']lon["\']\s*[:=]\s*["\']?(-?\d+(?:\.\d+)?)',
    ]

    latitude = regex_number(card_html, lat_patterns)
    longitude = regex_number(card_html, lon_patterns)

    if latitude is not None and longitude is not None:
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return latitude, longitude, "embedded_html"

    # 3. Respaldo aproximado por ciudad.
    base = CITY_COORDINATES.get(city)

    if base:
        latitude = base["latitude"] + random.uniform(
            -COORDINATE_JITTER,
            COORDINATE_JITTER,
        )
        longitude = base["longitude"] + random.uniform(
            -COORDINATE_JITTER,
            COORDINATE_JITTER,
        )
        return latitude, longitude, "city_approximate"

    return None, None, "not_available"


def extract_record(card, city: str, page_number: int):
    """Extrae los datos principales de una tarjeta y construye un registro."""
    url = extract_url(card)
    if not url:
        return None

    text = clean_text(card.get_text(" ", strip=True))

    title = first_text(
        card,
        ["h2", "h3", "[data-qa*='title']", "[class*='title']"],
    )

    price_text = first_text(
        card,
        ["[data-qa*='price']", "[class*='price']", "[class*='Price']"],
    )

    if not price_text:
        match = re.search(
            r"(?:USD|US\$|\$)\s*[\d.,]+",
            text,
            re.IGNORECASE,
        )
        price_text = match.group(0) if match else None

    location = first_text(
        card,
        [
            "[data-qa*='location']",
            "[class*='location']",
            "[class*='address']",
            "h4",
        ],
    )

    area_match = re.search(
        r"([\d.,]+)\s*m(?:²|2)",
        text,
        re.IGNORECASE,
    )

    area_text = area_match.group(0) if area_match else None
    area = parse_number(area_match.group(1)) if area_match else None

    latitude, longitude, coordinate_source = extract_coordinates(card, city)

    return {
        "url": url,
        "city": city,
        "title": title,
        "location": location,
        "price_text": price_text,
        "price_usd": parse_number(price_text),
        "area_text": area_text,
        "construction_area_sqm": area,
        "bedrooms": regex_number(
            text,
            [
                r"([\d.,]+)\s*(?:habitaciones?|dormitorios?|hab\.?)",
            ],
        ),
        "bathrooms": regex_number(
            text,
            [r"([\d.,]+)\s*(?:baños?|baño)"],
        ),
        "parking_spots": regex_number(
            text,
            [
                r"([\d.,]+)\s*(?:parqueaderos?|estacionamientos?|garajes?)",
            ],
        ),
        "latitude": latitude,
        "longitude": longitude,
        "coordinate_source": coordinate_source,
        "page_number": page_number,
        "scraped_at": now_text(),
    }


def insert_record(conn, record) -> bool:
    """Inserta una propiedad en SQLite usando INSERT OR IGNORE para evitar duplicados."""
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO properties (
            url, city, title, location, price_text, price_usd,
            area_text, construction_area_sqm, bedrooms, bathrooms,
            parking_spots, latitude, longitude, coordinate_source,
            page_number, scraped_at
        )
        VALUES (
            :url, :city, :title, :location, :price_text, :price_usd,
            :area_text, :construction_area_sqm, :bedrooms, :bathrooms,
            :parking_spots, :latitude, :longitude, :coordinate_source,
            :page_number, :scraped_at
        )
        """,
        record,
    )
    conn.commit()
    return cursor.rowcount == 1


def find_next_url(current_url: str, html: str):
    """Busca el enlace de la siguiente página de resultados."""
    soup = BeautifulSoup(html, "html.parser")
    current = navigation_url(current_url)

    selectors = [
        "a[rel='next']",
        "a[aria-label*='iguiente']",
        "a[data-qa*='next']",
        "li[class*='next'] a",
        "a[class*='next']",
    ]

    candidates = []

    for selector in selectors:
        for anchor in soup.select(selector):
            href = anchor.get("href")
            if href:
                candidates.append(navigation_url(href))

    for anchor in soup.select("a[href]"):
        text = clean_text(anchor.get_text(" ", strip=True)).lower()
        aria = clean_text(anchor.get("aria-label")).lower()

        if (
            "siguiente" in text
            or "siguiente" in aria
            or text in {"›", "»", ">", "next"}
        ):
            candidates.append(navigation_url(anchor["href"]))

    for candidate in dict.fromkeys(candidates):
        if candidate != current:
            return candidate

    return None


# ============================================================
# 6. EXPORTACIÓN Y AVANCE
# ============================================================
def export_csv(conn):
    """Exporta SQLite a un CSV bruto y a otro limpio con precio por metro cuadrado."""
    df = pd.read_sql_query(
        "SELECT * FROM properties ORDER BY scraped_at, url",
        conn,
    )

    # CSV bruto con nombres compatibles con el dashboard y el modelo.
    raw_export = df.rename(
        columns={
            "url": "LINK",
            "city": "CITY",
            "price_usd": "PRICE_USD",
            "construction_area_sqm": "CONSTRUCTION_AREA_SQM",
            "bedrooms": "BEDROOMS",
            "bathrooms": "BATHROOMS",
            "parking_spots": "PARKING_SPOTS",
            "latitude": "LATITUDE",
            "longitude": "LONGITUDE",
            "coordinate_source": "COORDINATE_SOURCE",
        }
    )

    raw_export.to_csv(RAW_CSV, index=False, encoding="utf-8-sig")

    clean = df.drop_duplicates(subset=["url"]).copy()
    clean["model_area_sqm"] = pd.to_numeric(
        clean["construction_area_sqm"],
        errors="coerce",
    )
    clean["price_usd"] = pd.to_numeric(
        clean["price_usd"],
        errors="coerce",
    )
    clean["price_per_sqm"] = (
        clean["price_usd"] / clean["model_area_sqm"]
    )

    clean = clean.rename(
        columns={
            "url": "LINK",
            "city": "CITY",
            "price_usd": "PRICE_USD",
            "construction_area_sqm": "CONSTRUCTION_AREA_SQM",
            "bedrooms": "BEDROOMS",
            "bathrooms": "BATHROOMS",
            "parking_spots": "PARKING_SPOTS",
            "latitude": "LATITUDE",
            "longitude": "LONGITUDE",
            "coordinate_source": "COORDINATE_SOURCE",
        }
    )
    clean.to_csv(CLEAN_CSV, index=False, encoding="utf-8-sig")


def city_count(conn, city: str) -> int:
    """Cuenta cuántos registros existen para una ciudad."""
    return conn.execute(
        "SELECT COUNT(*) FROM properties WHERE city = ?",
        (city,),
    ).fetchone()[0]


def print_progress(conn) -> None:
    """Muestra el avance total y por ciudad."""
    print("\n" + "-" * 52)
    print(f"TOTAL: {db_count(conn)}/{TARGET_RECORDS}")
    for city in SEARCH_URLS:
        print(
            f"{city:<12}: {city_count(conn, city)}/"
            f"{TARGET_BY_CITY[city]}"
        )
    print("-" * 52)


# ============================================================
# 7. PROCESAMIENTO DEL SCRAPING
# ============================================================
def advance_to_saved_page(driver, city: str, first_url: str, saved_page: int):
    """Reconstruye la URL guardada recorriendo la paginación sin extraer."""
    current_url = first_url
    current_page = 1

    while current_page < saved_page:
        try:
            driver.get(current_url)
        except TimeoutException:
            pass
        except WebDriverException as exc:
            print(f"{city}: error al reanudar: {exc}")
            return None

        if not wait_for_access(driver, f"{city}_reanudar_{current_page}"):
            return None

        scroll_page(driver)
        next_url = find_next_url(current_url, driver.page_source)

        if not next_url:
            return None

        current_url = next_url
        current_page += 1
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    return current_url


def process_city_page(driver, conn, city: str, current_url: str, page_number: int):
    """Procesa una sola página y devuelve la URL de la siguiente."""
    if city_count(conn, city) >= TARGET_BY_CITY[city]:
        print(f"{city}: cuota alcanzada.")
        return None, False

    print("\n" + "=" * 72)
    print(f"{city} - página {page_number}")
    print(f"Total actual: {db_count(conn)}/{TARGET_RECORDS}")
    print(f"Ciudad: {city_count(conn, city)}/{TARGET_BY_CITY[city]}")
    print(f"URL: {current_url}")
    print("=" * 72)

    try:
        driver.get(current_url)
    except TimeoutException:
        print("Carga lenta; se intentará continuar.")
    except WebDriverException as exc:
        print(f"{city}: no se pudo abrir la página: {exc}")
        return current_url, False

    if not wait_for_access(driver, f"{city}_pagina_{page_number}"):
        print(f"{city}: Cloudflare no fue superado. Se pasa a otra ciudad.")
        return current_url, False

    scroll_page(driver)

    if is_blocked(driver):
        save_diagnostic(driver, f"{city}_pagina_{page_number}_bloqueada")
        return current_url, False

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    cards = find_cards(soup)

    if not cards:
        print(f"{city}: no se detectaron tarjetas.")
        save_diagnostic(driver, f"{city}_pagina_{page_number}_sin_tarjetas")
        return current_url, False

    inserted = 0
    remaining = TARGET_BY_CITY[city] - city_count(conn, city)

    for card in cards:
        if db_count(conn) >= TARGET_RECORDS or inserted >= remaining:
            break

        record = extract_record(card, city, page_number)

        if record and insert_record(conn, record):
            inserted += 1

    print(f"Tarjetas detectadas: {len(cards)}")
    print(f"Registros nuevos en {city}: {inserted}")

    next_url = find_next_url(current_url, html)
    update_progress(conn, city, page_number + 1)
    export_csv(conn)
    print_progress(conn)

    return next_url, inserted > 0


def scrape(driver, conn):
    """Recorre Quito, Guayaquil y Manta de manera intercalada."""
    city_urls = {}
    city_pages = {}
    active = {}

    for city, first_url in SEARCH_URLS.items():
        saved_page = get_next_page_number(conn, city)
        current_url = advance_to_saved_page(
            driver,
            city,
            first_url,
            saved_page,
        )

        city_urls[city] = current_url or first_url
        city_pages[city] = saved_page
        active[city] = (
            current_url is not None
            and saved_page <= MAX_PAGES_PER_CITY
            and city_count(conn, city) < TARGET_BY_CITY[city]
        )

    while db_count(conn) < TARGET_RECORDS and any(active.values()):
        progress_this_round = False

        for city in SEARCH_URLS:
            if db_count(conn) >= TARGET_RECORDS:
                break

            if not active[city]:
                continue

            if city_pages[city] > MAX_PAGES_PER_CITY:
                active[city] = False
                continue

            next_url, inserted = process_city_page(
                driver,
                conn,
                city,
                city_urls[city],
                city_pages[city],
            )

            if inserted:
                progress_this_round = True

            if (
                city_count(conn, city) >= TARGET_BY_CITY[city]
                or next_url is None
            ):
                active[city] = False
            else:
                city_urls[city] = next_url
                city_pages[city] += 1

            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        if not progress_this_round:
            print(
                "No hubo registros nuevos en esta ronda. "
                "Se detiene para evitar un ciclo infinito."
            )
            break

# ============================================================
# 8. EJECUCIÓN PRINCIPAL
# ============================================================
def main():
    """Inicializa recursos, ejecuta el scraping, exporta resultados y cierra conexiones."""
    for directory in (
        RAW_DIR,
        PROCESSED_DIR,
        PROFILE_DIR,
        DIAGNOSTIC_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    initialize_db(conn)

    driver = create_driver()

    try:
        scrape(driver, conn)
        export_csv(conn)

        print("\n" + "=" * 72)
        print("RESUMEN")
        print("=" * 72)
        print(f"Registros guardados: {db_count(conn)}/{TARGET_RECORDS}")
        print(f"SQLite: {DB_PATH}")
        print(f"CSV bruto: {RAW_CSV}")
        print(f"CSV limpio: {CLEAN_CSV}")

    except KeyboardInterrupt:
        print("\nProceso detenido. El avance quedó guardado.")
        export_csv(conn)

    finally:
        try:
            driver.quit()
        except WebDriverException:
            pass
        conn.close()


if __name__ == "__main__":
    main()