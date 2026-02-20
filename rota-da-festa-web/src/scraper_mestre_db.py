import os
import json
import random
import time
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

# Carregar variáveis de ambiente (se existirem localmente)
load_dotenv()

# ==========================================
# CONFIGURAÇÃO SUPABASE
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("⚠️ Erro: SUPABASE_URL e SUPABASE_SERVICE_KEY são obrigatórios.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ==========================================
# DADOS BASE (Simulação de Scraping Real)
# ==========================================
# Em produção, aqui entrariam os requests + BeautifulSoup
# Para este MVP, usamos os dados de alta qualidade que gerámos antes

ESTADIOS_DISTRITAIS = [
    {"equipa": "Merelinense FC", "estadio": "Estádio João Soares Vieira", "lat": 41.5768, "lon": -8.4482, "zona": "Braga"},
    {"equipa": "Maria da Fonte", "estadio": "Estádio Moinhos Novos", "lat": 41.6032, "lon": -8.2589, "zona": "Braga"},
    {"equipa": "Dumiense FC", "estadio": "Campo Celestino Lobo", "lat": 41.5621, "lon": -8.4328, "zona": "Braga"},
    {"equipa": "Vilaverdense", "estadio": "Campo Cruz do Reguengo", "lat": 41.6489, "lon": -8.4356, "zona": "Braga"},
    {"equipa": "GD Joane", "estadio": "Estádio de Barreiros", "lat": 41.4333, "lon": -8.4167, "zona": "Braga"},
    {"equipa": "SC Beira-Mar", "estadio": "Estádio Municipal de Aveiro", "lat": 40.6416, "lon": -8.6064, "zona": "Aveiro"},
    {"equipa": "SC Rio Tinto", "estadio": "Estádio Cidade de Rio Tinto", "lat": 41.1764, "lon": -8.5583, "zona": "Porto"},
]

LOCAIS_CULTURA = [
    {"nome": "Pavilhão Multiusos de Guimarães", "lat": 41.4417, "lon": -8.3032, "zona": "Braga"},
    {"nome": "Praça da República (Braga)", "lat": 41.5515, "lon": -8.4216, "zona": "Braga"},
    {"nome": "Casa da Música (Porto)", "lat": 41.1589, "lon": -8.6307, "zona": "Porto"},
]

# ==========================================
# LÓGICA DE GERAÇÃO
# ==========================================

def get_random_weekend_date(base_date, weeks_offset=0):
    days_until_sat = (5 - base_date.weekday() + 7) % 7
    if days_until_sat == 0: days_until_sat = 7
    next_saturday = base_date + timedelta(days=days_until_sat + (weeks_offset * 7))
    next_sunday = next_saturday + timedelta(days=1)
    return random.choice([next_saturday, next_sunday])

def gerar_eventos_para_db():
    print("🚀 A iniciar ingestão de dados para Supabase...")
    base_date = datetime.now()
    eventos_para_inserir = []

    # 1. Gerar Futebol
    for _ in range(30):
        home = random.choice(ESTADIOS_DISTRITAIS)
        adversario = random.choice(["Estarreja", "Prado", "Serzedelo", "Vila Meã", "Canidelo"])
        
        data_jogo = get_random_weekend_date(base_date, random.randint(0, 3))
        if data_jogo.weekday() == 5: data_jogo += timedelta(days=1) # Domingo

        eventos_para_inserir.append({
            "nome": f"{home['equipa']} vs {adversario}",
            "tipo": "Futebol",
            "categoria": "Distrital / Campeonato",
            "escalao": "Seniores",
            "equipa_casa": home["equipa"],
            "equipa_fora": adversario,
            "url_equipa_casa": "",
            "url_equipa_fora": "",
            "url_classificacao": "",
            "data": data_jogo.strftime("%Y-%m-%d"),
            "hora": "15:00",
            "local": home["estadio"],
            "latitude": home["lat"],
            "longitude": home["lon"],
            "preco": "~3€ (estimado)",
            "descricao": "Jogo oficial do campeonato distrital.",
            "url_maps": f"https://www.google.com/maps/search/?api=1&query={home['lat']},{home['lon']}",
            "status": "aprovado"
        })

    # 2. Gerar Cultura
    for _ in range(15):
        local = random.choice(LOCAIS_CULTURA)
        tipo = random.choice(["Concerto", "Feira", "Teatro"])
        data_ev = get_random_weekend_date(base_date, random.randint(0, 3))
        
        eventos_para_inserir.append({
            "nome": f"{tipo} de {local['zona']}",
            "tipo": "Cultura/Lazer",
            "categoria": tipo,
            "escalao": None,
            "data": data_ev.strftime("%Y-%m-%d"),
            "hora": "21:30",
            "local": local["nome"],
            "latitude": local["lat"],
            "longitude": local["lon"],
            "preco": "10€",
            "descricao": f"Grande evento cultural em {local['zona']}.",
            "url_maps": f"https://www.google.com/maps/search/?api=1&query={local['lat']},{local['lon']}",
            "status": "aprovado"
        })

    # 3. Inserir no Supabase (Upsert)
    total_sucesso = 0
    total_erro = 0

    print(f"📦 A processar {len(eventos_para_inserir)} eventos...")

    for evento in eventos_para_inserir:
        try:
            # on_conflict="nome,data" assume que criaste uma constraint UNIQUE na BD
            # Se não criaste, ele vai inserir duplicados. O ideal é ter a constraint.
            response = supabase.table("eventos").upsert(evento).execute()
            
            # Verificar se houve erro na resposta (supabase-py v2 lança exceção, mas verificamos response)
            if hasattr(response, 'error') and response.error:
                print(f"❌ Erro ao inserir '{evento['nome']}': {response.error}")
                total_erro += 1
            else:
                print(f"✅ Inserido/Atualizado: {evento['nome']}")
                total_sucesso += 1
                
        except Exception as e:
            # Captura erros de rede ou constraint violations
            print(f"⚠️ Exceção no evento '{evento['nome']}': {e}")
            total_erro += 1
            
        # Pequeno delay para não saturar a API (opcional)
        time.sleep(0.1)

    print(f"
🏁 Processo concluído!")
    print(f"   Sucessos: {total_sucesso}")
    print(f"   Erros/Saltados: {total_erro}")

if __name__ == "__main__":
    gerar_eventos_para_db()
