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

# ========================================================================
# Cache de estádios — todas as equipas profissionais e semi-profissionais
# ========================================================================
CACHE_ESTADIOS = {
    # --- Liga Portugal (Primeira Liga) ---
    "Benfica": {"lat": 38.7527, "lon": -9.1847, "local": "Estádio da Luz"},
    "Sporting": {"lat": 38.7614, "lon": -9.1608, "local": "Estádio José Alvalade"},
    "FC Porto": {"lat": 41.1617, "lon": -8.5839, "local": "Estádio do Dragão"},
    "SC Braga": {"lat": 41.5617, "lon": -8.4309, "local": "Estádio Municipal de Braga"},
    "Braga": {"lat": 41.5617, "lon": -8.4309, "local": "Estádio Municipal de Braga"},
    "Vitória SC": {"lat": 41.4468, "lon": -8.2974, "local": "Estádio D. Afonso Henriques"},
    "Vitória": {"lat": 41.4468, "lon": -8.2974, "local": "Estádio D. Afonso Henriques"},
    "Moreirense": {"lat": 41.3831, "lon": -8.3364, "local": "Parque Comendador Joaquim de Almeida Freitas"},
    "Famalicão": {"lat": 41.4111, "lon": -8.5273, "local": "Estádio Municipal de Famalicão"},
    "Gil Vicente": {"lat": 41.5372, "lon": -8.6339, "local": "Estádio Cidade de Barcelos"},
    "Rio Ave": {"lat": 41.3638, "lon": -8.7401, "local": "Estádio dos Arcos"},
    "Arouca": {"lat": 40.9333, "lon": -8.2439, "local": "Estádio Municipal de Arouca"},
    "Boavista": {"lat": 41.1614, "lon": -8.6425, "local": "Estádio do Bessa"},
    "Casa Pia": {"lat": 38.7539, "lon": -9.2342, "local": "Estádio Pina Manique"},
    "Estoril": {"lat": 38.7067, "lon": -9.3978, "local": "Estádio António Coimbra da Mota"},
    "Estrela Amadora": {"lat": 38.7539, "lon": -9.2342, "local": "Estádio José Gomes"},
    "Est. Amadora": {"lat": 38.7539, "lon": -9.2342, "local": "Estádio José Gomes"},
    "Santa Clara": {"lat": 37.7500, "lon": -25.6667, "local": "Estádio de São Miguel"},
    "Nacional": {"lat": 32.6476, "lon": -16.9316, "local": "Estádio da Madeira"},
    "AVS": {"lat": 41.3638, "lon": -8.7401, "local": "Estádio dos Arcos"},
    "Farense": {"lat": 37.0156, "lon": -7.9275, "local": "Estádio de São Luís"},
    # --- Liga Portugal 2 ---
    "Leixões": {"lat": 41.1833, "lon": -8.7000, "local": "Estádio do Mar"},
    "Vizela": {"lat": 41.3789, "lon": -8.3075, "local": "Estádio do FC Vizela"},
    "FC Vizela": {"lat": 41.3789, "lon": -8.3075, "local": "Estádio do FC Vizela"},
    "Tondela": {"lat": 40.5167, "lon": -8.0833, "local": "Estádio João Cardoso"},
    "CD Tondela": {"lat": 40.5167, "lon": -8.0833, "local": "Estádio João Cardoso"},
    "Académica": {"lat": 40.2109, "lon": -8.4377, "local": "Estádio Cidade de Coimbra"},
    "Penafiel": {"lat": 41.2083, "lon": -8.2833, "local": "Estádio Municipal 25 de Abril"},
    "Feirense": {"lat": 40.9255, "lon": -8.5414, "local": "Estádio Marcolino de Castro"},
    "Oliveirense": {"lat": 40.8386, "lon": -8.4776, "local": "Estádio Carlos Osório"},
    "Chaves": {"lat": 41.7431, "lon": -7.4714, "local": "Estádio Municipal Eng. Manuel Branco Teixeira"},
    "Desportivo de Chaves": {"lat": 41.7431, "lon": -7.4714, "local": "Estádio Municipal Eng. Manuel Branco Teixeira"},
    "Portimonense": {"lat": 37.1326, "lon": -8.5379, "local": "Estádio Municipal de Portimão"},
    "Marítimo": {"lat": 32.6476, "lon": -16.9316, "local": "Estádio dos Barreiros"},
    "Paços Ferreira": {"lat": 41.2764, "lon": -8.3886, "local": "Estádio Capital do Móvel"},
    "Paços de Ferreira": {"lat": 41.2764, "lon": -8.3886, "local": "Estádio Capital do Móvel"},
    "Varzim": {"lat": 41.3833, "lon": -8.7667, "local": "Estádio do Varzim SC"},
    "Trofense": {"lat": 41.3333, "lon": -8.5500, "local": "Estádio do CD Trofense"},
    "Mafra": {"lat": 38.9400, "lon": -9.3275, "local": "Estádio Municipal Dr. Mário Silveira"},
    "Alverca": {"lat": 38.8953, "lon": -9.0392, "local": "Estádio do FC Alverca"},
    "Benfica B": {"lat": 38.7527, "lon": -9.1847, "local": "Caixa Futebol Campus"},
    "Porto B": {"lat": 41.1617, "lon": -8.5839, "local": "Estádio do Olival"},
    # --- Liga 3 / Campeonato de Portugal ---
    "Beira-Mar": {"lat": 40.6416, "lon": -8.6064, "local": "Estádio Municipal de Aveiro"},
    "Sp. Covilhã": {"lat": 40.2833, "lon": -7.5000, "local": "Estádio Santos Pinto"},
    "Académico Viseu": {"lat": 40.6610, "lon": -7.9097, "local": "Estádio do Fontelo"},
    "Real SC": {"lat": 38.7539, "lon": -9.2342, "local": "Estádio Municipal de Rio Maior"},
    "Belenenses": {"lat": 38.7025, "lon": -9.2067, "local": "Estádio do Restelo"},
    "Cova da Piedade": {"lat": 38.6667, "lon": -9.1500, "local": "Estádio Municipal de Almada"},
    "Felgueiras": {"lat": 41.3642, "lon": -8.1978, "local": "Estádio Municipal de Felgueiras"},
    "Fafe": {"lat": 41.4500, "lon": -8.1667, "local": "Parque Municipal de Desportos de Fafe"},
    "AD Fafe": {"lat": 41.4500, "lon": -8.1667, "local": "Parque Municipal de Desportos de Fafe"},
    "Amarante": {"lat": 41.2717, "lon": -8.0750, "local": "Estádio Municipal de Amarante"},
    "Tirsense": {"lat": 41.3444, "lon": -8.4758, "local": "Estádio Municipal de Santo Tirso"},
    "Gondomar": {"lat": 41.1444, "lon": -8.5333, "local": "Estádio de São Miguel"},
    "Espinho": {"lat": 41.0068, "lon": -8.6291, "local": "Estádio Comendador Manuel Violas"},
    "SC Espinho": {"lat": 41.0068, "lon": -8.6291, "local": "Estádio Comendador Manuel Violas"},
    "Leça": {"lat": 41.1833, "lon": -8.7000, "local": "Estádio do Leça FC"},
    "Maia": {"lat": 41.2333, "lon": -8.6167, "local": "Estádio Prof. Dr. José Vieira de Carvalho"},
    "Limianos": {"lat": 41.7667, "lon": -8.5833, "local": "Estádio Municipal de Ponte de Lima"},
    # --- Regionais ---
    "Académico": {"lat": 41.5503, "lon": -8.4270, "local": "Estádio 1º de Maio, Braga"},
    "Merelinense": {"lat": 41.5768, "lon": -8.4482, "local": "Estádio João Soares Vieira"},
    "Vilaverdense": {"lat": 41.6489, "lon": -8.4356, "local": "Campo Cruz do Reguengo"},
    "Sanjoanense": {"lat": 41.0333, "lon": -8.5000, "local": "Estádio da Sanjoanense"},
    "Anadia": {"lat": 40.4357, "lon": -8.4357, "local": "Estádio Municipal de Anadia"},
    "Lusitano de Évora": {"lat": 38.5667, "lon": -7.9000, "local": "Estádio do Lusitano de Évora"},
    "Vitória Setúbal": {"lat": 38.5244, "lon": -8.8882, "local": "Estádio do Bonfim"},
    "Leiria": {"lat": 39.7500, "lon": -8.8000, "local": "Estádio Dr. Magalhães Pessoa"},
    "Covilhã": {"lat": 40.2833, "lon": -7.5000, "local": "Estádio Santos Pinto"},
}

# Palavras-chave de competições portuguesas
PORTUGUESE_COMP_KEYWORDS = [
    "liga portugal", "primeira liga", "liga 2", "segunda liga", "meu super",
    "liga 3", "campeonato de portugal", "taça de portugal", "taça da liga",
    "supertaça", "liga revelação", "taça revelação",
    "af braga", "af porto", "af aveiro", "af lisboa", "af leiria",
    "af coimbra", "af viseu", "af setúbal", "af santarém", "af beja",
    "pro-nacional", "distrital", "divisão de honra",
]

# Nomes de equipas portuguesas (para detectar em competições internacionais)
PORTUGUESE_TEAMS = [
    "Benfica", "Sporting", "FC Porto", "SC Braga", "Vitória SC", "Moreirense",
    "Famalicão", "Gil Vicente", "Rio Ave", "Arouca", "Boavista", "Casa Pia",
    "Estoril", "Estrela Amadora", "Est. Amadora", "Santa Clara", "Nacional",
    "AVS", "Farense", "Leixões", "FC Vizela", "Tondela", "CD Tondela",
    "Académica", "Penafiel", "Feirense", "Oliveirense", "Chaves",
    "Desportivo de Chaves", "Portimonense", "Marítimo", "Paços de Ferreira",
    "Paços Ferreira", "Varzim", "Trofense", "Mafra", "Alverca", "Benfica B",
    "Porto B", "Beira-Mar", "Sp. Covilhã", "Académico Viseu", "Real SC",
    "Belenenses", "Felgueiras", "Fafe", "AD Fafe", "Amarante", "Tirsense",
    "Gondomar", "Espinho", "SC Espinho", "Leça", "Maia", "Limianos",
    "Académico", "Merelinense", "Vilaverdense", "Sanjoanense", "Anadia",
    "Vitória Setúbal", "Leiria", "Covilhã",
]


def geolocalizar_estadio(nome_equipa: str):
    """Localiza o estádio de uma equipa, primeiro via cache, depois via geocoding."""
    for k, v in CACHE_ESTADIOS.items():
        if _team_match(k, nome_equipa):
            return v

    try:
        loc = geolocator.geocode(f"Estádio {nome_equipa}, Portugal", timeout=5)
        if loc:
            return {"lat": loc.latitude, "lon": loc.longitude, "local": loc.address.split(",")[0]}
    except Exception:
        pass

    return None


def is_portuguese_game(casa: str, fora: str, comp_text: str = "",
                       has_pt_flag: bool = False) -> bool:
    """Verifica se o jogo é português (bandeira PT, competição, ou equipas)."""
    if has_pt_flag:
        return True
    cl = comp_text.lower()
    # Word boundary match para evitar "liga 2" em "bundesliga 25/26"
    if any(re.search(r'(?:^|\b)' + re.escape(kw) + r'(?:\b|$)', cl)
           for kw in PORTUGUESE_COMP_KEYWORDS):
        return True
    return any(
        _team_match(t, casa) or _team_match(t, fora) for t in PORTUGUESE_TEAMS
    )


def _team_match(pt_name: str, team_name: str) -> bool:
    """Verifica se o nome da equipa portuguesa corresponde ao nome dado.
    Evita falsos positivos como 'Nacional' em 'Nacional Potosí'."""
    pl = pt_name.lower()
    tl = team_name.lower().strip()
    if tl == pl:
        return True
    # Aceitar "SC Braga" → "Braga" mas não "Nacional Potosí" → "Nacional"
    return pl in tl and len(pl) / len(tl) > 0.55


def _extract_game_id(url: str) -> str:
    """Extrai o ID numérico do jogo a partir do URL para deduplicação."""
    m = re.search(r'/(\d{6,})(?:\?|$)', url)
    return m.group(1) if m else url


def parse_games_from_html(html: str) -> list:
    """Extrai jogos do HTML usando BeautifulSoup (li.game + tabela, sempre ambos)."""
    soup = BeautifulSoup(html, "html.parser")
    ids_vistos = set()
    resultados = []

    # --- 1. Tabela principal agenda_list (tem nomes completos de competições) ---
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
            gid = _extract_game_id(game_url)
            if gid in ids_vistos:
                continue
            ids_vistos.add(gid)

            game_text = game_link.get_text(strip=True)
            vs_match = re.match(r'(.+?)\s+(?:vs|\d+-\d+)\s+(.+)', game_text)
            if not vs_match:
                continue
            casa = vs_match.group(1).strip()
            fora = vs_match.group(2).strip()

            url_date = re.search(
                r'/(?:jogo|live-ao-minuto)/(\d{4}-\d{2}-\d{2})', game_url
            )
            data = url_date.group(1) if url_date else datetime.now().strftime("%Y-%m-%d")

            comp_el = info_td.select_one("div.match_info")
            comp_text = comp_el.get_text(strip=True) if comp_el else ""

            # Bandeira PT apenas na div da competição (evita falsos positivos)
            comp_img = info_td.select_one("div.main_info div.image")
            has_pt_flag = bool(comp_img and "flag:PT" in str(comp_img))

            resultados.append({
                "casa": casa, "fora": fora,
                "data": data, "hora": hora,
                "competicao": comp_text, "url": game_url,
                "has_pt_flag": has_pt_flag,
            })
        except Exception:
            continue

    # --- 2. Elementos li.game (matchbox / listas laterais) ---
    for li in soup.select("li.game"):
        try:
            link = li.select_one(
                "a[href*='/jogo/'], a[href*='/live-ao-minuto/']"
            )
            if not link:
                continue
            game_url = link.get("href", "")
            gid = _extract_game_id(game_url)
            if gid in ids_vistos:
                continue
            ids_vistos.add(gid)

            teams = li.select("div.team span.title")
            if len(teams) < 2:
                continue
            casa = teams[0].get_text(strip=True)
            fora = teams[1].get_text(strip=True)
            if not casa or not fora:
                continue

            url_date = re.search(
                r'/(?:jogo|live-ao-minuto)/(\d{4}-\d{2}-\d{2})', game_url
            )
            data = url_date.group(1) if url_date else None

            hora = None
            date_el = li.select_one("div.date span")
            if date_el:
                tm = re.search(r'(\d{2}:\d{2})', date_el.get_text())
                hora = tm.group(1) if tm else None
            if not hora:
                time_tag = li.select_one("span.tag.time")
                if time_tag:
                    t = time_tag.get_text(strip=True)
                    if re.match(r'\d{2}:\d{2}$', t):
                        hora = t

            if not data or not hora:
                continue

            comp_el = li.select_one("div.comp")
            comp_text = re.sub(r'\s+', ' ', comp_el.get_text(strip=True)) if comp_el else ""

            # Bandeira PT apenas na div da competição
            comp_img = li.select_one("div.comp div.image")
            has_pt_flag = bool(comp_img and "flag:PT" in str(comp_img))

            resultados.append({
                "casa": casa, "fora": fora,
                "data": data, "hora": hora,
                "competicao": comp_text, "url": game_url,
                "has_pt_flag": has_pt_flag,
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


async def load_page(page, url: str, accept_cookies: bool = False,
                    retries: int = 2) -> str:
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


def limpar_eventos_antigos():
    """Remove da base de dados os eventos com data anterior a hoje."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    try:
        result = supabase.table("eventos").delete().lt("data", hoje).execute()
        n = len(result.data) if result.data else 0
        print(f"🧹 Removidos {n} eventos antigos (antes de {hoje}).")
    except Exception as e:
        print(f"⚠️ Erro ao limpar eventos antigos: {e}")


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
            ids_vistos = set()

            # Scrape hoje + próximos 6 dias (cobre o fim-de-semana)
            hoje = datetime.now()
            datas = [
                (hoje + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)
            ]

            for idx, data_str in enumerate(datas):
                url = f"{base_url}?date={data_str}"
                print(f"📅 A processar {data_str}...")

                html = await load_page(page, url, accept_cookies=(idx == 0))
                if not html:
                    continue

                jogos = parse_games_from_html(html)
                novos = 0
                for jogo in jogos:
                    gid = _extract_game_id(jogo["url"])
                    if gid not in ids_vistos:
                        ids_vistos.add(gid)
                        all_games.append(jogo)
                        novos += 1
                print(f"   🔍 {len(jogos)} jogos na página, {novos} novos")

            # Filtrar: manter apenas jogos portugueses
            resultados = []
            for jogo in all_games:
                casa, fora = jogo["casa"], jogo["fora"]
                if not is_portuguese_game(
                    casa, fora, jogo["competicao"], jogo.get("has_pt_flag", False)
                ):
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
                    "url_maps": (
                        f"https://www.google.com/maps/search/"
                        f"?api=1&query={geo['lat']},{geo['lon']}"
                    ),
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
    # 1. Limpar eventos que já passaram
    limpar_eventos_antigos()

    # 2. Scrape de novos eventos
    eventos = await scrape_zerozero()

    if not eventos:
        print("⚠️ Nenhum evento português encontrado.")
        return

    # 3. Guardar na base de dados
    print(f"\n📦 A guardar {len(eventos)} eventos no Supabase...")
    guardados = 0
    for ev in eventos:
        try:
            supabase.table("eventos").upsert(ev, on_conflict="nome,data").execute()
            guardados += 1
        except Exception as e:
            print(f"  Erro DB: {e}")

    print(f"🏁 Feito. {guardados}/{len(eventos)} eventos guardados com sucesso.")


if __name__ == "__main__":
    asyncio.run(main())
