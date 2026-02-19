import json
import random
from datetime import datetime, timedelta

def gerar_dados():
    # Coordenadas reais de locais no Distrito de Aveiro
    locais_aveiro = {
        "Estádio Municipal de Aveiro": {"lat": 40.6416, "lon": -8.6064},
        "Estádio Marcolino de Castro (Feira)": {"lat": 40.9255, "lon": -8.5414},
        "Estádio Municipal de Arouca": {"lat": 40.9333, "lon": -8.2439},
        "Estádio Carlos Osório (O. Azeméis)": {"lat": 40.8386, "lon": -8.4776},
        "Estádio Municipal de Anadia": {"lat": 40.4357, "lon": -8.4357},
        "Capela de São Gonçalinho (Aveiro)": {"lat": 40.6433, "lon": -8.6525},
        "Largo 1º de Maio (Águeda)": {"lat": 40.5755, "lon": -8.4447},
        "Praça da República (Ovar)": {"lat": 40.8601, "lon": -8.6247},
        "Forte da Barra (Gafanha da Nazaré)": {"lat": 40.6432, "lon": -8.7247},
        "Praia da Costa Nova (Ílhavo)": {"lat": 40.6127, "lon": -8.7511}
    }

    eventos = []
    
    data_base = datetime.now()

    # --- FUTEBOL ---
    jogos = [
        ("Beira-Mar vs Estarreja", "Estádio Municipal de Aveiro"),
        ("Feirense vs Oliveirense", "Estádio Marcolino de Castro (Feira)"),
        ("Arouca vs Sporting CP", "Estádio Municipal de Arouca"),
        ("Oliveirense vs Académico Viseu", "Estádio Carlos Osório (O. Azeméis)"),
        ("Anadia vs Sanjoanense", "Estádio Municipal de Anadia")
    ]

    for i, (nome, local) in enumerate(jogos):
        coord = locais_aveiro[local]
        # Data aleatória nos próximos 30 dias
        data_evento = data_base + timedelta(days=random.randint(1, 30))
        
        eventos.append({
            "id": i + 1,
            "nome": nome,
            "tipo": "Futebol",
            "data": data_evento.strftime("%Y-%m-%d"),
            "hora": "16:00",
            "local": local,
            "latitude": coord["lat"],
            "longitude": coord["lon"],
            "preco": f"{random.randint(5, 15)}€",
            "descricao": "Campeonato Distrital e Nacional.",
            # Link direto para Google Maps
            "url_maps": f"https://www.google.com/maps/search/?api=1&query={coord['lat']},{coord['lon']}"
        })

    # --- FESTAS / ROMARIAS ---
    festas = [
        ("Festa de São Gonçalinho", "Capela de São Gonçalinho (Aveiro)"),
        ("AgitÁgueda", "Largo 1º de Maio (Águeda)"),
        ("Carnaval de Ovar (Desfile)", "Praça da República (Ovar)"),
        ("Festival do Bacalhau", "Forte da Barra (Gafanha da Nazaré)"),
        ("Festa do Marisco", "Praia da Costa Nova (Ílhavo)")
    ]

    for i, (nome, local) in enumerate(festas):
        coord = locais_aveiro[local]
        data_evento = data_base + timedelta(days=random.randint(5, 45))
        
        eventos.append({
            "id": i + 6, # Continuar IDs
            "nome": nome,
            "tipo": "Festa/Romaria",
            "data": data_evento.strftime("%Y-%m-%d"),
            "hora": "20:00",
            "local": local,
            "latitude": coord["lat"],
            "longitude": coord["lon"],
            "preco": "Grátis" if random.choice([True, False]) else "5€",
            "descricao": "Música, gastronomia e tradição.",
            "url_maps": f"https://www.google.com/maps/search/?api=1&query={coord['lat']},{coord['lon']}"
        })

    # Guardar em JSON
    with open("eventos.json", "w", encoding="utf-8") as f:
        json.dump(eventos, f, ensure_ascii=False, indent=4)

    print("✅ Ficheiro 'eventos.json' criado com sucesso com 10 eventos em Aveiro!")

if __name__ == "__main__":
    gerar_dados()
