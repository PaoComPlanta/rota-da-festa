"""
Scraper de Festas, Concertos, Feiras e Cultura — Rota da Festa
================================================================
Scrape de eventos culturais/festivos em Portugal a partir de:
  1. Eventbrite Portugal (Playwright — renderiza JS)
  2. Classificação automática via Groq LLM

Corre diariamente na GitHub Action após o scraper_mestre.py.
"""

import os
import re
import asyncio
import time
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from playwright.async_api import async_playwright

# Carregar envs
load_dotenv()
load_dotenv("../.env.local")
load_dotenv("../../rota-da-festa-web/.env.local")

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Credenciais Supabase em falta.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
geolocator = Nominatim(user_agent="rota_da_festa_festas_v1")

# ========================================================================
# Cidades/regiões para pesquisar no Eventbrite
# ========================================================================
EVENTBRITE_SEARCHES = [
    # (slug URL, nome da região, lat fallback, lon fallback)
    ("braga--portugal", "Braga", 41.5503, -8.4270),
    ("porto--portugal", "Porto", 41.1496, -8.6109),
    ("lisboa--portugal", "Lisboa", 38.7223, -9.1393),
    ("aveiro--portugal", "Aveiro", 40.6405, -8.6538),
    ("coimbra--portugal", "Coimbra", 40.2109, -8.4377),
    ("faro--portugal", "Faro", 37.0194, -7.9304),
    ("viseu--portugal", "Viseu", 40.6610, -7.9097),
    ("guimaraes--portugal", "Guimarães", 41.4425, -8.2918),
    ("viana-do-castelo--portugal", "Viana do Castelo", 41.6936, -8.8319),
    ("leiria--portugal", "Leiria", 39.7437, -8.8070),
    ("evora--portugal", "Évora", 38.5667, -7.9000),
    ("setubal--portugal", "Setúbal", 38.5244, -8.8882),
    ("funchal--portugal", "Funchal", 32.6669, -16.9241),
]

# Categorias para classificação
CATEGORIAS_FESTAS = {
    "music": "Concerto",
    "festival": "Festa/Romaria",
    "food": "Feira",
    "food-drink": "Feira",
    "performing-arts": "Cultura",
    "arts": "Cultura",
    "sports-fitness": "Desporto",
    "charity": "Cultura",
    "community": "Festa/Romaria",
    "spirituality": "Tradição",
    "holiday": "Festa/Romaria",
    "fashion": "Feira",
    "film-media": "Cultura",
    "science-tech": "Cultura",
    "travel-outdoor": "Cultura",
    "business": "Cultura",
}

# Cache de geocoding para locais de festas
_GEO_CACHE: dict = {}
_GEO_FAILED: set = set()


def geocode_local(local: str, fallback_lat: float = None, fallback_lon: float = None):
    """Geocode um local com cache e fallback."""
    if not local:
        return fallback_lat, fallback_lon, local or "Local TBD"

    local_clean = local.strip()
    cache_key = local_clean.lower()

    if cache_key in _GEO_CACHE:
        c = _GEO_CACHE[cache_key]
        return c["lat"], c["lon"], c["local"]

    if cache_key in _GEO_FAILED:
        return fallback_lat, fallback_lon, local_clean

    # Tentar geocoding
    queries = [
        f"{local_clean}, Portugal",
        local_clean,
    ]

    for q in queries:
        try:
            time.sleep(1.1)
            location = geolocator.geocode(q, timeout=10)
            if location:
                _GEO_CACHE[cache_key] = {
                    "lat": location.latitude,
                    "lon": location.longitude,
                    "local": local_clean,
                }
                return location.latitude, location.longitude, local_clean
        except Exception as e:
            print(f"  ⚠️ Geocoding erro para '{q}': {e}")

    _GEO_FAILED.add(cache_key)
    return fallback_lat, fallback_lon, local_clean


def classify_event_groq(nome: str, descricao: str = "") -> str:
    """Usa Groq para classificar o tipo do evento. Fallback para heurística."""
    text = f"{nome} {descricao}".lower()

    # Heurística rápida (sem API call)
    if any(w in text for w in ["concerto", "música", "concert", "dj", "festival de música", "live music", "rock", "jazz", "hip hop"]):
        return "Concerto"
    if any(w in text for w in ["feira", "mercado", "gastronomia", "artesanato", "food", "market"]):
        return "Feira"
    if any(w in text for w in ["festa", "romaria", "santos", "carnaval", "arraial", "procissão", "holiday", "celebration"]):
        return "Festa/Romaria"
    if any(w in text for w in ["teatro", "exposição", "cinema", "dança", "ballet", "ópera", "museum", "gallery", "art"]):
        return "Cultura"
    if any(w in text for w in ["corrida", "maratona", "trail", "run", "yoga", "fitness", "sport"]):
        return "Desporto"
    if any(w in text for w in ["tradição", "folclore", "popular", "medieval", "históric"]):
        return "Tradição"

    return "Cultura"  # Default


def parse_eventbrite_date(date_str: str) -> tuple:
    """Parseia uma data do Eventbrite (ex: 'Sat, Mar 8, 10:00 AM') → (data, hora)."""
    if not date_str:
        return None, None

    date_str = date_str.strip()

    # Meses em inglês e português
    months = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
        "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04", "maio": "05",
        "junho": "06", "julho": "07", "agosto": "08", "setembro": "09", "outubro": "10",
        "novembro": "11", "dezembro": "12",
    }

    # Pattern: "Sat, Mar 8, 10:00 AM" or "sáb., 8 de mar., 10:00"
    # Try English format first
    m = re.search(r'(\w+)\s+(\d{1,2})(?:,\s*(\d{1,2}:\d{2})\s*(AM|PM)?)?', date_str, re.IGNORECASE)
    if m:
        month_str = m.group(1).lower()[:3]
        day = m.group(2)
        time_str = m.group(3) or ""
        ampm = m.group(4) or ""

        if month_str in months:
            month = months[month_str]
            year = datetime.now().year
            # Se o mês já passou, é do próximo ano
            current_month = datetime.now().month
            if int(month) < current_month - 1:
                year += 1

            data = f"{year}-{month}-{day.zfill(2)}"

            hora = None
            if time_str:
                if ampm.upper() == "PM" and not time_str.startswith("12"):
                    h, mi = time_str.split(":")
                    hora = f"{int(h)+12}:{mi}"
                elif ampm.upper() == "AM" and time_str.startswith("12"):
                    hora = f"00:{time_str.split(':')[1]}"
                else:
                    hora = time_str

            return data, hora

    # Try Portuguese format: "8 de mar." or "8 mar"
    m2 = re.search(r'(\d{1,2})\s+(?:de\s+)?(\w+)\.?(?:,?\s*(\d{1,2}:\d{2}))?', date_str, re.IGNORECASE)
    if m2:
        day = m2.group(1)
        month_str = m2.group(2).lower()[:3]
        time_str = m2.group(3) or ""

        if month_str in months:
            month = months[month_str]
            year = datetime.now().year
            current_month = datetime.now().month
            if int(month) < current_month - 1:
                year += 1
            data = f"{year}-{month}-{day.zfill(2)}"
            return data, time_str or None

    return None, None


async def scrape_eventbrite(page, region_slug: str, region_name: str, fallback_lat: float, fallback_lon: float) -> list:
    """Scrape eventos do Eventbrite para uma região."""
    url = f"https://www.eventbrite.pt/d/{region_slug}/events/"
    eventos = []

    try:
        print(f"\n🌐 Eventbrite: {region_name} ({url})")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Scroll para carregar mais eventos
        for _ in range(3):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Eventbrite usa JSON-LD structured data
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)

                # Normalizar: extrair eventos de diferentes estruturas JSON-LD
                events_raw = []
                if isinstance(data, list):
                    events_raw = data
                elif isinstance(data, dict):
                    if data.get("@type") == "Event":
                        events_raw = [data]
                    elif "itemListElement" in data:
                        # Eventbrite usa ItemList → ListItem → item (Event)
                        for list_item in data["itemListElement"]:
                            inner = list_item.get("item", list_item)
                            events_raw.append(inner)
                    else:
                        events_raw = [data]

                for item in events_raw:
                    if item.get("@type") != "Event":
                        continue

                    nome = item.get("name", "").strip()
                    if not nome:
                        continue

                    # Data
                    start_date = item.get("startDate", "")
                    data_str = start_date[:10] if start_date else None
                    hora = start_date[11:16] if len(start_date) > 16 else None

                    if not data_str:
                        continue

                    # Filtrar: só eventos nos próximos 30 dias
                    try:
                        event_date = datetime.strptime(data_str, "%Y-%m-%d")
                        if event_date < datetime.now() - timedelta(days=1):
                            continue
                        if event_date > datetime.now() + timedelta(days=30):
                            continue
                    except ValueError:
                        continue

                    # Local
                    location = item.get("location", {})
                    local_name = location.get("name", "")
                    address = location.get("address", {})
                    if isinstance(address, dict):
                        street = address.get("streetAddress", "")
                        city = address.get("addressLocality", region_name)
                        local_full = f"{local_name}, {city}" if local_name else city
                    else:
                        local_full = local_name or region_name
                        city = region_name

                    # Coordenadas do JSON-LD
                    geo = location.get("geo", {})
                    lat = geo.get("latitude")
                    lon = geo.get("longitude")

                    if not lat or not lon:
                        lat, lon, _ = geocode_local(local_full, fallback_lat, fallback_lon)

                    # Preço
                    offers = item.get("offers", {})
                    if isinstance(offers, list) and offers:
                        price = offers[0].get("price", "")
                        currency = offers[0].get("priceCurrency", "EUR")
                    elif isinstance(offers, dict):
                        price = offers.get("price", "")
                        currency = offers.get("priceCurrency", "EUR")
                    else:
                        price = ""
                        currency = "EUR"

                    try:
                        price_val = float(price) if price else None
                        if price_val is not None and price_val == 0:
                            preco = "Grátis"
                        elif price_val is not None:
                            preco = f"{price_val}€"
                        else:
                            preco = "Variável"
                    except (ValueError, TypeError):
                        preco = "Variável"

                    # URL
                    url_evento = item.get("url", "")

                    # Descrição
                    descricao = item.get("description", "")[:200] if item.get("description") else ""

                    # Classificação
                    tipo = classify_event_groq(nome, descricao)

                    evento = {
                        "nome": nome,
                        "tipo": tipo,
                        "categoria": tipo,
                        "escalao": "",
                        "equipa_casa": "",
                        "equipa_fora": "",
                        "data": data_str,
                        "hora": hora or "A definir",
                        "local": local_full,
                        "latitude": float(lat) if lat else None,
                        "longitude": float(lon) if lon else None,
                        "preco": preco,
                        "descricao": f"📍 {local_full} | {descricao}" if descricao else f"📍 {local_full}",
                        "url_jogo": url_evento,
                        "url_equipa_casa": "",
                        "url_equipa_fora": "",
                        "url_classificacao": "",
                        "url_maps": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}" if lat and lon else "",
                        "status": "aprovado",
                    }

                    eventos.append(evento)

            except (json.JSONDecodeError, KeyError, TypeError):
                continue

        # Fallback: parse HTML cards if no JSON-LD found
        if not eventos:
            cards = soup.select("a[data-testid='event-card-link'], section.discover-search-desktop-card a")
            for card in cards[:20]:
                try:
                    title_el = card.select_one("h3, [data-testid='event-card-title']")
                    if not title_el:
                        continue
                    nome = title_el.get_text(strip=True)
                    if not nome:
                        continue

                    # Data do card
                    date_el = card.select_one("p[data-testid='event-card-date'], time")
                    date_text = date_el.get_text(strip=True) if date_el else ""
                    data_str, hora = parse_eventbrite_date(date_text)

                    if not data_str:
                        continue

                    # Filtrar: só eventos nos próximos 30 dias
                    try:
                        event_date = datetime.strptime(data_str, "%Y-%m-%d")
                        if event_date < datetime.now() - timedelta(days=1):
                            continue
                        if event_date > datetime.now() + timedelta(days=30):
                            continue
                    except ValueError:
                        continue

                    # Local do card
                    venue_el = card.select_one("p[data-testid='event-card-venue'], .event-card__clamp-line--one")
                    local_text = venue_el.get_text(strip=True) if venue_el else region_name

                    lat, lon, local_clean = geocode_local(local_text, fallback_lat, fallback_lon)
                    tipo = classify_event_groq(nome)
                    url_evento = card.get("href", "")
                    if url_evento and not url_evento.startswith("http"):
                        url_evento = f"https://www.eventbrite.pt{url_evento}"

                    evento = {
                        "nome": nome,
                        "tipo": tipo,
                        "categoria": tipo,
                        "escalao": "",
                        "equipa_casa": "",
                        "equipa_fora": "",
                        "data": data_str,
                        "hora": hora or "A definir",
                        "local": local_clean,
                        "latitude": float(lat) if lat else None,
                        "longitude": float(lon) if lon else None,
                        "preco": "Variável",
                        "descricao": f"📍 {local_clean}",
                        "url_jogo": url_evento,
                        "url_equipa_casa": "",
                        "url_equipa_fora": "",
                        "url_classificacao": "",
                        "url_maps": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}" if lat and lon else "",
                        "status": "aprovado",
                    }
                    eventos.append(evento)
                except Exception:
                    continue

        print(f"  ✅ {region_name}: {len(eventos)} eventos encontrados")

    except Exception as e:
        print(f"  ❌ Erro em {region_name}: {e}")

    return eventos


def deduplicate_events(eventos: list) -> list:
    """Remove duplicados por (nome normalizado, data)."""
    seen = set()
    unique = []
    for ev in eventos:
        key = (ev["nome"].lower().strip(), ev["data"])
        if key not in seen:
            seen.add(key)
            unique.append(ev)
    return unique


async def main():
    print("=" * 60)
    print("🎪 SCRAPER DE FESTAS E CULTURA — Rota da Festa")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    todos_eventos = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="pt-PT",
            timezone_id="Europe/Lisbon",
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-PT', 'pt', 'en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };
        """)
        page = await context.new_page()

        # === FONTE 1: Eventbrite Portugal ===
        print("\n🎫 FONTE: Eventbrite Portugal")
        for slug, name, lat, lon in EVENTBRITE_SEARCHES:
            try:
                eventos = await scrape_eventbrite(page, slug, name, lat, lon)
                todos_eventos.extend(eventos)
                await page.wait_for_timeout(2000)  # Rate limiting
            except Exception as e:
                print(f"  ❌ Falha total em {name}: {e}")

        await browser.close()

    # Deduplicar
    todos_eventos = deduplicate_events(todos_eventos)

    # Filtrar eventos sem coordenadas
    com_geo = [ev for ev in todos_eventos if ev.get("latitude") and ev.get("longitude")]
    sem_geo = len(todos_eventos) - len(com_geo)
    if sem_geo:
        print(f"\n⚠️ {sem_geo} eventos descartados (sem geolocalização)")

    todos_eventos = com_geo

    if not todos_eventos:
        print("\n⚠️ Nenhum evento de cultura/festas encontrado.")
        return

    # Guardar no Supabase (upsert por nome+data)
    print(f"\n📦 A guardar {len(todos_eventos)} eventos culturais no Supabase...")
    guardados = 0
    erros = 0
    for ev in todos_eventos:
        try:
            supabase.table("eventos").upsert(ev, on_conflict="nome,data").execute()
            guardados += 1
        except Exception as e:
            erros += 1
            if erros <= 5:
                print(f"  Erro DB: {e}")

    print(f"\n🏁 Festas scraper feito. {guardados}/{len(todos_eventos)} eventos guardados ({erros} erros).")


if __name__ == "__main__":
    asyncio.run(main())
