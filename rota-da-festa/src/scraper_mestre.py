import os
import asyncio
import re
from datetime import datetime
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

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Credenciais Supabase em falta.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
geolocator = Nominatim(user_agent="rota_da_festa_bot_v5")

def geolocalizar_estadio(nome_equipa: str):
    # Cache manual para equipas comuns do Norte/Aveiro
    CACHE = {
        "Braga": {"lat": 41.5617, "lon": -8.4309, "local": "Estádio Municipal de Braga"},
        "Vitória SC": {"lat": 41.4468, "lon": -8.2974, "local": "Estádio D. Afonso Henriques"},
        "Porto": {"lat": 41.1617, "lon": -8.5839, "local": "Estádio do Dragão"},
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
        "Arouca": {"lat": 40.9333, "lon": -8.2439, "local": "Estádio Municipal de Arouca"},
        "Oliveirense": {"lat": 40.8386, "lon": -8.4776, "local": "Estádio Carlos Osório"}
    }
    
    for k, v in CACHE.items():
        if k in nome_equipa: return v

    cidades = ["Braga", "Guimarães", "Porto", "Aveiro", "Barcelos", "Maia", "Matosinhos", "Espinho", "Ovar", "Águeda"]
    if any(c in nome_equipa for c in cidades):
        try:
            loc = geolocator.geocode(f"{nome_equipa}, Portugal")
            if loc: return {"lat": loc.latitude, "lon": loc.longitude, "local": loc.address.split(",")[0]}
        except: pass
            
    return None

async def scrape_zerozero():
    url = "https://www.zerozero.pt/agenda.php"
    print(f"🌍 A abrir: {url}")

    async with async_playwright() as p:
        # Browser com Viewport de Desktop para garantir layout correto
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        try:
            await page.goto(url, timeout=90000, wait_until="domcontentloaded")
            
            # Debug: Título da página (ajuda a detetar bloqueios Cloudflare)
            title = await page.title()
            print(f"📄 Título da página: {title}")

            # 1. Tentar aceitar cookies (Seletor específico do ZeroZero/Didomi)
            try:
                print("🍪 A tentar aceitar cookies...")
                await page.click("#didomi-notice-agree-button", timeout=3000)
            except:
                pass # Se falhar, tenta continuar

            # 2. Esperar explicitamente pelos elementos de jogo
            try:
                await page.wait_for_selector(".zz-gameline, tr.parent", timeout=10000)
            except:
                print("⚠️ Timeout à espera da tabela de jogos.")

            # 3. Extrair Jogos
            jogos_els = await page.locator("div.zz-gameline").all()
            if not jogos_els:
                jogos_els = await page.locator("tr.parent").all()

            print(f"🔍 Encontrados {len(jogos_els)} elementos potenciais.")
            
            if len(jogos_els) == 0:
                print("⚠️ Falha na extração. Possível bloqueio ou mudança de layout.")
                return []

            resultados = []
            
            for el in jogos_els:
                texto = await el.inner_text()
                texto_limpo = re.sub(r'\s+', ' ', texto).strip()
                
                if not re.search(r'\d{2}:\d{2}', texto_limpo): continue

                hora = re.search(r'\d{2}:\d{2}', texto_limpo).group(0)
                
                # Extração de equipas mais robusta
                equipas_texto = await el.locator("a").all_inner_texts()
                equipas = [l for l in equipas_texto if len(l) > 2 and not l[0].isdigit()]

                if len(equipas) < 2: continue
                
                casa = equipas[0]
                fora = equipas[1]

                zonas = ["Braga", "Guimarães", "Porto", "Aveiro", "Barcelos", "Famalicão", "Feira", "Varzim", "Leixões", "Trofense", "Rio Tinto", "Maia", "Espinho", "Ovar", "Arouca"]
                if not any(z in casa for z in zonas) and not any(z in fora for z in zonas):
                    continue

                geo = geolocalizar_estadio(casa)
                if not geo: continue

                cat = "Futebol Distrital"
                preco = "5€"
                if "Liga Portugal" in texto_limpo: 
                    cat = "Liga Portugal"
                    preco = "15€+"
                elif any(x in texto_limpo for x in ["Juniores", "Sub-19", "Sub-17"]):
                    cat = "Formação"
                    preco = "Grátis"

                evento = {
                    "nome": f"{casa} vs {fora}",
                    "tipo": "Futebol",
                    "categoria": cat,
                    "data": datetime.now().strftime("%Y-%m-%d"),
                    "hora": hora,
                    "local": geo["local"],
                    "latitude": geo["lat"],
                    "longitude": geo["lon"],
                    "preco": preco,
                    "descricao": f"Jogo extraído do ZeroZero. {cat}",
                    "url_maps": f"https://www.google.com/maps/search/?api=1&query={geo['lat']},{geo['lon']}",
                    "status": "aprovado"
                }
                
                resultados.append(evento)
                print(f"✅ Extraído: {evento['nome']}")

            return resultados

        except Exception as e:
            print(f"❌ Erro Scraping: {e}")
            return []
        finally:
            await browser.close()

async def main():
    eventos = await scrape_zerozero()
    
    if not eventos:
        print("⚠️ Nada encontrado.")
        return

    print(f"\n📦 A guardar {len(eventos)} eventos...")
    for ev in eventos:
        try:
            supabase.table("eventos").upsert(ev, on_conflict="nome,data").execute()
        except Exception as e:
            print(f"Erro DB: {e}")
    
    print("🏁 Feito.")

if __name__ == "__main__":
    asyncio.run(main())
