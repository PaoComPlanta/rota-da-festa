import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, LocateControl
import json
import os
import math
from datetime import datetime

# --- CONFIGURAÇÃO GLOBAL ---
st.set_page_config(
    page_title="Rota da Festa 🇵🇹",
    page_icon="🎉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PROFISSIONAL ---
st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; }
    
    /* Cartões de Eventos */
    .event-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left: 6px solid #ff4b4b;
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    .event-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0,0,0,0.12);
    }
    .event-card h4 { margin-top: 0; color: #2c3e50; }
    .event-card .meta { color: #7f8c8d; font-size: 0.9rem; margin-bottom: 0.5rem; }
    .event-card .price { 
        background: #f1f2f6; color: #2c3e50; padding: 4px 8px; 
        border-radius: 6px; font-weight: bold; font-size: 0.85rem; 
    }
    
    /* Botões */
    .stButton button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES UTILITÁRIAS ---

def haversine(lat1, lon1, lat2, lon2):
    """Calcula a distância em km entre dois pontos."""
    R = 6371  # Raio da Terra em km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@st.cache_data
def carregar_dados():
    path = os.path.join(os.path.dirname(__file__), '../data/eventos.json')
    if not os.path.exists(path):
        return pd.DataFrame()
    
    with open(path, "r", encoding="utf-8") as f:
        dados = json.load(f)
    
    df = pd.DataFrame(dados)
    if not df.empty:
        df['data_obj'] = pd.to_datetime(df['data'])
        df['dia_semana'] = df['data_obj'].dt.strftime('%a') # Seg, Ter...
    return df

# --- GESTÃO DE ESTADO (FAVORITOS) ---
if 'favoritos' not in st.session_state:
    st.session_state.favoritos = set()

def toggle_fav(id_evento):
    if id_evento in st.session_state.favoritos:
        st.session_state.favoritos.remove(id_evento)
    else:
        st.session_state.favoritos.add(id_evento)

# --- SIDEBAR (CONTROLO) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/785/785116.png", width=80)
    st.title("Rota da Festa")
    
    # 1. Onde estou?
    locais_base = {
        "Aveiro (Centro)": (40.6405, -8.6538),
        "Porto (Aliados)": (41.1469, -8.6111),
        "Braga (Sé)": (41.5503, -8.4270),
        "Guimarães": (41.4425, -8.2918),
        "Águeda": (40.5744, -8.4485),
        "Ovar": (40.8601, -8.6247),
        "S. M. Feira": (40.9255, -8.5414),
    }
    user_loc_name = st.selectbox("📍 Onde estás?", list(locais_base.keys()))
    user_lat, user_lon = locais_base[user_loc_name]

    st.divider()

    # 2. Filtros
    df = carregar_dados()
    if df.empty:
        st.error("Sem dados! Corre 'seed_data.py'.")
        st.stop()
        
    tipos = st.multiselect("Tipo", df['tipo'].unique(), default=df['tipo'].unique())
    
    # Filtro de Data
    hoje = datetime.now().date()
    data_filtro = st.date_input("A partir de:", value=hoje)
    
    # Pesquisa Texto
    search_term = st.text_input("🔎 Pesquisar evento...", "").lower()

# --- LÓGICA DE FILTRAGEM ---
# Calcular distâncias primeiro
df['distancia'] = df.apply(
    lambda row: haversine(user_lat, user_lon, row['latitude'], row['longitude']), axis=1
)

# Aplicar filtros
mask = (
    (df['tipo'].isin(tipos)) &
    (df['data_obj'].dt.date >= data_filtro) &
    (df['nome'].str.lower().str.contains(search_term) | df['local'].str.lower().str.contains(search_term))
)
df_filtrado = df[mask].sort_values(by=['data_obj', 'distancia'])

# --- DASHBOARD (KPIs) ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Eventos Encontrados", len(df_filtrado))
col2.metric("Próximo Jogo", "Hoje" if not df_filtrado.empty and df_filtrado.iloc[0]['data'] == str(hoje) else "Brevemente")
col3.metric("Temperatura", "18ºC", "🌤️") # Simulado (podia vir de API)
col4.metric("Favoritos", len(st.session_state.favoritos))

# --- MAPA INTERATIVO (CLUSTER) ---
st.subheader("🗺️ Mapa de Eventos")

# Mapa Base
m = folium.Map(location=[user_lat, user_lon], zoom_start=11, tiles="Cartodb Positron")

# Adicionar "Eu"
folium.Marker(
    [user_lat, user_lon], 
    tooltip="Estás aqui", 
    icon=folium.Icon(color="blue", icon="user", prefix="fa")
).add_to(m)

# Cluster para eventos
marker_cluster = MarkerCluster().add_to(m)

for _, row in df_filtrado.iterrows():
    # Cor baseada no tipo
    cor = "green" if row['tipo'] == "Futebol" else "red"
    icon = "futbol-o" if row['tipo'] == "Futebol" else "glass"
    
    html = f"""
    <div style='font-family: sans-serif; min-width: 180px'>
        <b>{row['nome']}</b><br>
        <small>{row['data']} • {row['hora']}</small><br>
        <span style='color: green'>{row['preco']}</span><br>
        <a href='{row['url_maps']}' target='_blank'>Navegar ➔</a>
    </div>
    """
    
    folium.Marker(
        [row['latitude'], row['longitude']],
        popup=html,
        tooltip=f"{row['nome']} ({row['distancia']:.1f} km)",
        icon=folium.Icon(color=cor, icon=icon, prefix="fa")
    ).add_to(marker_cluster)

# OTIMIZAÇÃO CRÍTICA: returned_objects=[] impede que o mapa recarregue a app ao fazer zoom/pan
st_folium(m, width="100%", height=450, returned_objects=[])

# --- LISTA DETALHADA ---
st.subheader("📅 Lista de Eventos")

tab1, tab2 = st.tabs(["Todos os Eventos", "⭐ Meus Favoritos"])

with tab1:
    if df_filtrado.empty:
        st.info("Nenhum evento corresponde aos filtros.")
    else:
        for idx, row in df_filtrado.iterrows():
            # Cartão Customizado HTML + Streamlit
            with st.container():
                col_info, col_action = st.columns([3, 1])
                
                with col_info:
                    st.markdown(f"""
                    <div class="event-card" style="border-left-color: {'#2ecc71' if row['tipo'] == 'Futebol' else '#e74c3c'}">
                        <h4>{row['nome']} <span style="font-size:0.8em; color:#999">({row['distancia']:.1f} km)</span></h4>
                        <div class="meta">📍 {row['local']} • 📅 {row['dia_semana']}, {row['data']} às {row['hora']}</div>
                        <span class="price">{row['preco']}</span> • <small>{row.get('descricao', '')}</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_action:
                    st.write("") # Espaçamento
                    st.write("")
                    # Botão Favorito
                    is_fav = row['id'] in st.session_state.favoritos
                    label_fav = "❤️ Remover" if is_fav else "🤍 Guardar"
                    if st.button(label_fav, key=f"fav_{row['id']}"):
                        toggle_fav(row['id'])
                        st.rerun()
                        
                    st.markdown(f"[📍 Ir Agora]({row['url_maps']})", unsafe_allow_html=True)

with tab2:
    if not st.session_state.favoritos:
        st.info("Ainda não tens favoritos. Adiciona alguns na aba 'Todos'!")
    else:
        df_fav = df[df['id'].isin(st.session_state.favoritos)]
        st.dataframe(df_fav[['nome', 'data', 'hora', 'local', 'preco']], use_container_width=True)
