import os
import asyncio
import re
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# Carregar envs
load_dotenv()
load_dotenv("../.env.local")
load_dotenv("../../rota-da-festa-web/.env.local")

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Credenciais Supabase em falta.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
geolocator = Nominatim(user_agent="rota_da_festa_bot_v5")

# Cache de estádios para equipas conhecidas do Norte/Aveiro/Porto
CACHE_ESTADIOS = {
    "SC Braga": {"lat": 41.5617, "lon": -8.4309, "local": "Estádio Municipal de Braga"},
    "Braga": {"lat": 41.5617, "lon": -8.4309, "local": "Estádio Municipal de Braga"},
    "Vitória SC": {"lat": 41.4468, "lon": -8.2974, "local": "Estádio D. Afonso Henriques"},
    "Vitória": {"lat": 41.4468, "lon": -8.2974, "local": "Estádio D. Afonso Henriques"},
    "FC Porto": {"lat": 41.1617, "lon": -8.5839, "local": "Estádio do Dragão"},
    "Porto": {"lat": 41.1617, "lon": -8.5839, "local": "Estádio do Dragão"},
    "Boavista": {"lat": 41.1614, "lon": -8.6425, "local": "Estádio do Bessa"},
    "Beira-Mar": {"lat": 40.6416, "lon": -8.6064, "local": "Estádio Municipal de Aveiro"},
    "Feirense": {"lat": 40.9255, "lon": -8.5414, "local": "Estádio Marcolino de Castro"},
    "Famalicão": {"lat": 41.4111, "lon": -8.5273, "local": "Estádio Municipal de Famalicão"},
    "Gil Vicente": {"lat": 41.5372, "lon": -8.6339, "local": "Estádio Cidade de Barcelos"},
    "Rio Ave": {"lat": 41.3638, "lon": -8.7401, "local": "Estádio dos Arcos"},
    "Leixões": {"lat": 41.1833, "lon": -8.7000, "local": "Estádio do Mar"},
    "Varzim": {"lat": 41.3833, "lon": -8.7667, "local": "Estádio do Varzim SC"},
    "Trofense": {"lat": 41.3333, "lon": -8.5500, "local": "Estádio do CD Trofense"},
    "Moreirense": {"lat": 41.3831, "lon": -8.3364, "local": "Parque Comendador Joaquim de Almeida Freitas"},
    "Vizela": {"lat": 41.3789, "lon": -8.3075, "local": "Estádio do FC Vizela"},
    "FC Vizela": {"lat": 41.3789, "lon": -8.3075, "local": "Estádio do FC Vizela"},
    "Arouca": {"lat": 40.9333, "lon": -8.2439, "local": "Estádio Municipal de Arouca"},
    "Oliveirense": {"lat": 40.8386, "lon": -8.4776, "local": "Estádio Carlos Osório"},
    "Académico": {"lat": 41.5503, "lon": -8.4270, "local": "Estádio 1º de Maio, Braga"},
    "Merelinense": {"lat": 41.5768, "lon": -8.4482, "local": "Estádio João Soares Vieira"},
    "Vilaverdense": {"lat": 41.6489, "lon": -8.4356, "local": "Campo Cruz do Reguengo"},
    "Fafe": {"lat": 41.4500, "lon": -8.1667, "local": "Parque Municipal de Desportos de Fafe"},
    "AD Fafe": {"lat": 41.4500, "lon": -8.1667, "local": "Parque Municipal de Desportos de Fafe"},
    "Espinho": {"lat": 41.0068, "lon": -8.6291, "local": "Estádio Comendador Manuel Violas"},
    "SC Espinho": {"lat": 41.0068, "lon": -8.6291, "local": "Estádio Comendador Manuel Violas"},
    "Gondomar": {"lat": 41.1444, "lon": -8.5333, "local": "Estádio de São Miguel"},
    "Leça": {"lat": 41.1833, "lon": -8.7000, "local": "Estádio do Leça FC"},
    "Penafiel": {"lat": 41.2083, "lon": -8.2833, "local": "Estádio Municipal 25 de Abril"},
    "Chaves": {"lat": 41.7431, "lon": -7.4714, "local": "Estádio Municipal Eng. Manuel Branco Teixeira"},
    "Maia": {"lat": 41.2333, "lon": -8.6167, "local": "Estádio Prof. Dr. José Vieira de Carvalho"},
    "Tirsense": {"lat": 41.3444, "lon": -8.4758, "local": "Estádio Municipal de Santo Tirso"},
    "Paços Ferreira": {"lat": 41.2764, "lon": -8.3886, "local": "Estádio Capital do Móvel"},
    "Paços de Ferreira": {"lat": 41.2764, "lon": -8.3886, "local": "Estádio Capital do Móvel"},
    "Felgueiras": {"lat": 41.3642, "lon": -8.1978, "local": "Estádio Municipal de Felgueiras"},
    "Limianos": {"lat": 41.7667, "lon": -8.5833, "local": "Estádio Municipal de Ponte de Lima"},
    "Amarante": {"lat": 41.2717, "lon": -8.0750, "local": "Estádio Municipal de Amarante"},
    "Desportivo de Chaves": {"lat": 41.7431, "lon": -7.4714, "local": "Estádio Municipal Eng. Manuel Branco Teixeira"},
}

# Palavras-chave para filtrar equipas da zona de interesse
ZONAS = [
    "Braga", "Guimarães", "Porto", "Aveiro", "Barcelos", "Famalicão",
    "Feira", "Varzim", "Leixões", "Trofense", "Rio Tinto", "Maia",
    "Espinho", "Ovar", "Arouca", "Vizela", "Moreirense", "Gil Vicente",
    "Rio Ave", "Feirense", "Boavista", "Beira-Mar", "Penafiel", "Chaves",
    "Fafe", "Oliveirense", "Académico", "Merelinense", "Vilaverdense",
    "Gondomar", "Leça", "SC Braga", "Vitória SC", "Vitória", "FC Porto",
    "Tirsense", "Paços", "Felgueiras", "Limianos", "Amarante",
]


def geolocalizar_estadio(nome_equipa: str):
    """Localiza o estádio de uma equipa, primeiro via cache, depois via geocoding."""
    nome_lower = nome_equipa.lower()
    for k, v in CACHE_ESTADIOS.items():
        if k.lower() in nome_lower:
            return v

    try:
        loc = geolocator.geocode(f"Estádio {nome_equipa}, Portugal", timeout=5)
        if loc:
            return {"lat": loc.latitude, "lon": loc.longitude, "local": loc.address.split(",")[0]}
    except Exception:
        pass

    return None


def equipa_na_zona(nome: str) -> bool:
    """Verifica se a equipa pertence a uma zona de interesse."""
    nome_lower = nome.lower()
    return any(z.lower() in nome_lower for z in ZONAS)


def parse_games_from_html(html: str) -> list:
    """Extrai jogos do HTML usando BeautifulSoup (li.game + table fallback)."""
    soup = BeautifulSoup(html, "html.parser")
    jogos_vistos = set()
    resultados = []

    # --- Abordagem 1: Elementos li.game (matchbox/lista) ---
    for li in soup.select("li.game"):
        try:
            link = li.select_one(
                "a[href*='/jogo/'], a[href*='/live-ao-minuto/']"
            )
            if not link:
                continue
            game_url = link.get("href", "")
            if game_url in jogos_vistos:
                continue
            jogos_vistos.add(game_url)

            teams = li.select("div.team span.title")
            if len(teams) < 2:
                continue
            casa = teams[0].get_text(strip=True)
            fora = teams[1].get_text(strip=True)
            if not casa or not fora:
                continue

            # Data do URL: /jogo/YYYY-MM-DD-... ou /live-ao-minuto/YYYY-MM-DD-...
            url_date = re.search(r'/(?:jogo|live-ao-minuto)/(\d{4}-\d{2}-\d{2})', game_url)
            data = url_date.group(1) if url_date else None

            # Hora do elemento date ou fallback para tag time
            hora = None
            date_el = li.select_one("div.date span")
            if date_el:
                time_match = re.search(r'(\d{2}:\d{2})', date_el.get_text())
                hora = time_match.group(1) if time_match else None
            if not hora:
                time_tag = li.select_one("span.tag.time")
                if time_tag:
                    t = time_tag.get_text(strip=True)
                    if re.match(r'\d{2}:\d{2}$', t):
                        hora = t

            if not data or not hora:
                continue

            # Competição
            comp_el = li.select_one("div.comp")
            comp_text = re.sub(r'\s+', ' ', comp_el.get_text(strip=True)) if comp_el else ""

            resultados.append({
                "casa": casa, "fora": fora,
                "data": data, "hora": hora,
                "competicao": comp_text, "url": game_url,
            })
        except Exception:
            continue

    # --- Abordagem 2 (fallback): Tabela principal agenda_list ---
    if not resultados:
        for row in soup.select("table.agenda_list tr"):
            try:
                time_td = row.select_one("td.time")
                info_td = row.select_one("td.info")
                if not time_td or not info_td:
                    continue

                hora = time_td.get_text(strip=True)
                if not re.match(r'\d{2}:\d{2}$', hora):
                    continue

                game_link = info_td.select_one(
                    "a[href*='/jogo/'], a[href*='/live-ao-minuto/']"
                )
                if not game_link:
                    continue
                game_url = game_link.get("href", "")
                if game_url in jogos_vistos:
                    continue
                jogos_vistos.add(game_url)

                game_text = game_link.get_text(strip=True)
                # "Team1 X-Y Team2" ou "Team1 vs Team2"
                vs_match = re.match(r'(.+?)\s+(?:vs|\d+-\d+)\s+(.+)', game_text)
                if not vs_match:
                    continue
                casa = vs_match.group(1).strip()
                fora = vs_match.group(2).strip()

                url_date = re.search(r'/(?:jogo|live-ao-minuto)/(\d{4}-\d{2}-\d{2})', game_url)
                data = url_date.group(1) if url_date else datetime.now().strftime("%Y-%m-%d")

                comp_el = info_td.select_one("div.match_info")
                comp_text = comp_el.get_text(strip=True) if comp_el else ""

                resultados.append({
                    "casa": casa, "fora": fora,
                    "data": data, "hora": hora,
                    "competicao": comp_text, "url": game_url,
                })
            except Exception:
                continue

    return resultados


def classificar_evento(comp_text: str):
    """Retorna (categoria, preço) baseado no texto da competição."""
    cl = comp_text.lower()
    if any(x in cl for x in ["liga portugal", "primeira liga", "liga 3"]):
        return "Liga Portugal", "15€+"
    if any(x in cl for x in ["liga 2", "segunda liga", "meu super"]):
        return "Liga Portugal 2", "10€"
    if any(x in cl for x in ["champions", "europa league", "conference"]):
        return "Competição Europeia", "20€+"
    if any(x in cl for x in ["taça de portugal", "taca de portugal"]):
        return "Taça de Portugal", "10€"
    if any(x in cl for x in ["revelação", "sub-19", "sub-17", "sub-15",
                               "juniores", "juvenis", "iniciados"]):
        return "Formação", "Grátis"
    if any(x in cl for x in ["pro-nacional", "campeonato de portugal"]):
        return "Campeonato de Portugal", "5€"
    return "Futebol Distrital", "5€"


async def load_page(page, url: str, accept_cookies: bool = False, retries: int = 2) -> str:
    """Carrega uma página com retry e devolve o HTML."""
    for attempt in range(retries + 1):
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")

            if accept_cookies:
                try:
                    btn = page.locator("#didomi-notice-agree-button")
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        await page.wait_for_timeout(1000)
                except Exception:
                    pass

            # Esperar pelo conteúdo de jogos
            try:
                await page.wait_for_selector(
                    "li.game, table.agenda_list", timeout=15000
                )
            except Exception:
                pass

            await page.wait_for_timeout(2000)

            title = await page.title()
            if "cloudflare" in title.lower() or "just a moment" in title.lower():
                raise RuntimeError("Cloudflare challenge detectado")

            return await page.content()

        except Exception as e:
            if attempt < retries:
                wait = 5 * (attempt + 1)
                print(f"  ⚠️ Tentativa {attempt + 1} falhou: {e}. Retry em {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(f"  ❌ Falha após {retries + 1} tentativas: {e}")
                return ""
    return ""


async def scrape_zerozero():
    base_url = "https://www.zerozero.pt/agenda.php"
    print("🌍 A iniciar scraping do ZeroZero...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        try:
            all_games = []
            urls_vistos = set()

            # Scrape hoje + próximos 6 dias (cobre o fim-de-semana)
            hoje = datetime.now()
            datas = [(hoje + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

            for idx, data_str in enumerate(datas):
                url = f"{base_url}?date={data_str}"
                print(f"📅 A processar {data_str}...")

                html = await load_page(page, url, accept_cookies=(idx == 0))
                if not html:
                    continue

                jogos = parse_games_from_html(html)
                novos = 0
                for jogo in jogos:
                    if jogo["url"] not in urls_vistos:
                        urls_vistos.add(jogo["url"])
                        all_games.append(jogo)
                        novos += 1
                print(f"   🔍 {len(jogos)} jogos na página, {novos} novos")

            # Filtrar jogos da zona de interesse e construir eventos
            resultados = []
            for jogo in all_games:
                casa, fora = jogo["casa"], jogo["fora"]
                if not equipa_na_zona(casa) and not equipa_na_zona(fora):
                    continue

                geo = geolocalizar_estadio(casa) or geolocalizar_estadio(fora)
                if not geo:
                    continue

                cat, preco = classificar_evento(jogo["competicao"])

                evento = {
                    "nome": f"{casa} vs {fora}",
                    "tipo": "Futebol",
                    "categoria": cat,
                    "data": jogo["data"],
                    "hora": jogo["hora"],
                    "local": geo["local"],
                    "latitude": geo["lat"],
                    "longitude": geo["lon"],
                    "preco": preco,
                    "descricao": f"Jogo de {cat}. {jogo['competicao']}",
                    "url_maps": f"https://www.google.com/maps/search/?api=1&query={geo['lat']},{geo['lon']}",
                    "status": "aprovado",
                }
                resultados.append(evento)
                print(f"  ✅ {evento['nome']} ({jogo['data']} {jogo['hora']})")

            return resultados

        except Exception as e:
            print(f"❌ Erro Scraping: {e}")
            return []
        finally:
            await browser.close()


async def main():
    eventos = await scrape_zerozero()

    if not eventos:
        print("⚠️ Nenhum evento encontrado na zona.")
        return

    print(f"\n📦 A guardar {len(eventos)} eventos no Supabase...")
    for ev in eventos:
        try:
            supabase.table("eventos").upsert(ev, on_conflict="nome,data").execute()
        except Exception as e:
            print(f"  Erro DB: {e}")

    print("🏁 Feito.")


if __name__ == "__main__":
    asyncio.run(main())
