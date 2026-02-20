# 🎉 Rota da Festa — Todos os Eventos Desportivos de Portugal

**Rota da Festa** é uma plataforma que agrega automaticamente **todos os jogos de futebol em Portugal** — desde a Liga Portugal até à mais pequena divisão distrital — e os apresenta num mapa interativo com filtros, favoritos, previsão meteorológica e navegação GPS.

> Nunca mais percas um jogo perto de ti. De Benfica vs Porto ao Águias de Alvite vs Serzedelo.

---

## 📸 Funcionalidades

- 🗺️ **Mapa interativo** — Leaflet com clustering, dark mode, e localização GPS
- ⚽ **Cobertura total** — Liga Portugal, Liga 2, Liga 3, Taça, **todas as 20 AFs distritais**, formação (Sub-19 a Benjamins) e feminino
- 🔍 **Pesquisa e filtros** — Por nome, tipo (Futebol/Festa), escalão (Seniores, Sub-17, etc.)
- 📍 **Ordenação por distância** — Jogos mais pertos de ti aparecem primeiro
- 🌤️ **Previsão meteorológica** — Integração Open-Meteo para o dia de cada evento
- ⭐ **Favoritos** — Guarda eventos com sync localStorage + Supabase
- 📅 **Adicionar ao calendário** — Exporta para Google Calendar / iCal
- 🚗 **Navegação GPS** — Abre directamente no Google Maps / Apple Maps
- 📤 **Partilhar** — Web Share API nativa
- ⚠️ **Jogos adiados** — Detecção automática com badge visual
- 🔴 **Badges "Hoje" / "Amanhã"** — Destaque visual nos jogos próximos
- 📊 **Classificações** — Link directo para classificação da competição no ZeroZero
- 🌙 **Dark mode** — Tema claro/escuro com toggle

---

## 🏗️ Arquitetura

```
FestasNaArea/
├── rota-da-festa/              # Backend — Scraper Python
│   ├── src/
│   │   ├── scraper_mestre.py   # Scraper principal (~1000 LOC)
│   │   ├── app.py              # Dashboard Streamlit (legacy)
│   │   ├── data_generator.py   # Gerador de dados mock
│   │   └── seed_data.py        # Seed para desenvolvimento
│   ├── data/
│   │   └── eventos.json        # Cache local de eventos
│   ├── requirements.txt        # Dependências Streamlit
│   └── requirements_etl.txt    # Dependências do scraper
│
├── rota-da-festa-web/          # Frontend — Next.js 16
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # Página principal
│   │   │   ├── layout.tsx      # Layout root + ThemeProvider
│   │   │   ├── login/page.tsx  # Autenticação
│   │   │   └── submit/page.tsx # Submissão de eventos
│   │   ├── components/
│   │   │   ├── Map.tsx         # Mapa Leaflet interativo
│   │   │   ├── EventCard.tsx   # Card de evento
│   │   │   ├── EventDetailModal.tsx  # Modal detalhado
│   │   │   └── ThemeProvider.tsx     # Dark mode
│   │   └── utils/
│   │       └── supabase/
│   │           └── client.ts   # Cliente Supabase
│   └── package.json
│
├── .github/
│   └── workflows/
│       └── scrape.yml          # GitHub Action — scraper diário
└── .gitignore
```

---

## ⚽ Scraper — `scraper_mestre.py`

O coração do projecto. Um scraper assíncrono que navega o [ZeroZero.pt](https://www.zerozero.pt) com Playwright para recolher **todos** os jogos de futebol em Portugal.

### Funcionamento (duas fases)

#### Fase 1 — Agenda Diária
Scrape da página `/agenda.php` do ZeroZero para os próximos **7 dias**. Captura jogos das ligas profissionais e alguns distritais visíveis na agenda.

#### Fase 2 — Competições AF (Distritais + Formação)
Navega **25 competições** directamente no ZeroZero:
- **20 Associações de Futebol** distritais (Braga, Porto, Lisboa, Algarve, Madeira, Açores, etc.)
- **5 competições nacionais** (Liga 3, Juniores A/B/C, Feminina)

Para cada competição:
1. Visita a página da competição
2. Descobre links para as **edições actuais** (Honra, 1ª Divisão, 2ª Divisão, Juniores, etc.)
3. Navega ao **calendário** de cada edição
4. Extrai jogos dos próximos 7 dias

### Pipeline de dados

```
ZeroZero.pt → Playwright → BeautifulSoup → Filtro PT → Geolocalização → Supabase
```

1. **Parsing** — Dois parsers: `parse_games_from_html()` (agenda) e `extract_games_from_page()` (edições/calendários)
2. **Filtro português** — `is_portuguese_game()` verifica bandeira PT, keywords de competição, ou nome de equipa conhecido
3. **Geolocalização** — 6 tentativas em cadeia:
   - Cache de ~170 estádios (Liga Portugal → distritais)
   - Nominatim: "Estádio {equipa}, Portugal"
   - Nominatim: "{equipa} futebol, Portugal"
   - Extracção de localidade do nome (ex: "Águias de **Alvite**" → "Alvite, Portugal")
   - Nome da equipa como localidade
   - Fallback: centróide do distrito (24 distritos/AFs mapeados)
4. **Detalhes** — Visita cada página de jogo para extrair URLs de equipas e classificação
5. **Classificação** — `classificar_evento()` categoriza (Liga Portugal, Distrital, Formação, etc.) e estima preços
6. **Upsert** — Supabase upsert com `on_conflict="nome,data"`

### Ciclo de vida dos eventos

| Dia | Acção |
|-----|-------|
| **Diariamente (03:00 UTC)** | Scrape novos eventos + verificar adiamentos |
| **Quinta-feira** | Limpeza de eventos passados (resultados do fim-de-semana ficam visíveis até quinta) |
| **Adiamentos** | Compara DB vs scrape — se um jogo desaparece da agenda, marca como "adiado" |
| **Remarcações** | Se o jogo aparece numa nova data, actualiza com nota de remarcação |

### Constantes e dados

- **`CACHE_ESTADIOS`** — ~170 estádios com coordenadas (Liga Portugal, Liga 2, Liga 3, distritais de Braga, Porto, Aveiro, etc.)
- **`DISTRICT_CENTROIDS`** — 24 centróides de distrito para fallback de geolocalização
- **`PORTUGUESE_COMP_KEYWORDS`** — 30+ keywords para identificar competições portuguesas
- **`PT_COMPETITION_URLS`** — 25 URLs de competições do sitemap do ZeroZero

---

## 🌐 Frontend — Next.js

Single-page app responsiva, optimizada para mobile.

### Páginas

| Rota | Descrição |
|------|-----------|
| `/` | Página principal — lista de eventos, mapa, filtros, pesquisa |
| `/login` | Autenticação via Supabase Auth |
| `/submit` | Formulário para submissão manual de eventos (status "pendente" até aprovação) |

### Componentes

| Componente | Funcionalidade |
|-----------|----------------|
| **`Map.tsx`** | Mapa Leaflet com markers coloridos por tipo, clustering, dark tiles, fly-to animation |
| **`EventCard.tsx`** | Card com badges (tipo, escalão, distância, 🔴Hoje, Amanhã, ⚠️Adiado), favoritos |
| **`EventDetailModal.tsx`** | Modal completo: meteorologia (Open-Meteo), equipas com links ZeroZero, classificação, acções rápidas (mapa, GPS, calendário, partilhar), eventos próximos |
| **`ThemeProvider.tsx`** | Dark/light mode com persistência localStorage |

### Filtros disponíveis

- **Tipo**: Todos / Futebol / Festa-Romaria
- **Escalão**: Todos / Seniores / Sub-19 / Sub-17 / Sub-15 / Sub-13 / Benjamins
- **Pesquisa**: Texto livre (equipas, festas)
- **Localização**: Braga / Porto / Aveiro / GPS
- **Ordenação**: Por distância (com GPS) ou por data
- **Status**: Eventos "adiado" aparecem no fim da lista com estilo visual distinto

---

## 🗄️ Base de Dados — Supabase

### Tabela `eventos`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | serial | PK auto-incremento |
| `nome` | text | Nome do evento (ex: "Benfica vs Porto") |
| `tipo` | text | "Futebol" ou "Festa/Romaria" |
| `categoria` | text | "Liga Portugal", "Futebol Distrital", "Formação - Sub-17", etc. |
| `escalao` | text | "Seniores", "Sub-19", "Sub-17", "Sub-15", etc. |
| `equipa_casa` | text | Nome da equipa da casa |
| `equipa_fora` | text | Nome da equipa visitante |
| `data` | date | Data do evento (YYYY-MM-DD) |
| `hora` | text | Hora (HH:MM) |
| `local` | text | Nome do estádio/local |
| `latitude` | float | Coordenada GPS |
| `longitude` | float | Coordenada GPS |
| `preco` | text | Preço estimado (ex: "~3€ (estimado)", "Grátis") |
| `descricao` | text | Descrição gerada automaticamente |
| `status` | text | "aprovado", "pendente", "adiado" |
| `url_jogo` | text | URL do jogo no ZeroZero |
| `url_equipa_casa` | text | URL da equipa da casa no ZeroZero |
| `url_equipa_fora` | text | URL da equipa visitante no ZeroZero |
| `url_classificacao` | text | URL da classificação no ZeroZero |
| `url_maps` | text | Link Google Maps |

**Constraint único**: `(nome, data)` — permite upsert sem duplicados.

### Tabela `favoritos`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `user_id` | uuid | FK para auth.users |
| `evento_id` | integer | FK para eventos.id |

---

## ⚙️ GitHub Actions

### `scrape.yml` — Scraper Diário

```yaml
name: Correr Scraper Diário
on:
  schedule:
    - cron: '0 3 * * *'   # Todos os dias às 03:00 UTC
  workflow_dispatch:        # Botão manual "Run workflow"
```

- **Runner**: `ubuntu-latest`
- **Timeout**: 120 minutos (o scraper pode demorar 30-60 min com todas as AFs)
- **Python**: 3.10 + Playwright Chromium
- **Secrets necessários**:
  - `SUPABASE_URL` — URL do projecto Supabase
  - `SUPABASE_SERVICE_KEY` — Service role key (com permissões de escrita)

---

## 🚀 Setup Local

### Pré-requisitos

- Node.js 18+
- Python 3.10+
- Conta Supabase (free tier funciona)

### Frontend

```bash
cd rota-da-festa-web
npm install

# Criar .env.local com:
# NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
# NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

npm run dev
# → http://localhost:3000
```

### Scraper (local)

```bash
cd rota-da-festa
python -m venv venv
source venv/bin/activate
pip install -r requirements_etl.txt
pip install supabase
playwright install --with-deps chromium

# Criar .env com:
# SUPABASE_URL=https://xxx.supabase.co
# SUPABASE_SERVICE_KEY=eyJ...

python src/scraper_mestre.py
```

### Supabase

1. Criar projecto em [supabase.com](https://supabase.com)
2. Criar tabela `eventos` com o schema acima (ou usar o seed em `seed_data.py`)
3. Criar tabela `favoritos` com FK para `eventos`
4. Configurar RLS (Row Level Security) conforme necessário
5. Copiar URL e keys para os ficheiros `.env`

---

## 🛠️ Tech Stack

| Camada | Tecnologia |
|--------|-----------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| **Mapa** | Leaflet, React-Leaflet |
| **Base de dados** | Supabase (PostgreSQL) |
| **Scraping** | Playwright (async), BeautifulSoup 4 |
| **Geolocalização** | Geopy / Nominatim (OpenStreetMap) |
| **Meteorologia** | Open-Meteo API (gratuita, sem key) |
| **CI/CD** | GitHub Actions (cron diário) |
| **Hosting** | Vercel (frontend) — opcional |

---

## 📊 Números

- **~170** estádios em cache com coordenadas GPS
- **20** Associações de Futebol distritais cobertas
- **25+** competições scrapeadas por execução
- **7 dias** de janela de eventos futuros
- **6 tentativas** de geolocalização por equipa desconhecida
- **~30+ keywords** para identificar competições portuguesas
- **24 distritos** com centróides de fallback

---

## 📝 Licença

Projecto académico / pessoal. Dados desportivos do [ZeroZero.pt](https://www.zerozero.pt).
