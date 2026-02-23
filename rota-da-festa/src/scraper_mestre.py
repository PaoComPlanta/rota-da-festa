import os
import asyncio
import re
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

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Credenciais Supabase em falta.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
geolocator = Nominatim(user_agent="rota_da_festa_bot_v5")

# ========================================================================
# Cache de estádios — profissionais + semi-profissionais + distritais
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
    "Leça FC": {"lat": 41.1833, "lon": -8.7000, "local": "Estádio do Leça FC"},
    "Maia": {"lat": 41.2333, "lon": -8.6167, "local": "Estádio Prof. Dr. José Vieira de Carvalho"},
    "Limianos": {"lat": 41.7667, "lon": -8.5833, "local": "Estádio Municipal de Ponte de Lima"},
    # --- AF BRAGA (distritais) ---
    "Merelinense": {"lat": 41.5768, "lon": -8.4482, "local": "Estádio João Soares Vieira"},
    "Merelinense FC": {"lat": 41.5768, "lon": -8.4482, "local": "Estádio João Soares Vieira"},
    "Vilaverdense": {"lat": 41.6489, "lon": -8.4356, "local": "Campo Cruz do Reguengo"},
    "Vilaverdense FC": {"lat": 41.6489, "lon": -8.4356, "local": "Campo Cruz do Reguengo"},
    "Maria da Fonte": {"lat": 41.6032, "lon": -8.2589, "local": "Estádio Moinhos Novos"},
    "Dumiense": {"lat": 41.5621, "lon": -8.4328, "local": "Campo Celestino Lobo"},
    "Dumiense FC": {"lat": 41.5621, "lon": -8.4328, "local": "Campo Celestino Lobo"},
    "GD Joane": {"lat": 41.4333, "lon": -8.4167, "local": "Estádio de Barreiros, Joane"},
    "Brito SC": {"lat": 41.4886, "lon": -8.3582, "local": "Parque de Jogos do Brito SC"},
    "Brito": {"lat": 41.4886, "lon": -8.3582, "local": "Parque de Jogos do Brito SC"},
    "Santa Maria FC": {"lat": 41.5333, "lon": -8.5333, "local": "Estádio da Devesa"},
    "Vieira SC": {"lat": 41.6333, "lon": -8.1333, "local": "Estádio Municipal de Vieira"},
    "AD Ninense": {"lat": 41.4667, "lon": -8.5500, "local": "Complexo Desportivo de Nine"},
    "GD Prado": {"lat": 41.6000, "lon": -8.4667, "local": "Complexo Desportivo do Faial"},
    "Pevidém SC": {"lat": 41.4167, "lon": -8.3333, "local": "Parque Albano Martins Coelho Lima"},
    "Pevidém": {"lat": 41.4167, "lon": -8.3333, "local": "Parque Albano Martins Coelho Lima"},
    "Caçadores Taipas": {"lat": 41.4833, "lon": -8.3500, "local": "Estádio do Montinho"},
    "Caçadores das Taipas": {"lat": 41.4833, "lon": -8.3500, "local": "Estádio do Montinho"},
    "Berço SC": {"lat": 41.4667, "lon": -8.3333, "local": "Complexo Desportivo de Ponte"},
    "CD Celeirós": {"lat": 41.5167, "lon": -8.4500, "local": "Parque Desportivo de Celeirós"},
    "Forjães SC": {"lat": 41.6167, "lon": -8.7333, "local": "Estádio Horácio Queirós"},
    "Desportivo de Ronfe": {"lat": 41.4333, "lon": -8.3667, "local": "Estádio do Desportivo de Ronfe"},
    "Sandineneses": {"lat": 41.4667, "lon": -8.3833, "local": "Complexo Desportivo D. Maria Teresa"},
    "Académico": {"lat": 41.5503, "lon": -8.4270, "local": "Estádio 1º de Maio, Braga"},
    "Sanjoanense": {"lat": 41.0333, "lon": -8.5000, "local": "Estádio da Sanjoanense"},
    "Caldelas SC": {"lat": 41.5833, "lon": -8.2667, "local": "Campo Municipal de Caldelas"},
    "Taipas": {"lat": 41.4833, "lon": -8.3500, "local": "Estádio do Montinho"},
    "FC Penafiel": {"lat": 41.2083, "lon": -8.2833, "local": "Estádio Municipal 25 de Abril"},
    "Ribeirão": {"lat": 41.5000, "lon": -8.4667, "local": "Campo de Ribeirão"},
    "Arões SC": {"lat": 41.5333, "lon": -8.2667, "local": "Campo de Arões"},
    "Arões": {"lat": 41.5333, "lon": -8.2667, "local": "Campo de Arões"},
    "Serzedelo": {"lat": 41.4333, "lon": -8.3333, "local": "Campo de Serzedelo"},
    "Martim": {"lat": 41.5333, "lon": -8.3500, "local": "Campo de Martim"},
    "Cabreiros": {"lat": 41.5833, "lon": -8.4333, "local": "Campo de Cabreiros"},
    "Esposende": {"lat": 41.5333, "lon": -8.7833, "local": "Estádio Municipal de Esposende"},
    "SC Esposende": {"lat": 41.5333, "lon": -8.7833, "local": "Estádio Municipal de Esposende"},
    "Bairro": {"lat": 41.5000, "lon": -8.3500, "local": "Campo do Bairro"},
    "Santa Eulália": {"lat": 41.5833, "lon": -8.3500, "local": "Campo de Santa Eulália"},
    "Porto d'Ave": {"lat": 41.5167, "lon": -8.3167, "local": "Campo de Porto d'Ave"},
    "Ruilhe": {"lat": 41.5667, "lon": -8.4833, "local": "Campo de Ruilhe"},
    "Pedralva": {"lat": 41.5500, "lon": -8.4000, "local": "Campo de Pedralva"},
    "Maximinos": {"lat": 41.5667, "lon": -8.4333, "local": "Campo de Maximinos"},
    "Real SC Braga": {"lat": 41.5503, "lon": -8.4270, "local": "Estádio 1º de Maio, Braga"},
    "Palmeiras FC": {"lat": 41.5500, "lon": -8.4667, "local": "Campo de Palmeiras, Braga"},
    "Nogueiró e Tenões": {"lat": 41.5350, "lon": -8.4050, "local": "Campo de Nogueiró"},
    "SC Barcelos": {"lat": 41.5372, "lon": -8.6339, "local": "Estádio Cidade de Barcelos"},
    # --- AF VIANA DO CASTELO (distritais) ---
    "Monção": {"lat": 42.0769, "lon": -8.4822, "local": "Estádio Municipal de Monção"},
    "Cerveira": {"lat": 41.9406, "lon": -8.7442, "local": "Campo Municipal de Vila Nova de Cerveira"},
    "Limianos": {"lat": 41.7667, "lon": -8.6333, "local": "Campo dos Limianos, Ponte de Lima"},
    # --- AF AVEIRO (distritais) ---
    "ADC Lobão": {"lat": 40.9634, "lon": -8.4876, "local": "Parque de Jogos de Lobão"},
    "Fiães SC": {"lat": 40.9921, "lon": -8.5235, "local": "Estádio do Bolhão"},
    "Fiães": {"lat": 40.9921, "lon": -8.5235, "local": "Estádio do Bolhão"},
    "RD Águeda": {"lat": 40.5744, "lon": -8.4485, "local": "Estádio Municipal de Águeda"},
    "Águeda": {"lat": 40.5744, "lon": -8.4485, "local": "Estádio Municipal de Águeda"},
    "Ovarense": {"lat": 40.8594, "lon": -8.6269, "local": "Estádio Municipal de Ovar"},
    "Pampilhosa": {"lat": 40.4500, "lon": -8.3833, "local": "Campo da Pampilhosa"},
    "Estarreja": {"lat": 40.7558, "lon": -8.5711, "local": "Estádio Municipal de Estarreja"},
    "Anadia": {"lat": 40.4357, "lon": -8.4357, "local": "Estádio Municipal de Anadia"},
    "Lusitano de Évora": {"lat": 38.5667, "lon": -7.9000, "local": "Estádio do Lusitano de Évora"},
    "Vitória Setúbal": {"lat": 38.5244, "lon": -8.8882, "local": "Estádio do Bonfim"},
    "Leiria": {"lat": 39.7500, "lon": -8.8000, "local": "Estádio Dr. Magalhães Pessoa"},
    "Covilhã": {"lat": 40.2833, "lon": -7.5000, "local": "Estádio Santos Pinto"},
    # --- AF PORTO (distritais) ---
    "SC Rio Tinto": {"lat": 41.1764, "lon": -8.5583, "local": "Estádio Cidade de Rio Tinto"},
    "Rio Tinto": {"lat": 41.1764, "lon": -8.5583, "local": "Estádio Cidade de Rio Tinto"},
    "Gondomar SC": {"lat": 41.1444, "lon": -8.5333, "local": "Estádio de São Miguel, Gondomar"},
    "Maia Lidador": {"lat": 41.2333, "lon": -8.6167, "local": "Estádio Prof. Dr. José Vieira de Carvalho"},
    "Pedras Rubras": {"lat": 41.2333, "lon": -8.6833, "local": "Campo de Pedras Rubras"},
    "Dragões Sandinenses": {"lat": 41.3167, "lon": -8.5500, "local": "Campo dos Dragões Sandinenses"},
    "Vila Meã": {"lat": 41.1500, "lon": -8.3833, "local": "Campo de Vila Meã"},
    "Foz": {"lat": 41.1500, "lon": -8.6833, "local": "Campo da Foz do Douro"},
    "Canidelo": {"lat": 41.1333, "lon": -8.6500, "local": "Campo de Canidelo"},
    "Infesta": {"lat": 41.2000, "lon": -8.6000, "local": "Campo de Infesta"},
    "Padroense": {"lat": 41.1833, "lon": -8.6167, "local": "Campo do Padroense FC"},
    "Salgueiros": {"lat": 41.1500, "lon": -8.6333, "local": "Estádio Engenheiro Vidal Pinheiro"},
    "Campanhã": {"lat": 41.1500, "lon": -8.5833, "local": "Campo de Campanhã"},
    "Águias Moreira": {"lat": 41.1833, "lon": -8.7333, "local": "Campo das Águias de Moreira"},
    "Nogueirense": {"lat": 41.2333, "lon": -8.5500, "local": "Campo do Nogueirense"},
    "Lusitânia Lourosa": {"lat": 40.9833, "lon": -8.5333, "local": "Estádio do Lusitânia de Lourosa"},
    "Lourosa": {"lat": 40.9833, "lon": -8.5333, "local": "Estádio do Lusitânia de Lourosa"},
}

# Ficheiro de cache persistente (ao lado do script)
_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_estadios.json")

def _load_cache():
    """Carrega cache de estádios do ficheiro JSON e faz merge com o hardcoded."""
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Merge: saved sobrepõe hardcoded (tem geocoding real)
            CACHE_ESTADIOS.update(saved)
            print(f"📂 Cache carregado: {len(saved)} entradas do ficheiro, {len(CACHE_ESTADIOS)} total")
        except Exception as e:
            print(f"⚠️ Erro ao carregar cache: {e}")

def _save_cache():
    """Guarda o cache completo num ficheiro JSON."""
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(CACHE_ESTADIOS, f, ensure_ascii=False, indent=2)
        print(f"💾 Cache guardado: {len(CACHE_ESTADIOS)} estádios em {_CACHE_FILE}")
    except Exception as e:
        print(f"⚠️ Erro ao guardar cache: {e}")

_load_cache()
DISTRICT_CENTROIDS = {
    "braga": {"lat": 41.5503, "lon": -8.4270, "local": "Braga (aproximado)"},
    "porto": {"lat": 41.1496, "lon": -8.6109, "local": "Porto (aproximado)"},
    "aveiro": {"lat": 40.6405, "lon": -8.6538, "local": "Aveiro (aproximado)"},
    "lisboa": {"lat": 38.7223, "lon": -9.1393, "local": "Lisboa (aproximado)"},
    "leiria": {"lat": 39.7437, "lon": -8.8070, "local": "Leiria (aproximado)"},
    "coimbra": {"lat": 40.2109, "lon": -8.4377, "local": "Coimbra (aproximado)"},
    "viseu": {"lat": 40.6610, "lon": -7.9097, "local": "Viseu (aproximado)"},
    "setúbal": {"lat": 38.5244, "lon": -8.8882, "local": "Setúbal (aproximado)"},
    "santarém": {"lat": 39.2369, "lon": -8.6850, "local": "Santarém (aproximado)"},
    "beja": {"lat": 38.0150, "lon": -7.8653, "local": "Beja (aproximado)"},
    "faro": {"lat": 37.0194, "lon": -7.9304, "local": "Faro (aproximado)"},
    "évora": {"lat": 38.5667, "lon": -7.9000, "local": "Évora (aproximado)"},
    "bragança": {"lat": 41.8063, "lon": -6.7572, "local": "Bragança (aproximado)"},
    "castelo branco": {"lat": 39.8228, "lon": -7.4906, "local": "Castelo Branco (aproximado)"},
    "guarda": {"lat": 40.5373, "lon": -7.2676, "local": "Guarda (aproximado)"},
    "viana": {"lat": 41.6936, "lon": -8.8319, "local": "Viana do Castelo (aproximado)"},
    "viana do castelo": {"lat": 41.6936, "lon": -8.8319, "local": "Viana do Castelo (aproximado)"},
    "vila real": {"lat": 41.2959, "lon": -7.7464, "local": "Vila Real (aproximado)"},
    "portalegre": {"lat": 39.2967, "lon": -7.4317, "local": "Portalegre (aproximado)"},
    "funchal": {"lat": 32.6669, "lon": -16.9241, "local": "Funchal (aproximado)"},
    "ponta delgada": {"lat": 37.7483, "lon": -25.6666, "local": "Ponta Delgada (aproximado)"},
    "angra do heroísmo": {"lat": 38.6545, "lon": -27.2177, "local": "Angra do Heroísmo (aproximado)"},
    "horta": {"lat": 38.5342, "lon": -28.6300, "local": "Horta (aproximado)"},
}

# Palavras-chave de competições portuguesas
PORTUGUESE_COMP_KEYWORDS = [
    "portugal",
    "liga portugal", "primeira liga", "liga 2", "segunda liga", "meu super",
    "liga 3", "campeonato de portugal", "taça de portugal", "taça da liga",
    "supertaça", "liga revelação", "taça revelação",
    "af braga", "af porto", "af aveiro", "af lisboa", "af leiria",
    "af coimbra", "af viseu", "af setúbal", "af santarém", "af beja",
    "af faro", "af évora", "af bragança", "af castelo branco",
    "af guarda", "af viana", "af vila real", "af portalegre",
    "af funchal", "af ponta delgada", "af angra", "af horta",
    "pro-nacional", "pró-nacional", "distrital", "divisão de honra",
    "1ª divisão", "2ª divisão", "3ª divisão", "divisão elite",
    "liga regional", "campeonato regional",
]

# Nomes de equipas portuguesas (para detectar em competições internacionais)
PORTUGUESE_TEAMS = list(CACHE_ESTADIOS.keys())


def _team_match(pt_name: str, team_name: str) -> bool:
    """Verifica se o nome da equipa portuguesa corresponde ao nome dado."""
    pl = pt_name.lower()
    tl = team_name.lower().strip()
    if tl == pl:
        return True
    return pl in tl and len(pl) / len(tl) > 0.55


def _extract_district(comp_text: str):
    """Extrai o distrito/AF do texto da competição e devolve o centróide."""
    cl = comp_text.lower()
    for district, geo in DISTRICT_CENTROIDS.items():
        if f"af {district}" in cl:
            return geo
    return None


# Equipas que já falharam todas as tentativas de geocoding
_GEO_FAILED = set()


def geolocalizar_estadio(nome_equipa: str, comp_text: str = ""):
    """Localiza o estádio de uma equipa com múltiplos fallbacks."""
    # 1. Cache
    for k, v in CACHE_ESTADIOS.items():
        if _team_match(k, nome_equipa):
            return v

    # 2. Já falhou antes? Ir direto ao fallback distrito
    if nome_equipa in _GEO_FAILED:
        district_geo = _extract_district(comp_text)
        return district_geo

    # 3. Nominatim: melhor query única
    for query in [
        f"Estádio {nome_equipa}, Portugal",
        f"{nome_equipa} futebol, Portugal",
    ]:
        try:
            loc = geolocator.geocode(query, timeout=5)
            if loc:
                result = {"lat": loc.latitude, "lon": loc.longitude, "local": loc.address.split(",")[0]}
                CACHE_ESTADIOS[nome_equipa] = result
                return result
        except Exception:
            pass
        time.sleep(1.1)

    # 4. Extrair localidade do nome (ex: "Águias de Alvite" → "Alvite, Portugal")
    m = re.search(r'\b(?:de|da|do|dos|das)\s+(.+)', nome_equipa, re.IGNORECASE)
    if m:
        localidade = m.group(1).strip()
        try:
            loc = geolocator.geocode(f"{localidade}, Portugal", timeout=5)
            if loc:
                result = {"lat": loc.latitude, "lon": loc.longitude, "local": f"Campo em {localidade}"}
                CACHE_ESTADIOS[nome_equipa] = result
                return result
        except Exception:
            pass
        time.sleep(1.1)

    # 5. Fallback: centróide do distrito extraído da competição
    district_geo = _extract_district(comp_text)
    if district_geo:
        print(f"    📍 Fallback distrito para {nome_equipa}: {district_geo['local']}")
        _GEO_FAILED.add(nome_equipa)
        return district_geo

    _GEO_FAILED.add(nome_equipa)
    return None


def is_portuguese_game(casa: str, fora: str, comp_text: str = "",
                       has_pt_flag: bool = False) -> bool:
    """Verifica se o jogo é português (bandeira PT, competição, ou equipas)."""
    if has_pt_flag:
        return True
    cl = comp_text.lower()
    if any(re.search(r'(?:^|\b)' + re.escape(kw) + r'(?:\b|$)', cl)
           for kw in PORTUGUESE_COMP_KEYWORDS):
        return True
    return any(
        _team_match(t, casa) or _team_match(t, fora) for t in PORTUGUESE_TEAMS
    )


def _extract_game_id(url: str) -> str:
    """Extrai o ID numérico do jogo a partir do URL para deduplicação."""
    m = re.search(r'/(\d{6,})(?:\?|$)', url)
    return m.group(1) if m else url


def parse_games_from_html(html: str) -> list:
    """Extrai jogos do HTML usando BeautifulSoup (li.game + tabela, sempre ambos)."""
    soup = BeautifulSoup(html, "html.parser")
    ids_vistos = set()
    resultados = []

    # --- 1. Tabela principal agenda_list ---
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
                # Tentar extrair equipas de outra forma se regex falhar
                continue
            casa = vs_match.group(1).strip()
            fora = vs_match.group(2).strip()

            url_date = re.search(
                r'/(?:jogo|live-ao-minuto)/(\d{4}-\d{2}-\d{2})', game_url
            )
            data = url_date.group(1) if url_date else datetime.now().strftime("%Y-%m-%d")

            comp_el = info_td.select_one("div.match_info")
            comp_text = comp_el.get_text(strip=True) if comp_el else ""

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

    # --- 2. Elementos li.game (matchbox) ---
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


async def scrape_game_details(page, game_url: str) -> dict:
    """Visita a página de um jogo no ZeroZero para extrair URLs de equipas e classificação."""
    result = {"url_equipa_casa": "", "url_equipa_fora": "", "url_classificacao": ""}
    base = "https://www.zerozero.pt"
    
    try:
        full_url = game_url if game_url.startswith("http") else base + game_url
        await page.goto(full_url, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Extrair URLs das equipas a partir do cabeçalho do jogo
        team_urls = []
        header = soup.select_one("#match-header, .match-header, [class*='matchHeader'], [class*='match_header']")
        team_links = (header or soup).select("a[href*='/equipa/']")
        seen_urls = set()
        for tl in team_links:
            href = tl.get("href", "")
            if "/equipa/" in href:
                full = href if href.startswith("http") else base + href
                if full not in seen_urls:
                    seen_urls.add(full)
                    team_urls.append(full)

        if len(team_urls) >= 2:
            result["url_equipa_casa"] = team_urls[0]
            result["url_equipa_fora"] = team_urls[1]
        elif len(team_urls) == 1:
            result["url_equipa_casa"] = team_urls[0]

        # Extrair URL da classificação (link com /edition/ ou classificacao)
        edition_links = soup.select("a[href*='/edition/'], a[href*='classificacao']")
        for el in edition_links:
            href = el.get("href", "")
            if "/edition/" in href or "classificacao" in href:
                result["url_classificacao"] = href if href.startswith("http") else base + href
                break

        # Fallback: procurar link da competição
        if not result["url_classificacao"]:
            comp_links = soup.select("a[href*='/edicao/'], a[href*='/competicao/']")
            for cl in comp_links:
                href = cl.get("href", "")
                if href:
                    result["url_classificacao"] = href if href.startswith("http") else base + href
                    break

    except Exception as e:
        print(f"    ⚠️ Erro ao extrair detalhes de {game_url}: {e}")

    return result


def extrair_escalao(comp_text: str, nome_jogo: str = "") -> str:
    """Extrai o escalão do texto da competição ou nome do jogo."""
    texto = (comp_text + " " + nome_jogo).lower()
    if any(x in texto for x in ["sub-19", "juniores a", "juniores"]):
        return "Sub-19"
    if any(x in texto for x in ["sub-17", "juvenis"]):
        return "Sub-17"
    if any(x in texto for x in ["sub-15", "iniciados"]):
        return "Sub-15"
    if any(x in texto for x in ["sub-13", "infantis"]):
        return "Sub-13"
    if any(x in texto for x in ["sub-11", "benjamins", "benjamim"]):
        return "Benjamins"
    if any(x in texto for x in ["sub-9", "sub-7", "traquinas", "petizes"]):
        return "Traquinas"
    if any(x in texto for x in ["revelação", "sub-23"]):
        return "Sub-23"
    return "Seniores"


def classificar_evento(comp_text: str, nome_jogo: str = ""):
    """Retorna (categoria, preço, escalão) baseado no texto da competição.

    Preços médios ponderados do futebol português (fontes: Liga Portugal, clubes):
    - Liga Portugal Betclic: €10-25, média ~15€
    - Liga Portugal 2: €5-15, média ~10€
    - Taça de Portugal: €5-15, média ~8€
    - Liga 3 / Camp. Portugal: €3-7, média ~5€
    - Distrital (Seniores): €2-5, média ~3€
    - Competições Europeias: €15-60, média ~25€
    - Formação (todos os escalões): Grátis
    """
    cl = comp_text.lower()
    escalao = extrair_escalao(comp_text, nome_jogo)

    # Formação é sempre grátis
    if escalao not in ("Seniores", "Sub-23"):
        return f"Formação - {escalao}", "Grátis", escalao

    if any(x in cl for x in ["champions", "europa league", "conference", "uefa"]):
        return "Competição Europeia", "~25€ (estimado)", escalao
    if any(x in cl for x in ["liga portugal", "primeira liga", "betclic"]):
        return "Liga Portugal", "~15€ (estimado)", escalao
    if any(x in cl for x in ["liga 2", "segunda liga", "meu super"]):
        return "Liga Portugal 2", "~10€ (estimado)", escalao
    if any(x in cl for x in ["liga 3"]):
        return "Liga 3", "~5€ (estimado)", escalao
    if any(x in cl for x in ["taça de portugal", "taca de portugal"]):
        return "Taça de Portugal", "~8€ (estimado)", escalao
    if any(x in cl for x in ["taça da liga"]):
        return "Taça da Liga", "~8€ (estimado)", escalao
    if any(x in cl for x in ["supertaça"]):
        return "Supertaça", "~15€ (estimado)", escalao
    if any(x in cl for x in ["revelação", "sub-23"]):
        return "Liga Revelação", "Grátis", "Sub-23"
    if any(x in cl for x in ["liga feminina", "liga bpi", "futebol feminino"]):
        return "Futebol Feminino", "~3€ (estimado)", escalao
    if any(x in cl for x in ["pro-nacional", "pró-nacional", "campeonato de portugal"]):
        return "Campeonato de Portugal", "~5€ (estimado)", escalao
    if any(x in cl for x in ["divisão de honra", "divisao de honra"]):
        return "Divisão de Honra", "~3€ (estimado)", escalao
    if any(x in cl for x in [
        "af ", "a.f.", "distrital", "1ª divisão", "2ª divisão", "3ª divisão",
        "divisão elite", "liga regional", "campeonato regional",
        "afp ", "afl ", "afb ",
    ]):
        return "Futebol Distrital", "~3€ (estimado)", escalao
    if any(x in cl for x in [
        "amigável", "amistoso", "particular", "friendly",
    ]):
        return "Amigável", "Grátis", escalao
    return "Futebol", "Variável", escalao


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
                # Esperar por qualquer um dos layouts comuns
                await page.wait_for_selector(
                    "li.game, table.agenda_list", timeout=15000
                )
            except Exception:
                pass

            await page.wait_for_timeout(1500)

            # Scroll para carregar conteúdo lazy-loaded (divisões inferiores)
            for _ in range(5):
                prev_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == prev_height:
                    break

            # Clicar em "ver mais" / "show more" se existir
            try:
                more_btn = page.locator("a.ver_mais, a.show_more, button:has-text('mais'), a:has-text('Ver mais')")
                while await more_btn.first.is_visible(timeout=1000):
                    await more_btn.first.click()
                    await page.wait_for_timeout(1500)
            except Exception:
                pass

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


async def load_page_fast(page, url: str, scroll: bool = False) -> str:
    """Carregamento rápido para Fase 2 — scroll leve opcional, sem retries."""
    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        if scroll:
            for _ in range(3):
                prev = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(800)
                if await page.evaluate("document.body.scrollHeight") == prev:
                    break

        title = await page.title()
        if "cloudflare" in title.lower() or "just a moment" in title.lower():
            return ""
        return await page.content()
    except Exception as e:
        print(f"    ⚠️ Fast load falhou ({url}): {e}")
        return ""


def limpar_eventos_concluidos():
    """Quinta-feira: limpa eventos passados. Outros dias: mantém tudo."""
    hoje = datetime.now()
    if hoje.weekday() != 3:  # 3 = quinta-feira
        print("📅 Não é quinta-feira — eventos passados mantidos.")
        return

    ontem = (hoje - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        result = supabase.table("eventos").delete().lt("data", ontem).execute()
        n = len(result.data) if result.data else 0
        print(f"🧹 Quinta-feira: removidos {n} eventos concluídos.")
    except Exception as e:
        print(f"⚠️ Erro ao limpar eventos: {e}")


def extract_games_from_page(html: str, comp_name: str = "") -> list:
    """Extrai jogos de qualquer página ZeroZero (edição, calendário, competição).
    Prioriza linhas dentro de table.zztable (conteúdo real) para evitar sidebar."""
    soup = BeautifulSoup(html, "html.parser")
    games = []
    hoje = datetime.now()
    limite = hoje + timedelta(days=14)
    seen = set()

    if not comp_name:
        h1 = soup.select_one("h1, .header h2, .comp_title")
        comp_name = h1.get_text(strip=True) if h1 else ""

    # Priorizar jogos dentro de tabelas (conteúdo principal, não sidebar)
    tables = soup.select("table.zztable")
    if tables:
        game_links = []
        for table in tables:
            game_links.extend(table.select("a[href*='/jogo/']"))
    else:
        game_links = soup.select("a[href*='/jogo/']")

    for match_link in game_links:
        href = match_link.get("href", "")
        if not href or href in seen:
            continue
        seen.add(href)

        url_date = re.search(r'/jogo/(\d{4}-\d{2}-\d{2})', href)
        if not url_date:
            parent = match_link.find_parent(["tr", "li", "div"])
            if parent:
                dm = re.search(r'(\d{4}-\d{2}-\d{2})', str(parent))
                if dm:
                    url_date = dm
        if not url_date:
            continue
        data = url_date.group(1) if hasattr(url_date, 'group') else url_date

        try:
            game_date = datetime.strptime(data, "%Y-%m-%d")
            if game_date.date() < hoje.date() or game_date > limite:
                continue
        except Exception:
            continue

        parent = match_link.find_parent(["tr", "li", "div"])
        if not parent:
            parent = match_link.parent

        # Equipas: links /equipa/ com texto não-vazio (ignorar links de logos)
        team_links = parent.select("a[href*='/equipa/']") if parent else []
        named_teams = [t.get_text(strip=True) for t in team_links if t.get_text(strip=True)]
        # Deduplicate mantendo ordem
        unique_teams = list(dict.fromkeys(named_teams))

        casa, fora = None, None
        if len(unique_teams) >= 2:
            casa = unique_teams[0]
            fora = unique_teams[1]
        else:
            text = match_link.get_text(strip=True)
            vs = re.match(r'(.+?)\s+(?:vs|x|\d+-\d+)\s+(.+)', text, re.IGNORECASE)
            if vs:
                casa = vs.group(1).strip()
                fora = vs.group(2).strip()

        if not casa or not fora:
            continue

        hora = "A definir"
        ctx_text = parent.get_text() if parent else ""
        time_match = re.search(r'\b(\d{2}:\d{2})\b', ctx_text)
        if time_match:
            hora = time_match.group(1)

        base_url = "https://www.zerozero.pt"
        full_url = href if href.startswith("http") else base_url + href

        games.append({
            "casa": casa, "fora": fora,
            "data": data, "hora": hora,
            "competicao": comp_name, "url": full_url,
            "has_pt_flag": True,
        })

    return games


async def scrape_zerozero():
    base_url = "https://www.zerozero.pt/agenda.php"
    base = "https://www.zerozero.pt"
    print("🌍 A iniciar scraping do ZeroZero...")

    # URLs das 20 AFs + competições nacionais (do sitemap zerozero.pt)
    PT_COMPETITION_URLS = {
        "af-algarve": "https://www.zerozero.pt/competicao/af-algarve/169",
        "af-aveiro": "https://www.zerozero.pt/competicao/af-aveiro/170",
        "af-beja": "https://www.zerozero.pt/competicao/af-beja/171",
        "af-braga": "https://www.zerozero.pt/competicao/af-braga/172",
        "af-braganca": "https://www.zerozero.pt/competicao/af-braganca/173",
        "af-castelo-branco": "https://www.zerozero.pt/competicao/af-castelo-branco/174",
        "af-coimbra": "https://www.zerozero.pt/competicao/af-coimbra/175",
        "af-evora": "https://www.zerozero.pt/competicao/af-evora/176",
        "af-guarda": "https://www.zerozero.pt/competicao/af-guarda/177",
        "af-leiria": "https://www.zerozero.pt/competicao/af-leiria/178",
        "af-lisboa": "https://www.zerozero.pt/competicao/af-lisboa/179",
        "af-portalegre": "https://www.zerozero.pt/competicao/af-portalegre/180",
        "af-porto": "https://www.zerozero.pt/competicao/af-porto/181",
        "af-santarem": "https://www.zerozero.pt/competicao/af-santarem/182",
        "af-setubal": "https://www.zerozero.pt/competicao/af-setubal/183",
        "af-viana-do-castelo": "https://www.zerozero.pt/competicao/af-viana-do-castelo/184",
        "af-vila-real": "https://www.zerozero.pt/competicao/af-vila-real/185",
        "af-viseu": "https://www.zerozero.pt/competicao/af-viseu/186",
        "af-ponta-delgada": "https://www.zerozero.pt/competicao/af-ponta-delgada/219",
        "af-madeira": "https://www.zerozero.pt/competicao/af-madeira/222",
        "liga-3": "https://www.zerozero.pt/competicao/iii-divisao/76",
        "juniores-a": "https://www.zerozero.pt/competicao/i-divisao-juniores-a-sub-19-/136",
        "juniores-b": "https://www.zerozero.pt/competicao/i-divisao-juniores-b-sub-17-/137",
        "juniores-c": "https://www.zerozero.pt/competicao/i-divisao-juniores-c-sub-15-/138",
        "feminina": "https://www.zerozero.pt/competicao/liga-portuguesa-feminina/143",
    }

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
            datas_ok = set()

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
                datas_ok.add(data_str)

                jogos = parse_games_from_html(html)
                novos = 0
                for jogo in jogos:
                    gid = _extract_game_id(jogo["url"])
                    if gid not in ids_vistos:
                        ids_vistos.add(gid)
                        all_games.append(jogo)
                        novos += 1
                print(f"   🔍 {len(jogos)} jogos na página, {novos} novos")

            print(f"\n📊 Fase 1 (Agenda): {len(all_games)} jogos encontrados")

            # ================================================================
            # FASE 2: Scraping por AF/competição — distritais e formação
            # ================================================================
            print("\n🏟️  Fase 2: A descobrir jogos distritais e de formação...")
            af_page = await context.new_page()
            af_total = 0

            for comp_name, comp_url in PT_COMPETITION_URLS.items():
                try:
                    print(f"  📋 {comp_name}...")

                    # 1. Visitar página da competição/AF (load completo com scroll)
                    html = await load_page(af_page, comp_url)
                    if not html:
                        continue

                    comp_soup = BeautifulSoup(html, "html.parser")

                    # 2. Recolher links de edições directamente (só época atual)
                    edition_urls = []
                    for link in comp_soup.select("a[href*='/edicao/']"):
                        href = link.get("href", "")
                        if href and ("2025-26" in href or "2025-2026" in href or "2026" in href):
                            full = href if href.startswith("http") else base + href
                            if full not in edition_urls:
                                edition_urls.append(full)

                    # 3. Se não há edições, esta é uma página "umbrella" (AF)
                    #    — descobrir sub-competições primeiro
                    if not edition_urls:
                        sub_comp_urls = []
                        for link in comp_soup.select("a[href*='/competicao/']"):
                            href = link.get("href", "")
                            if href and "/competicao/" in href:
                                full = href if href.startswith("http") else base + href
                                if full != comp_url and full not in sub_comp_urls:
                                    sub_comp_urls.append(full)

                        sub_comp_urls = sub_comp_urls[:20]
                        if sub_comp_urls:
                            print(f"     📂 {len(sub_comp_urls)} sub-competições encontradas")

                        for sc_url in sub_comp_urls:
                            try:
                                sc_html = await load_page_fast(af_page, sc_url)
                                if not sc_html:
                                    continue
                                sc_soup = BeautifulSoup(sc_html, "html.parser")
                                for link in sc_soup.select("a[href*='/edicao/']"):
                                    href = link.get("href", "")
                                    if href and ("2025-26" in href or "2025-2026" in href or "2026" in href):
                                        full = href if href.startswith("http") else base + href
                                        if full not in edition_urls:
                                            edition_urls.append(full)
                                await asyncio.sleep(0.2)
                            except Exception:
                                continue

                    # Limitar edições por AF (muitas séries/escalões)
                    edition_urls = edition_urls[:30]
                    print(f"     📖 {len(edition_urls)} edições encontradas")

                    # 4. Tentar extrair jogos directamente da página (alguns mostram próximos jogos)
                    if not edition_urls:
                        jogos = extract_games_from_page(html, comp_name)
                        for j in jogos:
                            gid = _extract_game_id(j["url"])
                            if gid not in ids_vistos:
                                ids_vistos.add(gid)
                                all_games.append(j)
                                af_total += 1
                        if jogos:
                            print(f"     ✅ Directos: +{len(jogos)} jogos")
                        continue

                    # 5. Para cada edição, visitar próximos jogos e extrair
                    for ed_idx, ed_url in enumerate(edition_urls):
                        try:
                            # Prioridade: "próximos jogos" (só mostra jogos futuros)
                            prox_url = ed_url.rstrip("/") + "/proximos-jogos"
                            html_ed = await load_page_fast(af_page, prox_url, scroll=True)

                            # Se não funcionou, tentar página principal da edição
                            if not html_ed or len(html_ed) < 5000:
                                html_ed = await load_page_fast(af_page, ed_url, scroll=True)

                            if not html_ed:
                                continue

                            ed_soup = BeautifulSoup(html_ed, "html.parser")
                            ed_h1 = ed_soup.select_one("h1, h2.header_title")
                            ed_comp = ed_h1.get_text(strip=True) if ed_h1 else comp_name

                            # Debug: primeira edição de cada AF — mostrar o que foi encontrado
                            if ed_idx == 0:
                                n_game_links = len(ed_soup.select("a[href*='/jogo/']"))
                                n_team_links = len(ed_soup.select("a[href*='/equipa/']"))
                                page_title = ed_soup.title.string if ed_soup.title else "sem título"
                                print(f"     🔍 Debug {ed_comp}: {n_game_links} links /jogo/, {n_team_links} links /equipa/, título: {page_title[:60]}")

                            # Tentar os dois parsers: genérico + o da Fase 1
                            jogos = extract_games_from_page(html_ed, ed_comp)
                            if not jogos:
                                jogos = parse_games_from_html(html_ed)
                                for j in jogos:
                                    j["competicao"] = ed_comp
                                    j["has_pt_flag"] = True

                            novos_ed = 0
                            for j in jogos:
                                gid = _extract_game_id(j["url"])
                                if gid not in ids_vistos:
                                    ids_vistos.add(gid)
                                    all_games.append(j)
                                    novos_ed += 1
                                    af_total += 1

                            if novos_ed:
                                print(f"     ✅ {ed_comp}: +{novos_ed} jogos")

                            await asyncio.sleep(0.3)
                        except Exception as e:
                            print(f"     ⚠️ Erro edição {ed_url}: {e}")
                            continue

                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"  ⚠️ Erro {comp_name}: {e}")
                    continue

            await af_page.close()
            print(f"\n📊 Fase 2 (AFs): +{af_total} jogos distritais/formação")
            print(f"📊 Total: {len(all_games)} jogos encontrados")

            # Filtrar: manter apenas jogos portugueses relevantes
            jogos_pt = []
            skipped_geo = 0
            for jogo in all_games:
                casa, fora = jogo["casa"], jogo["fora"]
                comp = jogo["competicao"]
                
                if not is_portuguese_game(
                    casa, fora, comp, jogo.get("has_pt_flag", False)
                ):
                    continue

                geo = (
                    geolocalizar_estadio(casa, comp)
                    or geolocalizar_estadio(fora, comp)
                )
                if not geo:
                    skipped_geo += 1
                    print(f"    ⚠️ Sem geolocalização: {casa} vs {fora} ({comp})")
                    continue

                jogo["_geo"] = geo
                jogos_pt.append(jogo)

            print(f"\n⚽ {len(jogos_pt)} jogos portugueses ({skipped_geo} sem geolocalização)")

            # Construir resultados + extrair detalhes (equipas/classificação) dos jogos
            resultados = []
            detail_page = await browser.new_page()
            await detail_page.set_extra_http_headers({"Accept-Language": "pt-PT,pt;q=0.9"})

            for idx, jogo in enumerate(jogos_pt):
                casa, fora = jogo["casa"], jogo["fora"]
                geo = jogo["_geo"]

                cat, preco, escalao = classificar_evento(jogo["competicao"], f"{casa} vs {fora}")

                evento = {
                    "nome": f"{casa} vs {fora}",
                    "tipo": "Futebol",
                    "categoria": cat,
                    "escalao": escalao,
                    "equipa_casa": casa,
                    "equipa_fora": fora,
                    "url_jogo": jogo.get("url", ""),
                    "url_equipa_casa": "",
                    "url_equipa_fora": "",
                    "url_classificacao": "",
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

                # Extrair URLs de equipas e classificação a partir da página do jogo
                if jogo.get("url"):
                    try:
                        details = await scrape_game_details(detail_page, jogo["url"])
                        evento["url_equipa_casa"] = details.get("url_equipa_casa", "")
                        evento["url_equipa_fora"] = details.get("url_equipa_fora", "")
                        evento["url_classificacao"] = details.get("url_classificacao", "")
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"    ⚠️ Sem detalhes para {casa} vs {fora}: {e}")

                    # Progresso
                    if (idx + 1) % 20 == 0:
                        print(f"  📋 Detalhes: {idx + 1}/{len(jogos_pt)} jogos processados")

                resultados.append(evento)
                print(f"  ✅ {evento['nome']} ({jogo['data']} {jogo['hora']})")

            await detail_page.close()
            print(f"\n🔗 Detalhes extraídos para {sum(1 for r in resultados if r['url_equipa_casa'])} jogos")

            return resultados, datas_ok

        except Exception as e:
            print(f"❌ Erro Scraping: {e}")
            return [], set()
        finally:
            await browser.close()


def verificar_adiamentos(eventos_novos: list, datas_ok: set):
    """Compara eventos futuros na DB com scrape fresco para detectar adiamentos."""
    hoje = datetime.now().strftime("%Y-%m-%d")

    try:
        result = (
            supabase.table("eventos")
            .select("*")
            .gte("data", hoje)
            .eq("status", "aprovado")
            .eq("tipo", "Futebol")
            .execute()
        )
        eventos_db = result.data or []
    except Exception as e:
        print(f"⚠️ Erro ao verificar adiamentos: {e}")
        return

    # Jogos encontrados no scrape: (nome, data)
    scrape_set = {(ev["nome"], ev["data"]) for ev in eventos_novos}

    # Nomes → datas no scrape (para detectar remarcações)
    nomes_datas = {}
    for ev in eventos_novos:
        nomes_datas.setdefault(ev["nome"], []).append(ev["data"])

    adiados = 0
    remarcados = 0

    for ev_db in eventos_db:
        nome, data = ev_db["nome"], ev_db["data"]

        # Só verificar datas que foram scrapeadas com sucesso
        if data not in datas_ok:
            continue

        if (nome, data) in scrape_set:
            continue

        # Jogo não aparece no scrape para esta data
        if nome in nomes_datas:
            novas = [d for d in nomes_datas[nome] if d != data]
            if novas:
                supabase.table("eventos").update({
                    "status": "adiado",
                    "descricao": f"⚠️ Remarcado para {novas[0]}. " + (ev_db.get("descricao") or ""),
                }).eq("id", ev_db["id"]).execute()
                remarcados += 1
                print(f"  🔄 Remarcado: {nome} ({data} → {novas[0]})")
                continue

        supabase.table("eventos").update({
            "status": "adiado",
        }).eq("id", ev_db["id"]).execute()
        adiados += 1
        print(f"  ⚠️ Adiado: {nome} ({data})")

    if adiados or remarcados:
        print(f"📋 Adiamentos: {adiados} adiados, {remarcados} remarcados")
    else:
        print("📋 Sem adiamentos detectados")


async def main():
    # 1. Quinta-feira: limpar eventos concluídos
    limpar_eventos_concluidos()

    # 2. Scrape de novos eventos
    eventos, datas_ok = await scrape_zerozero()

    if not eventos:
        print("⚠️ Nenhum evento português encontrado.")
        return

    # 3. Verificar adiamentos (antes de guardar novos)
    print("\n🔍 A verificar adiamentos...")
    verificar_adiamentos(eventos, datas_ok)

    # 4. Guardar na base de dados (upsert: atualiza existentes, insere novos)
    print(f"\n📦 A guardar {len(eventos)} eventos no Supabase...")
    guardados = 0
    erros = 0
    for ev in eventos:
        try:
            supabase.table("eventos").upsert(ev, on_conflict="nome,data").execute()
            guardados += 1
        except Exception as e:
            erros += 1
            if erros <= 5:
                print(f"  Erro DB: {e}")
            elif erros == 6:
                print("  ... (mais erros omitidos)")

    print(f"🏁 Feito. {guardados}/{len(eventos)} eventos guardados ({erros} erros).")

    # 5. Guardar cache de estádios para próximas execuções
    _save_cache()


if __name__ == "__main__":
    asyncio.run(main())
