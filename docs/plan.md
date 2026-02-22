# ROTA DA FESTA — Documento de Referência do Projeto

> **INSTRUÇÃO PARA IAs**: Lê este documento COMPLETO antes de qualquer alteração ao código.
> Após cada alteração, verifica se continua alinhada com a arquitetura, regras e fase atual.
> Não alteres ficheiros fora do scope da tarefa pedida. Não apagues código funcional.

---

## 1. O QUE É ESTE PROJETO

**Rota da Festa** é uma web app portuguesa que agrega TODOS os eventos de futebol (profissional até distrital/formação) e, futuramente, festas populares e cultura local, mostrando-os num mapa interativo. O objetivo é ser a "bússola do fim de semana" para qualquer pessoa em Portugal.

**Proposta de valor**: Nenhuma app faz a ponte entre futebol regional e economia local. Um pai vai ver o jogo dos iniciados e descobre uma feira gastronómica a 2km. A app é e será sempre **gratuita** para o utilizador.

**Repo**: `github.com/PaoComPlanta/rota-da-festa` (branch `main`)

---

## 2. ARQUITETURA E ESTRUTURA

```
FestasNaArea/
├── .github/workflows/
│   └── scrape.yml                    # GitHub Action — corre scraper diariamente 03:00 UTC
├── README.md                          # Documentação pública do repo
├── rota-da-festa/                     # Backend (Python)
│   ├── src/
│   │   ├── scraper_mestre.py          # ★ CORE — scraper ZeroZero + lifecycle + geocoding (~1100 linhas)
│   │   ├── app.py                     # Flask app (não usado em produção)
│   │   ├── data_generator.py          # Gerador de dados dummy (dev)
│   │   └── seed_data.py              # Seed inicial (dev)
│   ├── requirements.txt
│   └── requirements_etl.txt
├── rota-da-festa-web/                 # Frontend (Next.js)
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # ★ Página principal — mapa + lista + filtros
│   │   │   ├── layout.tsx             # Root layout (ThemeProvider, metadata)
│   │   │   ├── login/page.tsx         # Página de login
│   │   │   └── submit/page.tsx        # Formulário submeter evento
│   │   ├── components/
│   │   │   ├── EventCard.tsx          # ★ Card de evento (badges Hoje/Amanhã/Adiado)
│   │   │   ├── EventDetailModal.tsx   # ★ Modal detalhe (meteo, equipas, maps, adiamentos)
│   │   │   ├── Map.tsx               # Mapa Leaflet com pins
│   │   │   └── ThemeProvider.tsx     # Dark/light mode
│   │   ├── utils/supabase/
│   │   │   └── client.ts            # Supabase client (anon key)
│   │   └── scraper_mestre_db.py      # Cópia antiga (ignorar)
│   ├── package.json
│   └── tsconfig.json
```

### Tech Stack
| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Frontend | Next.js + React + TypeScript | 16.x / 19.x |
| Styling | Tailwind CSS | 4.x |
| Mapa | Leaflet + react-leaflet | 1.9 / 5.0 |
| Backend/DB | Supabase (PostgreSQL) | Cloud |
| Scraper | Python + Playwright + BeautifulSoup | 3.10 |
| Geocoding | Nominatim (geopy) | — |
| Meteorologia | Open-Meteo API | — |
| CI/CD | GitHub Actions | — |
| Hosting | Vercel | — |

### Variáveis de Ambiente
```
# Frontend (rota-da-festa-web/.env.local)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhb...

# Scraper (GitHub Actions secrets)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhb...
GROQ_API_KEY=gsk_...            # Disponível mas não usado ainda
```

---

## 3. BASE DE DADOS (Supabase)

### Tabela `eventos` (atual)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
nome            TEXT NOT NULL          -- "Benfica vs Porto"
tipo            TEXT                   -- "Futebol"
categoria       TEXT                   -- "Liga Portugal", "Futebol Distrital", "Formação - Sub-15"
escalao         TEXT                   -- "Seniores", "Sub-19", "Sub-17", etc.
equipa_casa     TEXT
equipa_fora     TEXT
url_jogo        TEXT                   -- URL ZeroZero do jogo
url_equipa_casa TEXT                   -- URL ZeroZero da equipa (pode estar vazio)
url_equipa_fora TEXT                   -- URL ZeroZero da equipa (pode estar vazio)
url_classificacao TEXT                 -- URL ZeroZero classificação (pode estar vazio)
data            TEXT NOT NULL          -- "2026-02-22"
hora            TEXT                   -- "15:00" ou "A definir"
local           TEXT                   -- "Estádio da Luz" ou "Braga (aproximado)"
latitude        FLOAT
longitude       FLOAT
preco           TEXT                   -- "~15€ (estimado)", "Grátis", "Variável"
descricao       TEXT
url_maps        TEXT                   -- Google Maps deep link
status          TEXT DEFAULT 'aprovado' -- "aprovado" | "adiado" | "pendente"
created_at      TIMESTAMPTZ DEFAULT now()
```
**Upsert key**: `(nome, data)` — mesmo jogo+data atualiza; data diferente cria novo registo.

### Tabela `favoritos` (atual)
```sql
id         UUID PRIMARY KEY
user_id    TEXT
event_id   UUID REFERENCES eventos(id)
created_at TIMESTAMPTZ DEFAULT now()
```

---

## 4. SCRAPER — COMO FUNCIONA

**Ficheiro**: `rota-da-festa/src/scraper_mestre.py`

### Pipeline de execução (main)
```
1. limpar_eventos_concluidos()    — Só às quintas: apaga eventos com data < ontem
2. scrape_zerozero()              — Fase 1 (agenda) + Fase 2 (AFs/competições)
3. verificar_adiamentos()         — Compara DB vs scrape fresco → marca "adiado"
4. Upsert no Supabase            — on_conflict="nome,data"
```

### Fase 1: Agenda global
- Visita `zerozero.pt/agenda.php?date=YYYY-MM-DD` para hoje + 6 dias
- Parseia `table.agenda_list tr` e `li.game` (dois layouts do ZeroZero)
- Filtra jogos portugueses via `is_portuguese_game()` (bandeira PT, keywords, cache de equipas)

### Fase 2: Competições distritais e formação
- Visita 25 URLs fixas (`PT_COMPETITION_URLS`): 20 AFs + Liga 3 + Juniores A/B/C + Feminina
- Descobre sub-competições (`/competicao/`) e edições (`/edicao/`)
- Para cada edição, visita `/proximos-jogos` (preferencial) ou página principal
- Extrai jogos via `extract_games_from_page()` + `parse_games_from_html()`
- **Problema atual**: A Fase 2 encontra edições mas ainda retorna 0 jogos (debug em progresso)

### Geocoding (6 passos de fallback)
```
1. CACHE_ESTADIOS (dict ~150 equipas hardcoded)
2. Nominatim: "Estádio {equipa}, Portugal"
3. Nominatim: "{equipa} futebol, Portugal"
4. Extrair localidade do nome: "Águias de Alvite" → "Alvite, Portugal"
5. DISTRICT_CENTROIDS (centróide do distrito da competição)
6. None → jogo descartado
```
**Rate limit**: `time.sleep(1.1)` entre chamadas Nominatim. Set `_GEO_FAILED` evita repetir equipas falhadas.

### Classificação de eventos (`classificar_evento`)
Retorna `(categoria, preço, escalão)`. A ordem de matching é:
1. Formação (Sub-19/17/15/13/etc.) → sempre "Grátis"
2. Competições europeias (Champions, Europa League, UEFA)
3. Liga Portugal, Liga 2, Liga 3
4. Taça de Portugal, Taça da Liga, Supertaça
5. Liga Revelação, Futebol Feminino
6. Campeonato de Portugal, Divisão de Honra
7. Distrital (só se tiver "af ", "distrital", "divisão" no texto)
8. Amigável
9. **Default**: "Futebol" / "Variável" (genérico, não assume distrital)

---

## 5. FRONTEND — COMPORTAMENTO ATUAL

### page.tsx (página principal)
- Carrega eventos do Supabase com `status IN ('aprovado', 'adiado')`
- `pendente` não é mostrado ao utilizador
- Adiados aparecem no fim da lista com opacidade reduzida
- Filtros: pesquisa texto, categoria, escalão (se implementado)
- Mapa Leaflet com pins clicáveis

### EventCard.tsx
- Badges: 🔴 "HOJE" (data === hoje), "Amanhã" (data === amanhã), ⚠️ "ADIADO" (status)
- Adiados: borda laranja, opacidade 70%

### EventDetailModal.tsx
- Meteorologia via Open-Meteo API (latitude/longitude do evento)
- Links "Ver equipa": usa `url_equipa_casa/fora` se disponível, senão pesquisa ZeroZero
- Link "Classificação": usa `url_classificacao` se disponível, senão pesquisa ZeroZero
- Banner laranja para eventos adiados
- Botão Google Maps

---

## 6. REGRAS E RESTRIÇÕES

### Para qualquer IA que altere o código:
1. **Não remover** CACHE_ESTADIOS, DISTRICT_CENTROIDS, PT_COMPETITION_URLS — são dados essenciais
2. **Não simplificar** o geocoding removendo fallbacks — equipas desconhecidas precisam deles
3. **Upsert key é `(nome, data)`** — não alterar sem migração
4. **url_equipa_casa/fora/classificacao podem estar vazios** — o frontend tem fallbacks
5. **O scraper corre em GitHub Actions** (Ubuntu, Python 3.10, Playwright Chromium) — testar compatibilidade
6. **Nominatim tem rate limit de 1 req/s** — manter `time.sleep(1.1)` entre chamadas
7. **ZeroZero bloqueia requests diretos** — usar sempre Playwright com user-agent de browser
8. **A app é grátis para o utilizador** — nunca implementar paywall para funcionalidades core
9. **Scraper timeout**: 90 minutos no GitHub Actions — otimizar se aproximar deste limite
10. **Língua**: Código em inglês (nomes de funções), strings e UI em **português de Portugal**

### Convenções de código
- **Python**: snake_case, docstrings em português, prints com emojis para logging
- **TypeScript/React**: camelCase, componentes funcionais, Tailwind para styling
- **Commits**: incluir `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`

---

## 7. PROBLEMAS CONHECIDOS (Fev 2026)

| # | Problema | Estado | Notas |
|---|---------|--------|-------|
| 1 | Fase 2 retorna 0 jogos distritais | 🔧 Debug | Edições encontradas mas `/proximos-jogos` pode não ter jogos. Debug logging adicionado |
| 2 | ~77 eventos no Supabase (devia ter 200+) | 🔧 Depende de #1 | Fase 1 funciona (59 jogos), Fase 2 precisa funcionar |
| 3 | Jogos não-distritais marcados como "Futebol Distrital" | ✅ Corrigido | Default mudado para "Futebol" genérico |
| 4 | url_equipa_casa/fora sempre vazios | ✅ Aceite | Removido scraping individual para performance. Frontend tem fallback |
| 5 | GROQ_API_KEY configurada mas não usada | ⏳ Futuro | Será usada para classificação automática e chatbot |

---

## 8. ROADMAP DE FASES

### FASE 1 — Solidificar o Futebol (Mar 2026) ← ESTAMOS AQUI
**Meta**: Melhor experiência map-first para futebol português em TODOS os escalões.

**Técnico**:
- [ ] Resolver Fase 2 do scraper (distritais + formação a aparecer)
- [ ] Filtro por escalão no frontend (Seniores / Sub-19 / Sub-17 / Sub-15 / etc.)
- [ ] Filtro por distrito/AF no frontend
- [ ] "Perto de mim" — ordenar por distância GPS
- [ ] Botão "Levar-me lá" (deep link Google/Apple Maps)
- [ ] PWA: manifest.json + service worker (instalar no ecrã, 0€)
- [ ] Cache de estádios persistente (JSON no repo em vez de só memória)
- [ ] Páginas SEO: `/jogos/braga`, `/jogos/porto` (Next.js SSR/ISR)

### FASE 2 — Festas Populares e Cultura (Abr-Mai 2026)
**Meta**: Ser a "bússola do fim de semana" completa (futebol + festas + cultura).

**Técnico**:
- [ ] Scraper de câmaras municipais e juntas de freguesia (agendas culturais públicas)
- [ ] Scraper de sites de festas (festasromarias.pt, vfreguesia.pt)
- [ ] Parser de PDFs com Groq LLM (programas de festas → eventos estruturados)
- [ ] Formulário "Submeter Evento" (qualquer pessoa adiciona uma festa)
- [ ] Moderação automática via Groq (classificar, detetar spam)
- [ ] Novas categorias: 🎪 Festas, 🎵 Concertos, 🍖 Feiras, 🎭 Teatro, 🏃 Desporto, 🔥 Tradições

**DB**: Adicionar colunas: `subcategoria`, `fonte`, `verificado`, `imagem_url`, `tags[]`

### FASE 3 — Comunidade e Viralidade (Jun-Jul 2026)
**Meta**: Crescimento orgânico. Verão = pico de festas, tem de estar pronto.

- [ ] Login Google/Apple (Supabase Auth, grátis até 50k MAU)
- [ ] "Vou a este evento" — contador social
- [ ] Reviews e fotos de eventos (Supabase Storage)
- [ ] Open Graph tags (previews bonitos ao partilhar)
- [ ] Chatbot Groq: "O que há perto de Guimarães este sábado?"

### FASE 4 — Monetização (Set 2026+)
Detalhes completos na secção 9.

### FASE 5 — Apps Nativas (Q4 2026)
- Capacitor.js wrapa o Next.js → Android + iOS com 1 codebase
- Google Play (25€ uma vez) + Apple Developer (99€/ano)
- Funcionalidades nativas: geofencing, widget ecrã, modo offline, deep links

---

## 9. MONETIZAÇÃO — Guia de Execução

### Princípio: A app é GRÁTIS para sempre. Receita vem dos negócios locais.

### Modelo 1: Pins Patrocinados no Mapa (receita principal)
Um restaurante/café paga para aparecer no mapa junto aos eventos.

| Plano | Preço | Inclui |
|-------|-------|--------|
| Básico | 10€/mês | Pin no mapa + nome + telefone |
| Destaque | 20€/mês | Pin + banner no evento + cupão desconto |
| Premium | 35€/mês | Tudo + push notification aos utilizadores perto |

**Implementação técnica**:
1. Tabela `negocios` no Supabase (nome, tipo, lat/lon, plano, ativo, cupao_texto)
2. Pins dourados no mapa para negócios pagos
3. Secção "Comer e beber perto" no EventDetailModal (raio 2km)
4. Stripe Checkout (0€ até cobrar, 1.4% + 0.25€/transação)
5. Webhook Stripe → Supabase Edge Function → ativa pin

**Passos do fundador**:
1. Criar conta Stripe (grátis)
2. Criar 3 Payment Links no dashboard Stripe (um por plano, sem código)
3. Landing page: "O seu negócio no mapa da Rota da Festa"
4. Início manual: negócio paga → tu adicionas à tabela
5. Automatizar com webhook quando >10 clientes

### Modelo 2: Cupões
"Mostre este ecrã → 10% desconto." Implementar com campo `cupao_texto` na tabela `negocios`, botão "Ver Cupão" com código/QR, tracking de aberturas.

### Modelo 3: Destaque de Eventos
Organizador paga 15€ para evento no topo + badge especial + push notification. Só ativar após ter festas populares (Fase 2+).

### Modelo 4: Dados Agregados (médio prazo)
Insights anónimos para AFs e Câmaras: "800 pessoas pesquisaram Sub-15 em Braga este mês." Receita passiva quando houver volume.

---

## 10. PUBLICIDADE E CRESCIMENTO

### Fase A: Pré-lançamento (<100 utilizadores)
1. Criar @rotadafesta no Instagram e TikTok. Bio: "Todos os jogos e festas de Portugal. No mapa. Grátis."
2. Registar domínio rotadafesta.pt (7-10€/ano)
3. Partilhar nos grupos WhatsApp pessoais
4. Reddit (r/portugal, r/PrimeiraLiga): "Fiz uma app gratuita que mostra todos os jogos no mapa"
5. DMs a 5 páginas Instagram de futebol regional

### Fase B: Crescimento orgânico (100-1000 utilizadores)
1. **Grupos Facebook regionais** (3-5/semana): "Futebol Braga", "AF Braga", "Festas Minho", "Braga Viva"
   - Mensagem tipo: "Boas! Fiz uma app gratuita que mostra os jogos todos no mapa. [link]. Aceito sugestões!"
2. **Pais de formação** (público-ouro): Contactar treinadores → partilham no WhatsApp dos pais → 20-30 users instantâneos
3. **Conteúdo semanal**: Sexta = "Jogos do FDS em [Distrito]". Domingo = "Resumo: X jogos". Stories/Reels filmando jogo distrital
4. **SEO**: Páginas `/jogos/braga`, `/jogos/porto` → Google indexa → tráfego passivo
5. **Parcerias AFs**: Email oferecendo widget embed gratuito para o site da AF

### Fase C: Escalar (1000-10000 utilizadores)
1. **Imprensa local**: Pitch a Correio do Minho, JN regional: "Jovem português cria app gratuita para futebol regional"
2. **Referral**: "Partilha com 3 amigos → desbloqueia dark mode/alertas personalizados"
3. **Presencial**: Ir a jogos distritais com autocolantes/QR codes
4. **Festas**: Contactar comissões de festas: "Adicionamos a vossa festa ao mapa, de graça. Partilham?"

### Fase D: Viralidade (10000+ utilizadores)
1. "Mapa viral do verão" — mapa interativo de TODAS as festas populares de Portugal
2. YouTubers/TikTokers de Portugal/viagens
3. Product Hunt + Hacker News launch

---

## 11. CRONOGRAMA SEMANAL

### Março 2026
| Sem | Técnico | Marketing | Monetização |
|-----|---------|-----------|-------------|
| 1 | Resolver scraper distritais | Criar @rotadafesta IG/TikTok | Criar conta Stripe |
| 2 | Filtros escalão/distrito frontend | 1º post + 3 grupos FB | Landing page negócios |
| 3 | PWA (manifest + service worker) | Reddit + DMs páginas futebol | Contactar 2 restaurantes |
| 4 | Páginas SEO por distrito | Post semanal "Jogos do FDS" | 1º cliente? → validação |

### Abril 2026
| Sem | Técnico | Marketing | Monetização |
|-----|---------|-----------|-------------|
| 1 | Scraper festas populares | Contactar 3 treinadores | Pins no mapa implementados |
| 2 | Formulário submeter evento | Contactar AF Braga/Porto | Stripe Payment Links live |
| 3 | Groq classificação eventos | Imprensa local | Landing page live |
| 4 | Categorias festas frontend | Expandir Aveiro grupos FB | Contactar 5 negócios |

### Maio 2026
| Sem | Técnico | Marketing | Monetização |
|-----|---------|-----------|-------------|
| 1 | Login social + "Vou" | Vídeo (ir a jogo distrital) | Cupões implementados |
| 2 | UGC + moderação Groq | Parcerias festas verão | Dashboard negócios |
| 3 | Push notifications PWA | SEO otimizar | Meta: 5 negócios a pagar |
| 4 | Performance + polish | Preparar "mapa do verão" | Referral program |

### Junho 2026 (VERÃO)
| Sem | Técnico | Marketing | Monetização |
|-----|---------|-----------|-------------|
| 1 | Mapa todas as festas | LANÇAR "Mapa do Verão" | Aumentar preços? |
| 2 | Capacitor.js → APK | Imprensa: "App mapeia festas" | + distritos |
| 3 | Play Store submit | Product Hunt / HN | Destaque eventos |
| 4 | iOS TestFlight | Santos Populares promo | Meta: 15 negócios, 500€/mês |

---

## 12. APIs GRATUITAS

| API | Uso | Limite Gratuito |
|-----|-----|----------------|
| **Groq** | LLM (classificação, chatbot, extração) | 30 req/min, Llama 3.3 70B |
| **Supabase** | DB + Auth + Storage + Realtime | 500MB DB, 1GB storage, 50k MAU |
| **Nominatim** | Geocoding (já usado) | 1 req/s, ilimitado |
| **Open-Meteo** | Meteorologia (já usado) | Ilimitado, sem key |
| **Overpass/OSM** | Dados geográficos (campos) | Ilimitado |
| **GitHub Actions** | CI/CD + scraper | 2000 min/mês |
| **Vercel** | Hosting Next.js | 100GB bandwidth |
| **Stripe** | Pagamentos | 0€ fixo, 1.4%+0.25€ por transação |
| **Upstash Redis** | Cache/rate limiting | 10k req/dia |
| **Resend** | Emails transacionais | 3000 emails/mês |

---

## 13. MÉTRICAS

| Métrica | Ferramenta | Meta 3 meses | Meta 6 meses |
|---------|-----------|-------------|-------------|
| Utilizadores únicos/mês | Vercel Analytics | 1.000 | 10.000 |
| Eventos no mapa/semana | Supabase query | 500 | 2.000 |
| Negócios pagos | Stripe | 5 | 20 |
| Receita mensal | Stripe | 100€ | 500€ |
| Seguidores IG/TikTok | Manual | 500 | 3.000 |
| Posição Google "jogos futebol [distrito]" | Search Console | Top 10 | Top 3 |

---

## 14. ZONA PILOTO

**Braga + Porto** — maior densidade de futebol distrital, muitas festas, população jovem.

Expansão: Braga+Porto → Aveiro+Viana+Vila Real → Lisboa+Setúbal → Sul → Ilhas.

---

## 15. ARQUITETURA FUTURA

```
Scrapers (ZeroZero, Câmaras, UGC)
         │
         ▼
   Groq LLM Pipeline (classificação, extração, moderação)
         │
         ▼
   Supabase (PostgreSQL + Auth + Storage + Realtime)
         │
    ┌────┼────┐
    ▼    ▼    ▼
  PWA  Android iOS     ← Capacitor.js (1 codebase)
```
