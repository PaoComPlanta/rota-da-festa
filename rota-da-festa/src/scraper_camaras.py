"""
Scraper de Câmaras Municipais — Rota da Festa
===============================================
Scrape de eventos culturais publicados em agendas municipais portuguesas.
Usa requests + BeautifulSoup (sem Playwright) para ser leve e rápido.

Fontes:
  - Câmaras com agenda cultural pública (HTML scraping)
  - Pesquisa genérica em sites municipais

Corre diariamente na GitHub Action após os outros scrapers.
"""

import os
import re
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
import requests

load_dotenv()
load_dotenv("../.env.local")
load_dotenv("../../rota-da-festa-web/.env.local")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Credenciais Supabase em falta.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
geolocator = Nominatim(user_agent="rota_da_festa_camaras_v1")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
}

# ========================================================================
# Câmaras Municipais com agendas culturais conhecidas
# Formato: (nome, url_agenda, seletores CSS, lat, lon)
# ========================================================================
CAMARAS = [
    {
        "nome": "CM Lisboa",
        "url": "https://www.agendalx.pt/events",
        "concelho": "Lisboa",
        "lat": 38.7223, "lon": -9.1393,
        "tipo": "agendalx",
    },
    {
        "nome": "CM Porto",
        "url": "https://www.porto.pt/pt/agenda",
        "concelho": "Porto",
        "lat": 41.1496, "lon": -8.6109,
        "tipo": "porto",
    },
    {
        "nome": "CM Braga",
        "url": "https://www.cm-braga.pt/pt/agenda",
        "concelho": "Braga",
        "lat": 41.5503, "lon": -8.4270,
        "tipo": "generic",
    },
    {
        "nome": "CM Guimarães",
        "url": "https://www.cm-guimaraes.pt/agenda",
        "concelho": "Guimarães",
        "lat": 41.4425, "lon": -8.2918,
        "tipo": "generic",
    },
    {
        "nome": "CM Coimbra",
        "url": "https://www.cm-coimbra.pt/areas/cultura-e-desporto/agenda-cultural",
        "concelho": "Coimbra",
        "lat": 40.2109, "lon": -8.4377,
        "tipo": "generic",
    },
    {
        "nome": "CM Aveiro",
        "url": "https://www.cm-aveiro.pt/municipio/agenda",
        "concelho": "Aveiro",
        "lat": 40.6405, "lon": -8.6538,
        "tipo": "generic",
    },
    {
        "nome": "CM Faro",
        "url": "https://www.cm-faro.pt/pt/agenda.aspx",
        "concelho": "Faro",
        "lat": 37.0194, "lon": -7.9304,
        "tipo": "generic",
    },
    {
        "nome": "CM Viseu",
        "url": "https://www.cm-viseu.pt/pt/agenda/",
        "concelho": "Viseu",
        "lat": 40.6610, "lon": -7.9097,
        "tipo": "generic",
    },
    {
        "nome": "CM Leiria",
        "url": "https://www.cm-leiria.pt/pages/1025",
        "concelho": "Leiria",
        "lat": 39.7437, "lon": -8.8070,
        "tipo": "generic",
    },
    {
        "nome": "CM Setúbal",
        "url": "https://www.mun-setubal.pt/agenda/",
        "concelho": "Setúbal",
        "lat": 38.5244, "lon": -8.8882,
        "tipo": "generic",
    },
    {
        "nome": "CM Viana do Castelo",
        "url": "https://www.cm-viana-castelo.pt/agenda/",
        "concelho": "Viana do Castelo",
        "lat": 41.6936, "lon": -8.8319,
        "tipo": "generic",
    },
    {
        "nome": "CM Évora",
        "url": "https://www.cm-evora.pt/agenda/",
        "concelho": "Évora",
        "lat": 38.5667, "lon": -7.9000,
        "tipo": "generic",
    },
    {
        "nome": "CM Vila Real",
        "url": "https://www.cm-vilareal.pt/index.php/agenda",
        "concelho": "Vila Real",
        "lat": 41.2959, "lon": -7.7464,
        "tipo": "generic",
    },
    {
        "nome": "CM Bragança",
        "url": "https://www.cm-braganca.pt/agenda",
        "concelho": "Bragança",
        "lat": 41.8063, "lon": -6.7572,
        "tipo": "generic",
    },
    {
        "nome": "CM Castelo Branco",
        "url": "https://www.cm-castelobranco.pt/municipe/agenda/",
        "concelho": "Castelo Branco",
        "lat": 39.8228, "lon": -7.4906,
        "tipo": "generic",
    },
    {
        "nome": "CM Guarda",
        "url": "https://www.mun-guarda.pt/agenda/",
        "concelho": "Guarda",
        "lat": 40.5373, "lon": -7.2676,
        "tipo": "generic",
    },
    {
        "nome": "CM Santarém",
        "url": "https://www.cm-santarem.pt/o-municipio/agenda-municipal",
        "concelho": "Santarém",
        "lat": 39.2369, "lon": -8.6850,
        "tipo": "generic",
    },
    {
        "nome": "CM Beja",
        "url": "https://www.cm-beja.pt/viewagenda.do1",
        "concelho": "Beja",
        "lat": 38.0150, "lon": -7.8653,
        "tipo": "generic",
    },
    {
        "nome": "CM Portalegre",
        "url": "https://www.cm-portalegre.pt/agenda",
        "concelho": "Portalegre",
        "lat": 39.2967, "lon": -7.4317,
        "tipo": "generic",
    },
    {
        "nome": "CM Funchal",
        "url": "https://www.cm-funchal.pt/pt/agenda",
        "concelho": "Funchal",
        "lat": 32.6669, "lon": -16.9241,
        "tipo": "generic",
    },
]


# Cache de geocoding
_GEO_CACHE: dict = {}
_GEO_FAILED: set = set()


def geocode_local(local: str, fallback_lat: float, fallback_lon: float):
    """Geocode com cache e fallback."""
    if not local:
        return fallback_lat, fallback_lon

    cache_key = local.strip().lower()
    if cache_key in _GEO_CACHE:
        return _GEO_CACHE[cache_key]
    if cache_key in _GEO_FAILED:
        return fallback_lat, fallback_lon

    for q in [f"{local.strip()}, Portugal", local.strip()]:
        try:
            time.sleep(1.1)
            loc = geolocator.geocode(q, timeout=10)
            if loc:
                _GEO_CACHE[cache_key] = (loc.latitude, loc.longitude)
                return loc.latitude, loc.longitude
        except Exception as e:
            print(f"  ⚠️ Geocoding erro: {e}")

    _GEO_FAILED.add(cache_key)
    return fallback_lat, fallback_lon


def classify_event_groq(title: str, description: str = "") -> str:
    """Classifica evento via Groq LLM."""
    if not GROQ_API_KEY:
        return "Cultura"

    prompt = f"""Classifica este evento cultural português numa destas categorias EXATAS:
- Concerto
- Festa/Romaria
- Feira
- Cultura
- Teatro
- Exposição
- Desporto
- Tradição

Título: {title}
{f'Descrição: {description[:200]}' if description else ''}

Responde APENAS com o nome da categoria."""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 20,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            cat = resp.json()["choices"][0]["message"]["content"].strip()
            valid = ["Concerto", "Festa/Romaria", "Feira", "Cultura", "Teatro", "Exposição", "Desporto", "Tradição"]
            for v in valid:
                if v.lower() in cat.lower():
                    return v
        return "Cultura"
    except Exception:
        return "Cultura"


def make_event_id(nome: str, data: str, local: str) -> str:
    """Gera ID determinístico para deduplicação."""
    raw = f"{nome.strip().lower()}|{data}|{local.strip().lower()}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Fetch page with retries."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
            print(f"  ⚠️ HTTP {resp.status_code} para {url}")
        except Exception as e:
            print(f"  ⚠️ Erro fetch (tentativa {attempt+1}): {e}")
            time.sleep(2)
    return None


def extract_date_from_text(text: str) -> Optional[str]:
    """Tenta extrair data de texto livre português."""
    meses = {
        "janeiro": "01", "fevereiro": "02", "março": "03", "abril": "04",
        "maio": "05", "junho": "06", "julho": "07", "agosto": "08",
        "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12",
        "jan": "01", "fev": "02", "mar": "03", "abr": "04",
        "mai": "05", "jun": "06", "jul": "07", "ago": "08",
        "set": "09", "out": "10", "nov": "11", "dez": "12",
    }

    # dd/mm/yyyy ou dd-mm-yyyy
    m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", text)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"

    # yyyy-mm-dd
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return m.group(0)

    # "dd de mês de yyyy" ou "dd mês yyyy"
    for mes_nome, mes_num in meses.items():
        pattern = rf"(\d{{1,2}})\s+(?:de\s+)?{mes_nome}(?:\s+(?:de\s+)?(\d{{4}}))?"
        m = re.search(pattern, text.lower())
        if m:
            dia = m.group(1).zfill(2)
            ano = m.group(2) or str(datetime.now().year)
            return f"{ano}-{mes_num}-{dia}"

    return None


def extract_time_from_text(text: str) -> str:
    """Extrai hora de texto."""
    m = re.search(r"(\d{1,2})[hH:](\d{2})?", text)
    if m:
        h = m.group(1).zfill(2)
        mins = m.group(2) or "00"
        return f"{h}:{mins}"
    return "21:00"


def scrape_agendalx() -> list:
    """Scrape da Agenda LX (Lisboa)."""
    events = []
    print("  📡 A scrapejar AgendaLX...")

    soup = fetch_page("https://www.agendalx.pt/events")
    if not soup:
        return events

    cards = soup.select("article, .event-card, .event-item, [class*='event']")
    if not cards:
        # Fallback: procurar links com datas
        cards = soup.select("a[href*='/event']")

    for card in cards[:30]:
        try:
            title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
            if not title_el:
                title_el = card if card.name == "a" else card.select_one("a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            # Data
            date_el = card.select_one("time, .date, [class*='date'], [datetime]")
            date_text = date_el.get("datetime", "") or date_el.get_text() if date_el else card.get_text()
            data = extract_date_from_text(str(date_text))
            if not data:
                continue

            # Local
            loc_el = card.select_one(".location, .venue, [class*='location'], [class*='venue']")
            local = loc_el.get_text(strip=True) if loc_el else "Lisboa"

            hora = extract_time_from_text(card.get_text())

            events.append({
                "nome": title[:200],
                "data": data,
                "hora": hora,
                "local": local,
                "lat": 38.7223,
                "lon": -9.1393,
                "fonte": "AgendaLX",
            })
        except Exception as e:
            print(f"  ⚠️ Erro AgendaLX card: {e}")

    print(f"  ✅ AgendaLX: {len(events)} eventos")
    return events


def scrape_generic_agenda(camara: dict) -> list:
    """Scraper genérico para agendas municipais."""
    events = []
    url = camara["url"]
    nome = camara["nome"]

    print(f"  📡 A scrapejar {nome}...")
    soup = fetch_page(url)
    if not soup:
        return events

    # Estratégia: procurar blocos com datas e títulos
    # 1. Procurar elementos comuns de agenda/eventos
    selectors = [
        "article", ".event", ".evento", ".agenda-item",
        "[class*='event']", "[class*='evento']", "[class*='agenda']",
        ".card", ".item", "li.item",
    ]

    cards = []
    for sel in selectors:
        cards = soup.select(sel)
        if len(cards) >= 2:
            break

    if not cards:
        # Fallback: procurar headings com datas próximas
        all_headings = soup.select("h2, h3, h4")
        for h in all_headings:
            parent = h.parent
            if parent:
                text = parent.get_text()
                if extract_date_from_text(text):
                    cards.append(parent)

    for card in cards[:20]:
        try:
            text = card.get_text(separator=" ", strip=True)
            if len(text) < 10:
                continue

            # Título — primeiro heading ou primeiro texto significativo
            title_el = card.select_one("h2, h3, h4, h5, a > strong, strong, .title")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                # Usar primeira linha de texto como título
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                title = lines[0] if lines else ""

            if not title or len(title) < 4:
                continue

            # Filtrar falsos positivos (menus, navigation)
            skip_words = ["menu", "login", "registar", "pesquisar", "cookies", "privacy"]
            if any(w in title.lower() for w in skip_words):
                continue

            # Data
            data = extract_date_from_text(text)
            if not data:
                continue

            # Verificar se a data não é muito antiga
            try:
                event_date = datetime.strptime(data, "%Y-%m-%d")
                if event_date < datetime.now() - timedelta(days=1):
                    continue
                if event_date > datetime.now() + timedelta(days=90):
                    continue
            except ValueError:
                continue

            hora = extract_time_from_text(text)

            # Local
            loc_el = card.select_one(".local, .location, .venue, [class*='local']")
            local = loc_el.get_text(strip=True) if loc_el else camara["concelho"]

            events.append({
                "nome": title[:200],
                "data": data,
                "hora": hora,
                "local": local,
                "lat": camara["lat"],
                "lon": camara["lon"],
                "fonte": nome,
            })
        except Exception as e:
            print(f"  ⚠️ Erro {nome} card: {e}")

    print(f"  ✅ {nome}: {len(events)} eventos")
    return events


def upsert_eventos(events: list):
    """Insere ou atualiza eventos no Supabase."""
    inserted = 0
    skipped = 0
    errors = 0

    for ev in events:
        try:
            event_hash = make_event_id(ev["nome"], ev["data"], ev["local"])

            # Geocode se necessário
            lat, lon = ev["lat"], ev["lon"]
            if ev["local"] and ev["local"] != ev.get("fonte", ""):
                lat, lon = geocode_local(ev["local"], ev["lat"], ev["lon"])

            # Classificar
            tipo = classify_event_groq(ev["nome"])

            record = {
                "nome": ev["nome"],
                "data": ev["data"],
                "hora": ev["hora"],
                "local": ev["local"],
                "latitude": lat,
                "longitude": lon,
                "tipo": tipo,
                "status": "aprovado",
                "fonte": ev.get("fonte", "Câmara Municipal"),
                "descricao": f"Evento publicado por {ev.get('fonte', 'Câmara Municipal')}",
                "url_fonte": "",
                "event_hash": event_hash,
            }

            # Upsert com deduplicação por hash
            existing = supabase.table("eventos").select("id").eq("nome", ev["nome"]).eq("data", ev["data"]).execute()
            if existing.data and len(existing.data) > 0:
                skipped += 1
                continue

            supabase.table("eventos").insert(record).execute()
            inserted += 1

        except Exception as e:
            errors += 1
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                skipped += 1
            else:
                print(f"  ❌ Erro a inserir '{ev['nome']}': {e}")

    return inserted, skipped, errors


def main():
    print("=" * 60)
    print("🏛️  Scraper de Câmaras Municipais — Rota da Festa")
    print("=" * 60)
    start = time.time()

    all_events = []

    for camara in CAMARAS:
        try:
            if camara["tipo"] == "agendalx":
                events = scrape_agendalx()
            else:
                events = scrape_generic_agenda(camara)
            all_events.extend(events)
            time.sleep(2)  # Ser gentil com os servidores
        except Exception as e:
            print(f"  ❌ Erro fatal {camara['nome']}: {e}")

    print(f"\n📊 Total eventos encontrados: {len(all_events)}")

    if all_events:
        inserted, skipped, errors = upsert_eventos(all_events)
        print(f"  ✅ Inseridos: {inserted}")
        print(f"  ⏭️ Duplicados: {skipped}")
        print(f"  ❌ Erros: {errors}")

    elapsed = time.time() - start
    print(f"\n⏱️ Tempo total: {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
