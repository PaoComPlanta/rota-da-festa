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
        "nome": "CM Faro",
        "url": "https://www.cm-faro.pt/pt/agenda.aspx",
        "concelho": "Faro",
        "lat": 37.0194, "lon": -7.9304,
        "tipo": "faro",
    },
    {
        "nome": "CM Évora",
        "url": "https://www.cm-evora.pt/municipe/agenda-e-noticias/agenda/lista-de-eventos/",
        "concelho": "Évora",
        "lat": 38.5667, "lon": -7.9000,
        "tipo": "evora",
    },
    {
        "nome": "CM Coimbra",
        "url": "https://www.cm-coimbra.pt/areas/cultura-e-desporto/agenda-cultural",
        "concelho": "Coimbra",
        "lat": 40.2109, "lon": -8.4377,
        "tipo": "generic",
    },
    # NOTE: Removed 7 câmaras with persistently broken URLs (404 / timeout):
    # Guimarães, Viana do Castelo, Vila Real, Bragança, Castelo Branco, Guarda, Santarém
    # Re-add when their agenda pages come back online.
    {
        "nome": "CM Portalegre",
        "url": "https://www.cm-portalegre.pt/agenda",
        "concelho": "Portalegre",
        "lat": 39.2967, "lon": -7.4317,
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

    cards = soup.select("article.card")
    if not cards:
        cards = soup.select("article")

    now = datetime.now()
    for card in cards[:40]:
        try:
            title_el = card.select_one("h2.card__title")
            if not title_el:
                title_el = card.select_one("h2, h3")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            # Data — signpost__date contém "10 março 2026"
            date_el = card.select_one(".signpost__date")
            if not date_el:
                date_el = card.select_one("[class*='date'], time")
            date_text = date_el.get_text(strip=True) if date_el else ""
            data = extract_date_from_text(date_text)
            if not data:
                continue

            # Validar intervalo de datas
            try:
                event_date = datetime.strptime(data, "%Y-%m-%d")
                if event_date < now - timedelta(days=1):
                    continue
                if event_date > now + timedelta(days=90):
                    continue
            except ValueError:
                continue

            # Local — signpost__venue contém nome do espaço
            loc_el = card.select_one(".signpost__venue")
            if not loc_el:
                loc_el = card.select_one("[class*='venue'], [class*='location']")
            local = loc_el.get_text(strip=True) if loc_el else "Lisboa"

            # Categoria — span.subject contém "música", "teatro", etc.
            cat_el = card.select_one("span.subject")
            categoria = cat_el.get_text(strip=True).capitalize() if cat_el else ""

            hora = extract_time_from_text(card.get_text())

            events.append({
                "nome": title[:200],
                "data": data,
                "hora": hora,
                "local": local,
                "lat": 38.7223,
                "lon": -9.1393,
                "descricao_fonte": "AgendaLX",
                "categoria_hint": categoria,
            })
        except Exception as e:
            print(f"  ⚠️ Erro AgendaLX card: {e}")

    print(f"  ✅ AgendaLX: {len(events)} eventos")
    return events


def scrape_faro() -> list:
    """Scrape da agenda da CM Faro."""
    events = []
    print("  📡 A scrapejar CM Faro...")

    soup = fetch_page("https://www.cm-faro.pt/pt/agenda.aspx")
    if not soup:
        return events

    now = datetime.now()
    items = soup.select(".list_agenda li.thumb, .list_agenda .description")
    # Faro uses paired li.thumb + li.description inside .list_agenda ul
    agenda_items = soup.select(".list_agenda > ul")
    if not agenda_items:
        agenda_items = soup.select(".list_agenda")

    for container in agenda_items:
        try:
            title_el = container.select_one("p.title a, .title a, h3 a, h2 a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            text = container.get_text(separator=" ", strip=True)
            data = extract_date_from_text(text)
            if not data:
                continue

            try:
                event_date = datetime.strptime(data, "%Y-%m-%d")
                if event_date < now - timedelta(days=1) or event_date > now + timedelta(days=90):
                    continue
            except ValueError:
                continue

            hora = extract_time_from_text(text)

            loc_el = container.select_one(".local, [class*='local']")
            local = loc_el.get_text(strip=True) if loc_el else "Faro"
            # Extract venue from text patterns like "Local: ..."
            if local == "Faro":
                loc_match = re.search(r"(?:Local|Onde)[:\s]+([^\n|]+)", text)
                if loc_match:
                    local = loc_match.group(1).strip()[:100]

            events.append({
                "nome": title[:200],
                "data": data,
                "hora": hora,
                "local": local,
                "lat": 37.0194,
                "lon": -7.9304,
                "descricao_fonte": "CM Faro",
            })
        except Exception as e:
            print(f"  ⚠️ Erro CM Faro: {e}")

    print(f"  ✅ CM Faro: {len(events)} eventos")
    return events


def scrape_evora() -> list:
    """Scrape da agenda da CM Évora."""
    events = []
    print("  📡 A scrapejar CM Évora...")

    soup = fetch_page("https://www.cm-evora.pt/municipe/agenda-e-noticias/agenda/lista-de-eventos/")
    if not soup:
        return events

    now = datetime.now()
    cards = soup.select(".event-001.small-12")

    for card in cards[:30]:
        try:
            title_el = card.select_one("h2, h3, .event-001-inner-content a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            date_el = card.select_one(".event-001-inner-date-inner")
            date_text = date_el.get_text(strip=True) if date_el else ""
            data = extract_date_from_text(date_text)
            if not data:
                continue

            try:
                event_date = datetime.strptime(data, "%Y-%m-%d")
                if event_date < now - timedelta(days=1) or event_date > now + timedelta(days=90):
                    continue
            except ValueError:
                continue

            hora = extract_time_from_text(card.get_text())

            events.append({
                "nome": title[:200],
                "data": data,
                "hora": hora,
                "local": "Évora",
                "lat": 38.5667,
                "lon": -7.9000,
                "descricao_fonte": "CM Évora",
            })
        except Exception as e:
            print(f"  ⚠️ Erro CM Évora: {e}")

    print(f"  ✅ CM Évora: {len(events)} eventos")
    return events


def extract_jsonld_events(soup: BeautifulSoup, camara: dict) -> list:
    """Tenta extrair eventos de JSON-LD Schema.org."""
    events = []
    now = datetime.now()
    scripts = soup.find_all("script", type="application/ld+json")

    for script in scripts:
        try:
            data = json.loads(script.string)
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                if data.get("@type") == "Event":
                    items = [data]
                elif data.get("@type") == "ItemList":
                    for el in data.get("itemListElement", []):
                        item = el.get("item", el)
                        if item.get("@type") == "Event":
                            items.append(item)
                elif "@graph" in data:
                    items = [i for i in data["@graph"] if i.get("@type") == "Event"]

            for item in items:
                if item.get("@type") != "Event":
                    continue
                nome = item.get("name", "").strip()
                if not nome or len(nome) < 3:
                    continue

                start = item.get("startDate", "")
                data_str = extract_date_from_text(start) or start[:10]
                if not data_str or len(data_str) != 10:
                    continue

                try:
                    event_date = datetime.strptime(data_str, "%Y-%m-%d")
                    if event_date < now - timedelta(days=1) or event_date > now + timedelta(days=90):
                        continue
                except ValueError:
                    continue

                hora = extract_time_from_text(start)
                loc = item.get("location", {})
                local = ""
                if isinstance(loc, dict):
                    local = loc.get("name", "") or loc.get("address", "")
                    if isinstance(local, dict):
                        local = local.get("streetAddress", camara["concelho"])
                local = local or camara["concelho"]

                events.append({
                    "nome": nome[:200],
                    "data": data_str,
                    "hora": hora,
                    "local": str(local)[:200],
                    "lat": camara["lat"],
                    "lon": camara["lon"],
                    "descricao_fonte": camara["nome"],
                })
        except (json.JSONDecodeError, TypeError):
            continue

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

    # Estratégia 1: JSON-LD Schema.org
    jsonld_events = extract_jsonld_events(soup, camara)
    if jsonld_events:
        print(f"  ✅ {nome}: {len(jsonld_events)} eventos (JSON-LD)")
        return jsonld_events

    # Estratégia 2: CSS selectors para blocos de eventos
    selectors = [
        "article", ".event", ".evento", ".agenda-item",
        "[class*='event']", "[class*='evento']",
        ".card", "li.item",
    ]

    cards = []
    for sel in selectors:
        found = soup.select(sel)
        # Filtrar body e elementos demasiado genéricos
        found = [c for c in found if c.name not in ("body", "html", "head", "nav", "header", "footer")]
        if len(found) >= 2:
            cards = found
            break

    if not cards:
        # Fallback: procurar headings com datas próximas
        all_headings = soup.select("h2, h3, h4")
        for h in all_headings:
            parent = h.parent
            if parent and parent.name not in ("body", "html", "nav", "header", "footer"):
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
            skip_words = ["menu", "login", "registar", "pesquisar", "cookies", "privacy", "newsletter", "subscrever"]
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
                "descricao_fonte": nome,
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
            # Geocode se necessário
            lat, lon = ev["lat"], ev["lon"]
            if ev["local"] and ev["local"] != ev.get("descricao_fonte", ""):
                lat, lon = geocode_local(ev["local"], ev["lat"], ev["lon"])

            # Classificar — usar hint de categoria se disponível
            categoria_hint = ev.get("categoria_hint", "")
            if categoria_hint:
                tipo = categoria_hint
            else:
                tipo = classify_event_groq(ev["nome"])

            record = {
                "nome": ev["nome"],
                "tipo": tipo,
                "categoria": "Cultura",
                "escalao": "",
                "equipa_casa": "",
                "equipa_fora": "",
                "data": ev["data"],
                "hora": ev["hora"],
                "local": ev["local"],
                "latitude": lat,
                "longitude": lon,
                "preco": "",
                "descricao": f"Evento publicado por {ev.get('descricao_fonte', 'Câmara Municipal')}",
                "status": "aprovado",
                "url_jogo": "",
                "url_equipa_casa": "",
                "url_equipa_fora": "",
                "url_classificacao": "",
                "url_maps": "",
            }

            result = supabase.table("eventos").upsert(
                record, on_conflict="nome,data"
            ).execute()

            if result.data:
                inserted += 1
            else:
                skipped += 1

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
            elif camara["tipo"] == "faro":
                events = scrape_faro()
            elif camara["tipo"] == "evora":
                events = scrape_evora()
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
