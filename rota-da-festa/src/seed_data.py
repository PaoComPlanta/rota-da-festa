import json
import random
import os
from datetime import datetime, timedelta

# ==========================================
# 1. BASE DE DADOS MASSIVA (Foco Braga)
# ==========================================

# Equipas e Estádios Reais - Foco AF BRAGA (60% da lista)
ESTADIOS_DISTRITAIS = [
    # --- AF BRAGA (O GROSSO DOS DADOS) ---
    {"equipa": "Merelinense FC", "estadio": "Estádio João Soares Vieira", "lat": 41.5768, "lon": -8.4482, "zona": "Braga"},
    {"equipa": "Maria da Fonte", "estadio": "Estádio Moinhos Novos", "lat": 41.6032, "lon": -8.2589, "zona": "Braga"},
    {"equipa": "Dumiense FC", "estadio": "Campo Celestino Lobo", "lat": 41.5621, "lon": -8.4328, "zona": "Braga"},
    {"equipa": "Vilaverdense", "estadio": "Campo Cruz do Reguengo", "lat": 41.6489, "lon": -8.4356, "zona": "Braga"},
    {"equipa": "GD Joane", "estadio": "Estádio de Barreiros", "lat": 41.4333, "lon": -8.4167, "zona": "Braga"},
    {"equipa": "Brito SC", "estadio": "Parque de Jogos do Brito SC", "lat": 41.4886, "lon": -8.3582, "zona": "Braga"},
    {"equipa": "Santa Maria FC", "estadio": "Estádio da Devesa", "lat": 41.5333, "lon": -8.5333, "zona": "Braga"},
    {"equipa": "Vieira SC", "estadio": "Estádio Municipal de Vieira", "lat": 41.6333, "lon": -8.1333, "zona": "Braga"},
    {"equipa": "AD Ninense", "estadio": "Complexo Desportivo de Nine", "lat": 41.4667, "lon": -8.5500, "zona": "Braga"},
    {"equipa": "GD Prado", "estadio": "Complexo Desportivo do Faial", "lat": 41.6000, "lon": -8.4667, "zona": "Braga"},
    {"equipa": "Pevidém SC", "estadio": "Parque de Jogos Albano Martins Coelho Lima", "lat": 41.4167, "lon": -8.3333, "zona": "Braga"},
    {"equipa": "Caçadores das Taipas", "estadio": "Estádio do Montinho", "lat": 41.4833, "lon": -8.3500, "zona": "Braga"},
    {"equipa": "Berço SC", "estadio": "Complexo Desportivo de Ponte", "lat": 41.4667, "lon": -8.3333, "zona": "Braga"},
    {"equipa": "CD Celeirós", "estadio": "Parque Desportivo de Celeirós", "lat": 41.5167, "lon": -8.4500, "zona": "Braga"},
    {"equipa": "Forjães SC", "estadio": "Estádio Horácio Queirós", "lat": 41.6167, "lon": -8.7333, "zona": "Braga"},
    {"equipa": "AD Fafe", "estadio": "Parque Municipal de Desportos de Fafe", "lat": 41.4500, "lon": -8.1667, "zona": "Braga"},
    {"equipa": "Desportivo de Ronfe", "estadio": "Estádio do Desportivo de Ronfe", "lat": 41.4333, "lon": -8.3667, "zona": "Braga"},
    {"equipa": "Sandineneses", "estadio": "Complexo Desportivo D. Maria Teresa", "lat": 41.4667, "lon": -8.3833, "zona": "Braga"},

    # --- AF AVEIRO ---
    {"equipa": "ADC Lobão", "estadio": "Parque de Jogos de Lobão", "lat": 40.9634, "lon": -8.4876, "zona": "Aveiro"},
    {"equipa": "Fiães SC", "estadio": "Estádio do Bolhão", "lat": 40.9921, "lon": -8.5235, "zona": "Aveiro"},
    {"equipa": "SC Espinho", "estadio": "Estádio Comendador Manuel Violas", "lat": 41.0068, "lon": -8.6291, "zona": "Aveiro"},
    {"equipa": "Beira-Mar", "estadio": "Estádio Municipal de Aveiro", "lat": 40.6416, "lon": -8.6064, "zona": "Aveiro"},
    {"equipa": "RD Águeda", "estadio": "Estádio Municipal de Águeda", "lat": 40.5744, "lon": -8.4485, "zona": "Aveiro"},

    # --- AF PORTO ---
    {"equipa": "SC Rio Tinto", "estadio": "Estádio Cidade de Rio Tinto", "lat": 41.1764, "lon": -8.5583, "zona": "Porto"},
    {"equipa": "Gondomar SC", "estadio": "Estádio de São Miguel", "lat": 41.1444, "lon": -8.5333, "zona": "Porto"},
    {"equipa": "Maia Lidador", "estadio": "Estádio Prof. Dr. José Vieira de Carvalho", "lat": 41.2333, "lon": -8.6167, "zona": "Porto"},
    {"equipa": "Leça FC", "estadio": "Estádio do Leça FC", "lat": 41.1833, "lon": -8.7000, "zona": "Porto"},
]

# Adversários para gerar variedade
ADVERSARIOS = {
    "Braga": ["Arões", "Serzedelo", "Ribeirão", "Martim", "Cabreiros", "Esposende", "Bairro", "Santa Eulália", "Porto d'Ave"],
    "Aveiro": ["Estarreja", "Ovarense", "Pampilhosa", "Alba", "Vista Alegre", "Cesarense", "Paivense"],
    "Porto": ["Pedras Rubras", "Dragões Sandinenses", "Vila Meã", "Foz", "Canidelo", "Infesta"]
}

COMPETICOES = {
    "Braga": ["Pro-Nacional AF Braga", "Divisão de Honra AF Braga", "Taça AF Braga"],
    "Aveiro": ["Campeonato SABSEG", "AF Aveiro 1ª Divisão"],
    "Porto": ["AF Porto Divisão de Elite", "AF Porto Honra"]
}

ESCALOES = ["Juniores A (Sub-19)", "Juvenis (Sub-17)", "Iniciados (Sub-15)", "Infantis (Sub-13)", "Benjamins", "Traquinas"]

# Locais Culturais (Foco Minho)
LOCAIS_CULTURA = [
    # Braga/Minho
    {"nome": "Pavilhão Multiusos de Guimarães", "lat": 41.4417, "lon": -8.3032, "zona": "Braga"},
    {"nome": "Praça da República (Braga)", "lat": 41.5515, "lon": -8.4216, "zona": "Braga"},
    {"nome": "Largo do Toural (Guimarães)", "lat": 41.4406, "lon": -8.2961, "zona": "Braga"},
    {"nome": "Campo da Feira (Barcelos)", "lat": 41.5317, "lon": -8.6193, "zona": "Braga"},
    {"nome": "Casa das Artes de Famalicão", "lat": 41.4116, "lon": -8.5198, "zona": "Braga"},
    {"nome": "Mosteiro de Tibães", "lat": 41.5562, "lon": -8.4795, "zona": "Braga"},
    {"nome": "Centro Cultural Vila Flor", "lat": 41.4394, "lon": -8.2952, "zona": "Braga"},
    # Outros
    {"nome": "Casa da Música (Porto)", "lat": 41.1589, "lon": -8.6307, "zona": "Porto"},
    {"nome": "Teatro Aveirense", "lat": 40.6406, "lon": -8.6538, "zona": "Aveiro"},
]

TIPOS_FESTA = [
    "Arraial Minhoto", "Feira de Artesanato", "Noite de Rusgas", "Encontro de Concertinas", 
    "Festival Folclórico", "Magusto Popular", "Cantares ao Desafio", "Feira de Velharias"
]

# ==========================================
# 2. FUNÇÕES GERADORAS
# ==========================================

def get_random_weekend_date(base_date, weeks_offset=0):
    """Gera data (Sábado/Domingo) nas próximas semanas."""
    # Encontrar próximo sábado
    days_until_sat = (5 - base_date.weekday() + 7) % 7
    if days_until_sat == 0: days_until_sat = 7
    
    next_saturday = base_date + timedelta(days=days_until_sat + (weeks_offset * 7))
    next_sunday = next_saturday + timedelta(days=1)
    
    return random.choice([next_saturday, next_sunday])

def generate_events():
    eventos = []
    base_date = datetime.now()
    count_id = 2000 # IDs altos

    print("🚀 A gerar 250+ eventos (Foco: AF Braga)...")

    # --- 1. FUTEBOL MASSIVO (200 eventos) ---
    # Geramos 4 fins de semana de jogos
    for semana in range(4): 
        for _ in range(50): # 50 jogos por fim de semana
            
            # Escolha ponderada: 70% chance de ser equipa de Braga
            if random.random() < 0.7:
                # Filtrar apenas equipas de Braga
                equipas_braga = [e for e in ESTADIOS_DISTRITAIS if e["zona"] == "Braga"]
                home = random.choice(equipas_braga)
            else:
                home = random.choice(ESTADIOS_DISTRITAIS)
            
            zona = home["zona"]
            adversario = random.choice(ADVERSARIOS.get(zona, ["Visitante"]))
            
            # 60% Formação (Sábados/Domingos manhã), 40% Seniores (Domingo tarde)
            is_senior = random.random() > 0.6 
            
            if is_senior:
                nome_jogo = f"{home['equipa']} vs {adversario}"
                categoria = random.choice(COMPETICOES[zona])
                preco = random.choice(["3€", "5€", "4€ (Sorteio Cabaz)", "Grátis"])
                
                # Seniores: Domingo à tarde
                data_jogo = get_random_weekend_date(base_date, semana)
                if data_jogo.weekday() == 5: data_jogo += timedelta(days=1) # Forçar Domingo
                hora = random.choice(["15:00", "15:30", "16:00"])
                desc = "Campeonato Distrital. Apoia a tua terra!"
            
            else:
                escalao = random.choice(ESCALOES)
                nome_jogo = f"{home['equipa']} ({escalao}) vs {adversario}"
                categoria = f"Formação - {escalao}"
                preco = "Grátis"
                
                # Formação: Sábado todo dia ou Domingo manhã
                data_jogo = get_random_weekend_date(base_date, semana)
                if data_jogo.weekday() == 6 and random.random() > 0.3: 
                    data_jogo -= timedelta(days=1) # Preferência por Sábado
                
                hora = random.choice(["09:00", "10:30", "11:00", "15:00", "17:00"])
                desc = f"Jogo de {escalao}. Vem ver o futuro do clube."

            eventos.append({
                "id": count_id,
                "nome": nome_jogo,
                "tipo": "Futebol",
                "categoria": categoria,
                "data": data_jogo.strftime("%Y-%m-%d"),
                "hora": hora,
                "local": home["estadio"],
                "latitude": home["lat"],
                "longitude": home["lon"],
                "preco": preco,
                "descricao": desc,
                "url_maps": f"https://www.google.com/maps/search/?api=1&query={home['lat']},{home['lon']}"
            })
            count_id += 1

    # --- 2. CULTURA & FESTAS (80 eventos) ---
    for semana in range(4):
        for _ in range(20):
            # Foco em locais de Braga
            if random.random() < 0.7:
                locais_braga = [l for l in LOCAIS_CULTURA if l["zona"] == "Braga"]
                local = random.choice(locais_braga)
            else:
                local = random.choice(LOCAIS_CULTURA)
            
            tipo = random.choice(TIPOS_FESTA)
            
            nomes = [
                f"{tipo} de {local['zona']}",
                f"Grande {tipo}",
                f"{tipo} da Freguesia",
                f"Noite de {tipo}"
            ]
            
            data_ev = get_random_weekend_date(base_date, semana)
            # Sexta à noite também conta
            if random.random() > 0.85: data_ev -= timedelta(days=random.choice([1, 2]))
            
            hora = random.choice(["21:00", "21:30", "16:00", "15:30"])
            
            eventos.append({
                "id": count_id,
                "nome": random.choice(nomes),
                "tipo": "Festa/Romaria",
                "categoria": tipo,
                "data": data_ev.strftime("%Y-%m-%d"),
                "hora": hora,
                "local": local["nome"],
                "latitude": local["lat"],
                "longitude": local["lon"],
                "preco": random.choice(["Grátis", "2€", "5€ (Com jantar)"]),
                "descricao": "Tradição, música e boa disposição. Organização local.",
                "url_maps": f"https://www.google.com/maps/search/?api=1&query={local['lat']},{local['lon']}"
            })
            count_id += 1

    # --- GUARDAR E ORDENAR ---
    path = os.path.join("rota-da-festa", "data", "eventos.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    eventos.sort(key=lambda x: x['data'])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(eventos, f, ensure_ascii=False, indent=4)
    
    print(f"✅ SUCESSO ABSOLUTO! {len(eventos)} eventos gerados.")
    print("   -> Foco principal: AF BRAGA (Pro-Nacional, Honra, Formação).")
    print("   -> Inclui cultura minhota (Rusgas, Concertinas).")

if __name__ == "__main__":
    generate_events()
