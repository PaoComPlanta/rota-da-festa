# ROTA DA FESTA — Documento de Referência do Projeto

> **INSTRUÇÃO PARA IAs**: Lê este documento COMPLETO antes de qualquer alteração ao código.
> Após cada alteração, verifica se continua alinhada com a arquitetura, regras e fase atual.
> Não alteres ficheiros fora do scope da tarefa pedida. Não apagues código funcional.
> **Última atualização**: 23 Fev 2026

---

## 1. O QUE É ESTE PROJETO

**Rota da Festa** é uma web app portuguesa que agrega TODOS os eventos de futebol (profissional até distrital/formação), festas populares e cultura local, mostrando-os num mapa interativo. É a "bússola do fim de semana" para qualquer pessoa em Portugal.

**Proposta de valor**: Nenhuma app faz a ponte entre futebol regional e economia local. Um pai vai ver o jogo dos iniciados e descobre uma feira gastronómica a 2km. A app é e será sempre **gratuita** para o utilizador.

**Repo**: `github.com/PaoComPlanta/rota-da-festa` (branch `main`)
**Live**: `https://rotadafesta.vercel.app`
**Supabase**: `https://bjncshaitykozfdolvut.supabase.co`

---

## 2. ARQUITETURA E ESTRUTURA

```
FestasNaArea/
├── .github/workflows/
│   └── scrape.yml                    # GitHub Action — corre 3 scrapers diariamente 03:00 UTC
├── README.md                          # Documentação pública do repo
├── rota-da-festa/                     # Backend (Python)
│   ├── src/
│   │   ├── scraper_mestre.py          # ★ CORE — scraper ZeroZero + lifecycle + geocoding (~1180 linhas)
│   │   ├── scraper_festas.py          # Scraper Eventbrite (13 cidades, Playwright)
│   │   ├── scraper_camaras.py         # Scraper câmaras municipais (20 concelhos, requests+BS4)
│   │   ├── app.py                     # Flask app (não usado em produção)
│   │   ├── data_generator.py          # Gerador de dados dummy (dev)
│   │   └── seed_data.py              # Seed inicial (dev)
│   ├── requirements.txt
│   └── requirements_etl.txt
├── rota-da-festa-web/                 # Frontend (Next.js)
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # ★ Página principal — mapa + lista + filtros + alertas
│   │   │   ├── layout.tsx             # Root layout (ThemeProvider, metadata, favicon, Analytics)
│   │   │   ├── sitemap.ts             # Sitemap dinâmico (20 distritos + estáticas)
│   │   │   ├── robots.ts              # robots.txt com sitemap
│   │   │   ├── not-found.tsx          # Página 404 personalizada
│   │   │   ├── login/page.tsx         # Login (Google OAuth + Email/Password)
│   │   │   ├── submit/page.tsx        # Formulário submeter evento (7 categorias + Groq)
│   │   │   ├── negocios/page.tsx      # Landing page negócios (3 planos Stripe)
│   │   │   ├── jogos/[distrito]/page.tsx  # Páginas SEO por distrito (SSG+ISR 1h)
│   │   │   └── api/
│   │   │       ├── chat/route.ts      # Chatbot Groq
│   │   │       ├── moderate/route.ts  # Moderação Groq
│   │   │       ├── vou/route.ts       # "Vou a este evento" toggle
│   │   │       ├── reviews/route.ts   # Reviews + fotos
│   │   │       ├── negocios/route.ts  # CRUD negócios
│   │   │       ├── alertas/route.ts   # Subscribe/unsubscribe alertas por distrito
│   │   │       ├── alertas/digest/route.ts  # Digest email semanal (Resend + Vercel Cron)
│   │   │       ├── stripe/checkout/route.ts # Stripe Checkout session (3 planos)
│   │   │       └── stripe/webhook/route.ts  # Stripe webhook handler
│   │   ├── components/
│   │   │   ├── EventCard.tsx          # ★ Card evento (badges coloridos por tipo)
│   │   │   ├── EventDetailModal.tsx   # ★ Modal detalhe (meteo, equipas, maps, share, reviews)
│   │   │   ├── Map.tsx               # Mapa Leaflet com pins
│   │   │   └── ThemeProvider.tsx     # Dark/light mode
│   │   └── utils/supabase/
│   │       └── client.ts            # Supabase client (anon key)
│   ├── public/
│   │   ├── favicon.svg               # Favicon SVG (círculo verde "RF")
│   │   ├── icons/icon-192.png        # PWA icon 192px
│   │   ├── icons/icon-512.png        # PWA icon 512px
│   │   ├── manifest.json             # PWA manifest
│   │   ├── sw.js                     # Service worker
│   │   └── og-image.png              # Open Graph image
│   ├── capacitor.config.json         # Capacitor.js config (Android/iOS)
│   ├── vercel.json                   # Vercel Cron (digest semanal segundas 9h UTC)
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
| Auth | Supabase Auth (Google OAuth + Email/Password) | — |
| Scraper Futebol | Python + Playwright + BeautifulSoup | 3.10 |
| Scraper Festas | Python + Playwright (Eventbrite) | 3.10 |
| Scraper Câmaras | Python + requests + BeautifulSoup | 3.10 |
| LLM | Groq (Llama 3.3 70B) — chatbot, moderação, classificação | — |
| Geocoding | Nominatim (geopy) | — |
| Meteorologia | Open-Meteo API | — |
| Email | Resend (digest semanal) | — |
| Pagamentos | Stripe (checkout + webhook) — ainda não ativo | — |
| Analytics | @vercel/analytics | — |
| Mobile | Capacitor.js (config pronta, build pendente) | — |
| CI/CD | GitHub Actions (3 scrapers diários às 03h UTC) | — |
| Hosting | Vercel (root dir: `rota-da-festa-web`) | — |

### Variáveis de Ambiente
```
# Frontend (rota-da-festa-web/.env.local) — JÁ CONFIGURADAS
NEXT_PUBLIC_SUPABASE_URL=https://bjncshaitykozfdolvut.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhb...
GROQ_API_KEY=gsk_...                       # Chave Groq (ver .env.local)

# Vercel Env Vars — JÁ CONFIGURADAS
NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, GROQ_API_KEY

# Vercel Env Vars — POR CONFIGURAR
CRON_SECRET=<random string>              # Protege /api/alertas/digest
RESEND_API_KEY=<key da resend.com>       # Para enviar emails semanais
STRIPE_SECRET_KEY=<futuro>               # Quando ativar pagamentos
STRIPE_WEBHOOK_SECRET=<futuro>           # Quando ativar pagamentos
SUPABASE_SERVICE_KEY=<service role key>  # Para API routes server-side

# GitHub Actions Secrets — JÁ CONFIGURADOS
SUPABASE_URL, SUPABASE_SERVICE_KEY, GROQ_API_KEY
```

---

## 3. BASE DE DADOS (Supabase)

### Tabela `eventos` (principal — **id é BIGINT, não UUID**)
```sql
id              BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY
nome            TEXT NOT NULL          -- "Benfica vs Porto"
tipo            TEXT                   -- "Futebol", "Concerto", "Feira", "Cultura", etc.
categoria       TEXT                   -- "Liga Portugal", "Futebol Distrital", "Formação - Sub-15"
escalao         TEXT                   -- "Seniores", "Sub-19", "Sub-17", etc.
equipa_casa     TEXT
equipa_fora     TEXT
url_jogo        TEXT                   -- URL ZeroZero do jogo
url_equipa_casa TEXT                   -- URL ZeroZero da equipa (populado via scrape_game_details)
url_equipa_fora TEXT                   -- URL ZeroZero da equipa (populado via scrape_game_details)
url_classificacao TEXT                 -- URL ZeroZero classificação
data            TEXT NOT NULL          -- "2026-02-22"
hora            TEXT                   -- "15:00" ou "A definir"
local           TEXT                   -- "Estádio da Luz" ou "Braga (aproximado)"
latitude        FLOAT
longitude       FLOAT
preco           TEXT                   -- "~15€ (estimado)", "Grátis", "Variável"
descricao       TEXT
url_maps        TEXT                   -- Google Maps deep link
status          TEXT DEFAULT 'aprovado' -- "aprovado" | "adiado" | "pendente"
fonte           TEXT                   -- "ZeroZero", "Eventbrite", "CM Lisboa", etc.
created_at      TIMESTAMPTZ DEFAULT now()
```
**⚠️ ATENÇÃO**: `eventos.id` é **BIGINT**, não UUID. Todas as FKs devem usar BIGINT.
**Upsert key**: `(nome, data)` — mesmo jogo+data atualiza; data diferente cria novo registo.

### Tabela `favoritos`
```sql
id         UUID PRIMARY KEY
user_id    TEXT
event_id   UUID REFERENCES eventos(id)
created_at TIMESTAMPTZ DEFAULT now()
```

### Tabela `vou_eventos`
```sql
evento_id  BIGINT REFERENCES eventos(id)
user_id    TEXT NOT NULL
created_at TIMESTAMPTZ DEFAULT now()
UNIQUE(evento_id, user_id)
```

### Tabela `reviews`
```sql
id         UUID PRIMARY KEY DEFAULT gen_random_uuid()
evento_id  BIGINT REFERENCES eventos(id)
user_id    TEXT NOT NULL
texto      TEXT
rating     INT CHECK (rating >= 1 AND rating <= 5)
foto_url   TEXT
created_at TIMESTAMPTZ DEFAULT now()
```

### Tabela `negocios`
```sql
id         UUID PRIMARY KEY DEFAULT gen_random_uuid()
nome       TEXT NOT NULL
tipo       TEXT                   -- "restaurante", "cafe", "bar", "loja"
latitude   FLOAT
longitude  FLOAT
telefone   TEXT
website    TEXT
cupao      TEXT                   -- "10% desconto com Rota da Festa"
plano      TEXT DEFAULT 'basico'  -- "basico", "destaque", "premium"
ativo      BOOLEAN DEFAULT false
created_at TIMESTAMPTZ DEFAULT now()
```

### Tabela `alertas` (⚠️ PRECISA SER CRIADA pelo user)
```sql
CREATE TABLE alertas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  distrito TEXT NOT NULL,
  ativo BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(email, distrito)
);
```

### Supabase Storage
- Bucket `fotos` (público) — para fotos de reviews

---

## 4. SCRAPERS — COMO FUNCIONAM

### GitHub Actions (`scrape.yml`)
Corre **diariamente às 03:00 UTC** com 3 scrapers sequenciais:
1. `scraper_mestre.py` — Futebol (ZeroZero, Playwright)
2. `scraper_festas.py` — Festas/Cultura (Eventbrite, Playwright)
3. `scraper_camaras.py` — Câmaras municipais (requests+BS4, sem Playwright)

**Timeout**: 90 minutos. **Deps**: `supabase requests beautifulsoup4 geopy groq playwright python-dotenv`

### scraper_mestre.py (Futebol)
**Pipeline**:
```
1. limpar_eventos_concluidos()    — Só às quintas: apaga eventos com data < ontem
2. scrape_zerozero()              — Fase 1 (agenda) + Fase 2 (AFs/competições)
3. scrape_game_details()          — Para cada jogo com url_jogo: extrai URLs equipas/classificação
4. verificar_adiamentos()         — Compara DB vs scrape fresco → marca "adiado"
5. Upsert no Supabase            — on_conflict="nome,data"
```

**Fase 1**: Agenda `zerozero.pt/agenda.php?date=YYYY-MM-DD` (hoje + 6 dias)
**Fase 2**: 25 URLs fixas (`PT_COMPETITION_URLS`): 20 AFs + Liga 3 + Juniores + Feminina
**Detail scraping**: `scrape_game_details(page, game_url)` abre cada página de jogo e extrai:
  - URLs equipas via `a[href*='/equipa/']`
  - URL classificação via `a[href*='/edition/']` ou `a[href*='/edicao/']`
  - Delay 0.5s entre jogos, progress log cada 20

**Geocoding (6 fallbacks)**: Cache estadios → Nominatim variações → Extrair localidade do nome → Centróide distrito → None

### scraper_festas.py (Eventbrite)
- 13 cidades portuguesas
- Playwright (renderiza JS)
- Classificação via Groq LLM
- Geocoding via Nominatim

### scraper_camaras.py (Câmaras Municipais) — NOVO
- 20 concelhos (todas as capitais de distrito)
- requests + BeautifulSoup (sem Playwright — leve e rápido)
- Scraper genérico que procura padrões comuns de agendas municipais
- Extração de datas em português (regex: dd/mm/yyyy, "dd de mês de yyyy")
- Classificação via Groq LLM
- Deduplicação por hash(nome+data+local)

---

## 5. FRONTEND — COMPORTAMENTO ATUAL

### page.tsx (página principal, ~640 linhas)
- Carrega eventos do Supabase com `status IN ('aprovado', 'adiado')`
- `pendente` não é mostrado ao utilizador
- Adiados aparecem no fim da lista com opacidade reduzida
- **Filtros**: pesquisa texto, categoria, escalão, distrito (dropdown 20 distritos), data (Hoje/FDS/Semana/Todos)
- **Mapa Leaflet** com pins clicáveis (cores por tipo)
- **PWA install prompt** (deteta `beforeinstallprompt`)
- **Chatbot** flutuante "Pergunte à Rota" (Groq)
- **Footer**: formulário alertas semanais + links SEO distritos + link /negocios
- **GPS**: botão geolocalização + seletor cidade

### EventCard.tsx (~125 linhas)
- Badges coloridos por tipo: 7 categorias com cores e ícones distintos
- Badges: 🔴 "HOJE", "Amanhã", ⚠️ "ADIADO"
- Adiados: borda laranja, opacidade 70%

### EventDetailModal.tsx (~820 linhas)
- Meteorologia via Open-Meteo API
- Links ZeroZero: equipa (url_equipa → url_jogo fallback → pesquisa) e classificação
- WhatsApp + Twitter/X + Copiar link (share)
- "Vou a este evento" com contador (Supabase sync)
- Reviews e fotos
- "Comer e beber perto" (negócios raio 3km)
- Banner laranja para eventos adiados
- Botão Google Maps
- **Dark mode**: todas as secções com contraste adequado (bg-*/900/30-40, borders visíveis)

### Páginas adicionais
- `/login` — Google OAuth + Email/Password (Supabase Auth)
- `/submit` — Submeter evento (7 categorias, moderação Groq)
- `/negocios` — Landing page negócios locais (3 planos pricing, Stripe checkout)
- `/jogos/[distrito]` — 20 páginas SEO estáticas (SSG + ISR 1h)
- `/404` — Página 404 personalizada

---

## 6. REGRAS E RESTRIÇÕES

### Para qualquer IA que altere o código:
1. **Não remover** CACHE_ESTADIOS, DISTRICT_CENTROIDS, PT_COMPETITION_URLS — são dados essenciais
2. **Não simplificar** o geocoding removendo fallbacks — equipas desconhecidas precisam deles
3. **Upsert key é `(nome, data)`** — não alterar sem migração
4. **`eventos.id` é BIGINT** — todas as FKs devem usar BIGINT, não UUID
5. **url_equipa_casa/fora/classificacao podem estar vazios** — o frontend tem fallbacks (url_jogo → pesquisa)
6. **O scraper corre em GitHub Actions** (Ubuntu, Python 3.10, Playwright Chromium) — testar compatibilidade
7. **Nominatim tem rate limit de 1 req/s** — manter `time.sleep(1.1)` entre chamadas
8. **ZeroZero bloqueia requests diretos** — usar sempre Playwright com user-agent de browser
9. **A app é grátis para o utilizador** — nunca implementar paywall para funcionalidades core
10. **Scraper timeout**: 90 minutos no GitHub Actions — otimizar se aproximar deste limite
11. **Língua**: Código em inglês (nomes de funções), strings e UI em **português de Portugal**
12. **Vercel root directory**: `rota-da-festa-web` (não a raiz do repo)
13. **Dark mode contrast**: usar `dark:bg-*/900/30-40` com `dark:border-*/700` (nunca `dark:bg-*/950/20`)

### Convenções de código
- **Python**: snake_case, docstrings em português, prints com emojis para logging
- **TypeScript/React**: camelCase, componentes funcionais, Tailwind para styling
- **Commits**: incluir `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>`

---

## 7. PROBLEMAS CONHECIDOS (Fev 2026)

| # | Problema | Estado | Notas |
|---|---------|--------|-------|
| 1 | Fase 2 retorna 0 jogos distritais | 🔧 Debug | Edições encontradas mas `/proximos-jogos` pode não ter jogos |
| 2 | ~77 eventos no Supabase (devia ter 200+) | 🔧 Depende de #1 | Fase 1 funciona, Fase 2 precisa funcionar |
| 3 | Jogos não-distritais marcados como "Futebol Distrital" | ✅ Corrigido | Default mudado para "Futebol" genérico |
| 4 | url_equipa_casa/fora populados | ✅ Corrigido | `scrape_game_details()` agora extrai URLs reais das páginas de jogo |
| 5 | GROQ_API_KEY | ✅ Em uso | Chatbot, moderação, classificação câmaras/festas |
| 6 | Tabela `alertas` não criada | ⚠️ User action | User precisa criar via SQL Editor (ver secção 3) |
| 7 | Scraper câmaras genérico | ⚠️ Pode falhar | Sites mudam estrutura HTML; monitorizar e ajustar seletores |
| 8 | Stripe não configurado | ⏸️ Adiado | Código pronto, falta criar conta + env vars quando decidir ativar |

---

## 8. ROADMAP DE FASES

### FASE 1 — Solidificar o Futebol ✅ CONCLUÍDA
**Meta**: Melhor experiência map-first para futebol português em TODOS os escalões.

- [x] Scraper ZeroZero completo (Fase 1 agenda + Fase 2 AFs/competições + detail scraping)
- [x] Filtros: escalão, distrito (20), categoria, data (Hoje/FDS/Semana/Todos), texto
- [x] "Perto de mim" — GPS + seletor cidade (20 distritos)
- [x] PWA: manifest.json + service worker + install prompt
- [x] Cache de estádios persistente (auto-commit pela Action)
- [x] Páginas SEO: `/jogos/[distrito]` (SSG + ISR 1h)
- [x] Login Google OAuth + Email/Password
- [x] Open Graph + Twitter Card meta + metadataBase
- [x] Deploy Vercel + Vercel Analytics
- [x] Contador de eventos no header
- [x] "Vou a este evento" com toggle + contador (Supabase sync)
- [x] Reviews + fotos (Supabase Storage)
- [x] Badges coloridos por tipo
- [x] Botões partilha (WhatsApp, Twitter/X, Copiar link)
- [x] Página 404 personalizada
- [x] Footer SEO + formulário alertas
- [x] sitemap.xml + robots.txt dinâmicos
- [x] Favicon personalizado (SVG verde "RF" + ICO + PWA icons)

### FASE 2 — Festas Populares e Cultura ✅ CONCLUÍDA
**Meta**: Ser a "bússola do fim de semana" completa (futebol + festas + cultura).

- [x] Scraper Eventbrite Portugal (13 cidades, Playwright)
- [x] Scraper câmaras municipais (20 concelhos, requests+BS4)
- [x] Formulário "Submeter Evento" (/submit, 7 categorias)
- [x] Moderação automática via Groq (classificar, detetar spam)
- [x] Novas categorias frontend + submit (⚽🎪🎵🍖🎭🏃🔥)
- [ ] Parser de PDFs com Groq LLM (programas de festas → eventos estruturados)
- [ ] Novas colunas DB: `subcategoria`, `verificado`, `imagem_url`, `tags[]`

### FASE 3 — Comunidade e Viralidade ✅ CONCLUÍDA
**Meta**: Crescimento orgânico.

- [x] Login Google + Email/Password (Supabase Auth)
- [x] Open Graph tags + social previews
- [x] "Vou a este evento" — contador social (Supabase sync + localStorage fallback)
- [x] Reviews e fotos de eventos (Supabase Storage)
- [x] Chatbot Groq: "O que há perto de Guimarães este sábado?"
- [x] Email alertas semanais por distrito (Resend + Vercel Cron)
- [ ] Push notifications via web push API
- [ ] Referral system ("Partilha com amigos")

### FASE 4 — Monetização 🔧 EM PROGRESSO
- [x] Pins patrocinados no mapa (gold icons, tabela negocios, cupões)
- [x] "Comer e beber perto" no modal (raio 3km, API route)
- [x] Landing page `/negocios` (3 planos, FAQ, formulário)
- [x] Stripe Checkout API (código pronto, falta ativar conta)
- [x] Stripe Webhook API (código pronto)
- [ ] Dashboard de negócios (quando houver clientes)
- [ ] Stripe: criar conta + configurar env vars + webhook endpoint

### FASE 5 — Apps Nativas ⏳ PENDENTE
- [x] Capacitor.js config (`capacitor.config.json` — server URL + splash)
- [ ] `npx cap add android` → Android Studio → APK
- [ ] `npx cap add ios` → Xcode → IPA
- [ ] Google Play (25€ uma vez) + Apple Developer (99€/ano)
- [ ] Funcionalidades nativas: geofencing, widget ecrã, modo offline, deep links

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
Scrapers (ZeroZero, Eventbrite, Câmaras, UGC)
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
         │
    ┌────┼────┐
    ▼    ▼    ▼
  Resend  Stripe  Vercel Cron
  (emails) (pagamentos) (digest)
```

---

## 16. SESSÃO DE TRABALHO — 23 FEV 2026

### Commits desta sessão (cronológico):
1. `384f6f0` — sitemap.xml, robots.txt, date filter, Vercel Analytics, metadataBase
2. `97e9d23` — WhatsApp + Twitter share buttons no EventDetailModal
3. `e50ef2b` — Badges coloridos por tipo no EventCard (7 categorias)
4. `dbdc469` — PWA install prompt, página 404, footer SEO com links distritos
5. `10df744` — Visual contrast polish (dark/light) + ZeroZero links fix + scraper detail extraction
6. `5cd7b19` — Email alerts API, Stripe checkout API, landing page /negocios
7. `5978a03` — Scraper câmaras municipais, Capacitor config, Vercel cron
8. `<último>` — Favicon personalizado (SVG + ICO + PWA icons)

### Funcionalidades implementadas:
- **SEO**: sitemap dinâmico, robots.txt, Vercel Analytics, metadataBase, JSON-LD
- **UX**: date filter, share buttons (WhatsApp/Twitter/Copy), badges coloridos, PWA install prompt, 404, footer SEO
- **Visual**: dark/light mode contrast polish completo em TODOS os componentes
- **ZeroZero links**: scraper agora extrai URLs reais de equipas/classificação via `scrape_game_details()`
- **Alertas email**: API subscribe/unsubscribe + digest semanal via Resend + Vercel Cron
- **Stripe**: Checkout session + webhook (código pronto, env vars pendentes)
- **Landing page `/negocios`**: 3 planos pricing, FAQ, formulário + checkout
- **Scraper câmaras**: 20 concelhos, requests+BS4, classificação Groq
- **Capacitor**: config pronta para wrapping Android/iOS
- **Favicon**: SVG (círculo verde "RF") + ICO multi-tamanho + PWA icons regenerados

### ⚠️ AÇÕES PENDENTES DO USER:

1. **Criar tabela `alertas` no Supabase SQL Editor**:
```sql
CREATE TABLE alertas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  distrito TEXT NOT NULL,
  ativo BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(email, distrito)
);
```

2. **CRON_SECRET no Vercel** → Settings → Environment Variables:
   - Nome: `CRON_SECRET`
   - Valor: qualquer string aleatória (ex: `rota-digest-secret-2026`)
   - O Vercel Cron usa isto automaticamente quando chama `/api/alertas/digest`

3. **RESEND_API_KEY no Vercel** (quando quiser ativar emails):
   - Criar conta em resend.com → copiar API key → Vercel env vars

4. **Stripe** (adiado — quando quiser ativar pagamentos):
   - Criar conta Stripe → `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` no Vercel
   - Webhook endpoint: `https://rotadafesta.vercel.app/api/stripe/webhook`

5. **Capacitor** (quando quiser gerar APK):
   - `cd rota-da-festa-web && npx cap add android`
   - Precisa de Android Studio instalado

### O que falta implementar (próximas sessões):
- [ ] Parser de PDFs com Groq LLM (programas de festas)
- [ ] Novas colunas DB: `subcategoria`, `verificado`, `imagem_url`, `tags[]`
- [ ] Push notifications via web push API
- [ ] Dashboard de negócios (quando houver clientes)
- [ ] Build Capacitor Android/iOS
- [ ] Performance audit (Lighthouse)
- [ ] i18n (inglês) — quando crescer internacionalmente
- [ ] Rate limiting (Upstash Redis) nos API routes
