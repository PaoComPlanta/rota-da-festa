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
geolocator = Nominatim(user_agent="rota_da_festa_bot_v4")

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
    
    # 1. Tentar encontrar nome da equipa na cache
    for k, v in CACHE.items():
        if k in nome_equipa: return v

    # 2. Geocoding se for uma equipa com nome de cidade
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
        browser = await p.chromium.launch(headless=True) # Mudar para False se quiseres ver a janela a abrir
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()

        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # 1. Tentar aceitar cookies (vários seletores possíveis)
            try:
                print("🍪 A tentar aceitar cookies...")
                await page.click("button:has-text('Aceitar')", timeout=3000)
                await page.click("button:has-text('Concordo')", timeout=3000)
            except:
                pass # Se não encontrar botão, segue em frente

            # 2. Esperar pela tabela de jogos
            await page.wait_for_timeout(3000) # Espera 3s para JS carregar
            
            # Extrair jogos usando seletores genéricos de estrutura
            # O ZeroZero organiza jogos em linhas com classe 'parent' ou dentro de divs 'zz-gameline'
            jogos_els = await page.locator("div.zz-gameline").all()
            
            if not jogos_els:
                # Fallback para estrutura antiga de tabela
                jogos_els = await page.locator("tr.parent").all()

            print(f"🔍 Encontrados {len(jogos_els)} elementos potenciais.")

            resultados = []
            
            for el in jogos_els:
                texto = await el.inner_text()
                
                # Limpeza básica
                texto_limpo = re.sub(r'\s+', ' ', texto).strip()
                
                # Ignorar se não tiver hora (formato HH:MM)
                if not re.search(r'\d{2}:\d{2}', texto_limpo):
                    continue

                # Extrair hora
                hora = re.search(r'\d{2}:\d{2}', texto_limpo).group(0)

                # Tentar extrair equipas (links dentro do elemento)
                links = await el.locator("a").all_inner_texts()
                # Filtrar links vazios ou curtos (ex: "VS", "-")
                equipas = [l for l in links if len(l) > 2 and not l[0].isdigit()]

                if len(equipas) < 2: continue
                
                casa = equipas[0]
                fora = equipas[1]

                # Filtro Geográfico (Norte/Aveiro)
                zonas = ["Braga", "Guimarães", "Porto", "Aveiro", "Barcelos", "Famalicão", "Feira", "Varzim", "Leixões", "Trofense", "Rio Tinto", "Maia", "Espinho", "Ovar", "Arouca"]
                if not any(z in casa for z in zonas) and not any(z in fora for z in zonas):
                    continue

                # Geolocalizar
                geo = geolocalizar_estadio(casa)
                if not geo: continue

                # Determinar Categoria e Preço
                cat = "Futebol Distrital"
                preco = "5€"
                if "Liga Portugal" in texto_limpo: 
                    cat = "Liga Portugal"
                    preco = "15€+"
                elif any(x in texto_limpo for x in ["Juniores", "Sub-19", "Sub-17"]):
                    cat = "Formação"
                    preco = "Grátis"

                # Objeto Final
                evento = {
                    "nome": f"{casa} vs {fora}",
                    "tipo": "Futebol",
                    "categoria": cat,
                    "data": datetime.now().strftime("%Y-%m-%d"), # Assume hoje
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
        print("⚠️ Nada encontrado. Tenta rodar de novo ou verifica se o site está acessível.")
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
