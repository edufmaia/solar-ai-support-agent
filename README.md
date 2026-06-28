# Solar AI Support Agent

[![CI](https://github.com/edufmaia/solar-ai-support-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/edufmaia/solar-ai-support-agent/actions/workflows/ci.yml)

Agente de IA para atendimento inicial, qualificação de leads e pré-análise geoespacial para empresas de energia solar.

## Índice

- [Quickstart](#quickstart) · [Telas](#telas) · [Status atual](#status-atual)
- [Arquitetura](#arquitetura) · [Stack](#stack) · [Estrutura principal](#estrutura-principal)
- [Configuração de ambiente](#configuração-de-ambiente) · [Como subir o projeto](#como-subir-o-projeto) · [Endpoints](#endpoints)
- [Interface web](#interface-web): [chat do cliente](#chat-do-cliente--httplocalhost8010ui) · [painel admin](#painel-interno-admin--httplocalhost8010uiadmin) · [widget embutível](#widget-embutível--uma-linha-de-script)
- [Instruções e base de conhecimento](#instruções-e-base-de-conhecimento)
- Validação: [API](#como-validar-a-api) · [chat mock](#como-validar-o-chat-em-modo-mock) · [OpenAI](#como-validar-o-chat-em-modo-openai) · [Claude](#como-validar-o-chat-em-modo-claude) · [leads/conversas](#como-validar-leads-e-conversas) · [eventos](#como-validar-eventos-do-agente) · [custo/tokens](#como-validar-o-custo-estimado-da-openai) · [métricas](#como-validar-as-métricas-do-agente) · [Chatwoot](#como-validar-o-webhook-do-chatwoot)
- [Geocoding & solar](#geocoding) · [Testes & CI](#testes) · [Decisões técnicas](#decisões-técnicas) · [Roadmap](#roadmap)

## Quickstart

Suba tudo com **um comando** (precisa apenas de Docker):

```bash
git clone https://github.com/edufmaia/solar-ai-support-agent.git
cd solar-ai-support-agent
docker compose up -d --build
```

Pronto — o schema do banco é aplicado automaticamente (service `migrate`) e o
backend sobe com healthcheck. Acesse:

- **Chat do cliente:** http://localhost:8010/ui/
- **Painel interno:** http://localhost:8010/ui/admin/ (requer `ADMIN_PASSWORD`, veja abaixo)
- **API (Swagger):** http://localhost:8010/docs

**Opcional — habilitar painel admin e/ou LLM real:** copie o template de ambiente
e edite antes de subir (sem isso, a stack roda em modo `mock` e o painel admin fica
desabilitado):

```bash
cp .env.example .env
# defina ADMIN_PASSWORD (habilita /ui/admin/) e, se quiser, as chaves de LLM
docker compose up -d
```

> O `docker-compose.yml` já fixa o project name (`solar-ai-support-agent`), então
> não é preciso passar `-p`. Para parar: `docker compose down` (use `down -v` para
> apagar os dados do banco).

### Telas

| Chat do cliente | Painel interno | Widget embutido |
|---|---|---|
| ![Chat do cliente](docs/images/chat.png) | ![Painel interno](docs/images/admin.png) | ![Widget embutido](docs/images/widget.png) |

> As imagens acima são geradas localmente — veja [`docs/images/README.md`](docs/images/README.md)
> para o que capturar e como.

## Status atual

O projeto já possui:

- API FastAPI mínima com `GET /health`
- configuração Docker para backend, PostgreSQL e Redis
- schema inicial em `database/schema.sql`
- camada de conexão com PostgreSQL
- endpoint `GET /health/db`
- utilitários para aplicar o schema no banco
- repositories básicos para `leads`, `conversations` e `messages`
- endpoint `POST /chat` com orquestrador de conversa
- repository de `agent_events` com rastreabilidade básica
- serviço mockado de extração de lead
- serviço mockado de scoring de lead
- camada abstrata de LLM com `BaseLLMProvider`
- `MockLLMProvider`
- `OpenAIProvider` usando a Responses API
- `ClaudeProvider` usando a Anthropic Messages API
- factory simples para escolher provider por variável de ambiente
- tools do agente (`save_lead`, `update_lead`, `classify_lead`, `request_human_handoff`)
- extração estruturada de lead e scoring enriquecido por análise geoespacial/solar
- geocoding (mock/Nominatim) e potencial solar (mock) com handoff por `technical_review`
- registro de custos do agente: evento `agent_turn_completed` por turno e `MessageRepository.aggregate_usage` (tokens/custo, com breakdown por modelo)
- métricas agregadas (leads, conversas, uso/custo, eventos) — públicas via `/admin/metrics` apenas com login
- sessão de conversa efêmera em Redis (cache com TTL; Postgres continua a fonte da verdade) com recuperação por turno e degradação graciosa
- webhook do Chatwoot (`POST /webhooks/chatwoot`): recebe mensagens `incoming`, processa pelo agente e responde via API do Chatwoot
- chat do cliente em `/ui` (white-label) e **painel interno com login** em `/ui/admin/` (dashboard + conversas + detalhe, só-leitura); `/metrics` e `/conversations/{id}` ficam protegidos por auth admin
- **instruções customizáveis + base de conhecimento** no painel admin: a empresa reescreve o prompt do agente e anexa PDF/DOCX/TXT/MD (ou cola texto) que viram referência via full-text search (RAG) nas respostas dos LLMs reais

## Stack

- Python 3.12
- FastAPI
- PostgreSQL
- Redis
- SQLAlchemy
- OpenAI Python SDK
- Anthropic Python SDK
- Docker Compose

## Estrutura principal

```text
backend/
  app/
    agents/
    api/
    config/
    llm/
    repositories/
    schemas/
    services/
    tools/
  tests/

database/
  migrations/
  schema.sql
  apply_schema.ps1
  apply_schema.sh

docs/
  specs/
    001-solar-ai-support-agent/
```

## Arquitetura

```mermaid
flowchart TD
    C1["POST /chat"] --> API
    C2["POST /webhooks/chatwoot"] --> API
    C3["GET /metrics"] --> API
    C4["GET /health[/db]"] --> API
    API["api/ (FastAPI)"] --> ORCH["MockAgentOrchestrator (agents/)"]
    ORCH --> SVC["services/ — extração · scoring · métricas"]
    ORCH --> TOOLS["tools/ — save · update · classify · handoff"]
    ORCH --> LLM["llm/ — mock · openai · claude"]
    ORCH --> GEO["geocoding/ · solar/ — mock · nominatim"]
    ORCH --> INT["integrations/chatwoot/"]
    ORCH --> REPO["repositories/ (SQL)"]
    ORCH --> SESS["session/ (Redis)"]
    REPO --> PG[("PostgreSQL — fonte da verdade")]
    SESS --> RD[("Redis — sessão + mapa Chatwoot, TTL")]
```

`MockAgentOrchestrator.handle_chat()` é o coração do sistema. Para cada mensagem, em ordem: recupera/cria a conversa → recupera a sessão efêmera no Redis → persiste a mensagem do usuário → extrai dados do lead → cria/atualiza e associa o lead → calcula o score base → (com consentimento + endereço) faz geocoding + potencial solar → reavalia o score com os dados geoespaciais → decide handoff humano (usuário/`hot`/`technical_review`) → monta o contexto e chama o LLM → avança o estado da conversa → persiste a resposta → emite `agent_turn_completed` (custo/tokens consolidados) → salva o snapshot da sessão no Redis. Cada passo relevante emite um `agent_event` para rastreabilidade.

O mesmo orquestrador atende os dois canais de entrada (`POST /chat` e o webhook do Chatwoot). O PostgreSQL é a fonte da verdade; o Redis é um cache efêmero (sessão da conversa + mapeamento Chatwoot→conversa interna) com degradação graciosa.

### Componentes

| Camada | Pasta | Responsabilidade |
|---|---|---|
| API | `app/api/` | Rotas FastAPI (`chat`, `chatwoot`, `metrics`, `health`) |
| Orquestrador | `app/agents/` | Fluxo de conversa, eventos, sessão |
| Serviços | `app/services/` | Extração de lead, scoring, métricas, webhook Chatwoot |
| Tools | `app/tools/` | `save_lead`, `update_lead`, `classify_lead`, `request_human_handoff` |
| LLM | `app/llm/` | `BaseLLMProvider` + mock/OpenAI/Claude (factory por env) |
| Geoespacial | `app/geocoding/`, `app/solar/` | Geocoding (mock/Nominatim) e potencial solar (mock) |
| Integrações | `app/integrations/chatwoot/` | Cliente Chatwoot + mapa de conversa em Redis |
| Persistência | `app/repositories/` | SQL manual via SQLAlchemy `text()` |
| Sessão | `app/session/` | Cache de sessão da conversa em Redis |

## Configuração de ambiente

Use `.env.example` como referência.

### Banco no Docker

```env
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=solar_ai_support
DATABASE_USER=solar
DATABASE_PASSWORD=solar_password
DATABASE_URL=postgresql+psycopg://solar:solar_password@postgres:5432/solar_ai_support
```

### Seleção de provider de LLM

```env
LLM_PROVIDER=mock
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_INPUT_PRICE_PER_1M_TOKENS=0.15
OPENAI_OUTPUT_PRICE_PER_1M_TOKENS=0.60
```

Observações:

- `LLM_PROVIDER` aceita atualmente `mock`, `openai`, `claude` e `hybrid`.
- Se `LLM_PROVIDER=openai` e `OPENAI_API_KEY` não estiver definida, `POST /chat` retorna erro claro de configuração.
- O fallback padrão continua sendo `mock`.

**Modo `hybrid` (economia de tokens):** roteia cada turno entre o mock (grátis) e um provider real (`HYBRID_REAL_PROVIDER`, padrão `openai`). Turnos scriptados — saudação, coleta de cidade/conta/endereço e o resumo da pré-análise solar — são respondidos pelo mock a custo zero; o LLM real só é chamado quando os dados-core estão completos e há texto livre para interpretar. O provider real é construído sob demanda (turnos mock funcionam mesmo sem a chave) e cada turno registra o provider/custo reais, então o painel de custo soma só os turnos pagos.

### Extração de lead via LLM

A cada mensagem o orquestrador extrai os dados do lead (nome, e-mail, telefone, cidade, endereço, conta, tipo de imóvel, intenção, consentimento) com uma chamada estruturada a um modelo **barato**, usando o **histórico completo** da conversa como contexto. É isso que permite capturar respostas em linha solta (ex.: o cliente responde só `Eduardo Freire Maia` ou `contato@exemplo.com` a uma pergunta) e parar de re-perguntar dados já informados.

```env
LEAD_EXTRACTION_PROVIDER=auto
LEAD_EXTRACTION_MODEL=
LEAD_EXTRACTION_MAX_TOKENS=1024
```

- `LEAD_EXTRACTION_PROVIDER`: `auto` | `openai` | `claude` | `regex`.
  - `auto` (padrão) segue o provider real da resposta — `HYBRID_REAL_PROVIDER` quando `LLM_PROVIDER=hybrid`, senão o próprio `LLM_PROVIDER`. Se isso resolver para `mock`, a extração por LLM fica desligada (usa o regex).
  - `openai` | `claude` forçam o provider, **independente** do provider que gera a resposta (dá para extrair com OpenAI e responder com Claude, ou o inverso, para baratear).
  - `regex` desliga a extração por LLM e usa só o extrator deterministico (útil para testes e operação offline).
- `LEAD_EXTRACTION_MODEL`: vazio usa o default barato por provider (`gpt-4o-mini` para OpenAI, `claude-haiku-4-5` para Claude); defina para fixar outro modelo.
- `LEAD_EXTRACTION_MAX_TOKENS`: teto de tokens da chamada de extração (usado pelo provider Claude).
- **Resiliência:** se a chamada falhar, expirar ou retornar JSON inválido, o sistema cai automaticamente no extrator regex e registra o evento `lead_extraction_llm_failed` — o turno nunca quebra por causa da extração. Reaproveita `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`; sem a chave do provider escolhido, também cai no regex.

### Sessão em Redis

```env
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0
SESSION_TTL_SECONDS=3600
```

O Redis guarda um snapshot efêmero da conversa (`current_state`, `lead_id`, score, `turn_count`) por `SESSION_TTL_SECONDS`, recuperado no início de cada turno. É um cache: se o Redis estiver indisponível, o `POST /chat` continua funcionando (o Postgres é a fonte da verdade) e o evento `session_store_unavailable` é registrado.

### Integração Chatwoot

```env
CHATWOOT_BASE_URL=https://app.chatwoot.com
CHATWOOT_API_ACCESS_TOKEN=seu_token
```

Sem essas variáveis, o webhook ainda processa a mensagem recebida, mas não envia a resposta (`reply_sent: false`).

## Como subir o projeto

Na raiz do repositório:

```bash
docker compose -p solar-ai-support-agent up --build -d
```

Portas expostas no host:

- API: `localhost:8010`
- PostgreSQL: `localhost:5434`
- Redis: `localhost:6381`

## Como aplicar o schema do banco

### PowerShell (Windows)

```powershell
.\database\apply_schema.ps1
```

### Bash / Linux / macOS / WSL

```bash
chmod +x database/apply_schema.sh
./database/apply_schema.sh
```

Os scripts usam:

- project name: `solar-ai-support-agent`
- service name: `postgres`
- database: `solar_ai_support`
- user: `solar`

## Como validar a API

### Health check básico

```bash
curl http://localhost:8010/health
```

Resultado esperado:

```json
{"status":"ok"}
```

### Health check do banco

```bash
curl http://localhost:8010/health/db
```

Resultado esperado:

```json
{"status":"ok","database":"connected"}
```

## Como validar o chat em modo mock

Defina no `.env`:

```env
LLM_PROVIDER=mock
```

Depois chame:

```bash
curl -X POST http://localhost:8010/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Olá, moro em Mossoró, minha conta vem R$ 650 e tenho interesse em energia solar para minha casa\",\"conversation_id\":null,\"channel\":\"api\"}"
```

Resultado esperado:

```json
{
  "conversation_id": "uuid-da-conversa",
  "response": "Seu perfil já mostra um bom potencial preliminar para energia solar. Se quiser, você pode me informar o endereço do imóvel para avançarmos para uma pré-análise geoespacial preliminar.",
  "mode": "mock"
}
```

## Como validar o chat em modo OpenAI

Defina no `.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sua_chave
OPENAI_MODEL=gpt-4o-mini
```

Rebuild:

```bash
docker compose -p solar-ai-support-agent up --build -d
```

Depois chame:

```bash
curl -X POST http://localhost:8010/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Olá, moro em Mossoró, minha conta vem R$ 650 e tenho interesse em energia solar para minha casa\",\"conversation_id\":null,\"channel\":\"api\"}"
```

Resultado esperado:

- resposta gerada pela OpenAI
- `mode = "openai"`
- mensagem do assistant salva com `model_provider = openai`
- mensagem do assistant salva com `model_name =` o modelo configurado
- evento `llm_openai_response_generated` registrado

## Como validar leads e conversas

Após chamar `POST /chat`, consulte:

```bash
docker compose -p solar-ai-support-agent exec postgres \
  psql -U solar -d solar_ai_support \
  -c "SELECT name, city, average_energy_bill, property_type, intent, lead_score, lead_temperature, source_channel FROM leads ORDER BY created_at DESC LIMIT 5;"
```

```bash
docker compose -p solar-ai-support-agent exec postgres \
  psql -U solar -d solar_ai_support \
  -c "SELECT id, lead_id, status, current_state FROM conversations ORDER BY started_at DESC LIMIT 5;"
```

## Como verificar mensagens salvas no banco

Após chamar `POST /chat`:

```bash
docker compose -p solar-ai-support-agent exec postgres \
  psql -U solar -d solar_ai_support \
  -c "SELECT role, content, model_provider, model_name, input_tokens, output_tokens, estimated_cost FROM messages ORDER BY created_at DESC LIMIT 5;"
```

Em modo mock, o assistant deve ser salvo com:

- `model_provider = mock`
- `model_name = mock-agent-v1`

Em modo OpenAI, o assistant deve ser salvo com:

- `model_provider = openai`
- `model_name =` o modelo realmente usado

## Como validar eventos do agente

Após chamar `POST /chat`, consulte os eventos:

```bash
docker compose -p solar-ai-support-agent exec postgres \
  psql -U solar -d solar_ai_support \
  -c "SELECT event_type, event_source, payload, created_at FROM agent_events ORDER BY created_at DESC LIMIT 10;"
```

Eventos esperados em modo mock:

- `conversation_started`
- `user_message_received`
- `lead_extraction_llm_failed` (apenas em degradação, se a extração via LLM falhar/retornar JSON inválido e cair no extrator regex)
- `lead_data_extracted`
- `lead_created` ou `lead_updated`
- `lead_scored`
- `geospatial_analysis_completed` (quando o usuário autoriza a análise e há endereço)
- `solar_potential_completed` (após o geocoding, quando há coordenadas)
- `lead_score_updated` (quando a análise geoespacial/solar altera o score)
- `human_handoff_requested` (usuário pede humano, lead `hot`, ou `technical_review` da análise solar)
- `session_recovered` (apenas quando a conversa é reusada e há sessão em cache no Redis)
- `llm_mock_response_generated`
- `assistant_mock_response_created`
- `agent_turn_completed` (resumo do turno: tokens, modelo, custo estimado e nº de eventos)
- `session_store_unavailable` (apenas em degradação, se o Redis estiver fora)

Eventos esperados em modo OpenAI:

- `conversation_started`
- `user_message_received`
- `lead_extraction_llm_failed` (apenas em degradação, se a extração via LLM falhar/retornar JSON inválido e cair no extrator regex)
- `lead_data_extracted`
- `lead_created` ou `lead_updated`
- `lead_scored`
- `geospatial_analysis_completed` (quando o usuário autoriza a análise e há endereço)
- `solar_potential_completed` (após o geocoding, quando há coordenadas)
- `lead_score_updated` (quando a análise geoespacial/solar altera o score)
- `human_handoff_requested` (usuário pede humano, lead `hot`, ou `technical_review` da análise solar)
- `session_recovered` (apenas quando a conversa é reusada e há sessão em cache no Redis)
- `llm_openai_response_generated`
- `assistant_mock_response_created`
- `agent_turn_completed` (resumo do turno: tokens, modelo, custo estimado e nº de eventos)
- `session_store_unavailable` (apenas em degradação, se o Redis estiver fora)

Limitação atual:

- `conversation_not_found` não é persistido em `agent_events`, porque a tabela exige `conversation_id` válido com foreign key para `conversations(id)`.

## Como validar o custo estimado da OpenAI

O `OpenAIProvider` calcula `estimated_cost` com base em:

- `input_tokens`
- `output_tokens`
- `OPENAI_INPUT_PRICE_PER_1M_TOKENS`
- `OPENAI_OUTPUT_PRICE_PER_1M_TOKENS`

Se a API não retornar usage, o projeto salva:

- `input_tokens = 0`
- `output_tokens = 0`
- `estimated_cost = 0`

## Como validar as métricas do agente

O endpoint `GET /metrics` retorna dados agregados de leads, conversas, uso/custo de LLM e eventos do agente (tudo calculado on-read, sem materialização):

```bash
curl http://localhost:8010/metrics
```

Resultado esperado (exemplo):

```json
{
  "leads": {"total": 14, "by_temperature": {"hot": 10, "warm": 2, "cold": 1, "unscored": 1}},
  "conversations": {"total": 19, "assigned_to_human": 7},
  "usage": {
    "total_messages": 48,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_estimated_cost": "0.000000",
    "by_model": [
      {"model_provider": "mock", "model_name": "mock-agent-v1", "message_count": 24, "input_tokens": 0, "output_tokens": 0, "estimated_cost": "0.000000"}
    ]
  },
  "events": [
    {"event_type": "assistant_mock_response_created", "count": 22},
    {"event_type": "agent_turn_completed", "count": 17}
  ]
}
```

- `usage` reusa o agregador de uso (`MessageRepository.aggregate_usage`) introduzido no T019.
- `events` conta os `agent_events` por tipo (mais frequentes primeiro).

## Como validar o webhook do Chatwoot

O endpoint `POST /webhooks/chatwoot` recebe eventos do Chatwoot. Apenas `message_created` com `message_type: incoming` é processado (mensagens `outgoing` são ignoradas para evitar loop). A continuidade da conversa é mantida em Redis (mapeando a conversa do Chatwoot para a conversa interna).

```bash
curl -X POST http://localhost:8010/webhooks/chatwoot \
  -H "Content-Type: application/json" \
  -d "{\"event\":\"message_created\",\"message_type\":\"incoming\",\"content\":\"Olá, moro em Natal e tenho interesse em energia solar\",\"conversation\":{\"id\":42},\"account\":{\"id\":1}}"
```

Resultado esperado (sem `CHATWOOT_*` configurado):

```json
{"status": "handled", "conversation_id": "uuid-da-conversa", "reply_sent": false, "reply_error": "CHATWOOT_BASE_URL and CHATWOOT_API_ACCESS_TOKEN must be set"}
```

Com as variáveis configuradas, `reply_sent` é `true` e a resposta do agente é enviada de volta ao Chatwoot como mensagem `outgoing`.

## Como validar se o schema foi aplicado

```bash
docker compose -p solar-ai-support-agent exec postgres psql -U solar -d solar_ai_support -c "\dt"
```

Resultado esperado: tabelas como:

- `leads`
- `conversations`
- `messages`
- `agent_events`
- `geospatial_analysis`
- `model_costs`
- `knowledge_documents`

## Como validar o chat em modo Claude

Defina no `.env`:

```env
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sua_chave
CLAUDE_MODEL=claude-opus-4-8
```

Rebuild:

```bash
docker compose -p solar-ai-support-agent up --build -d
```

Resultado esperado:

- resposta gerada pela Anthropic
- `mode = "claude"`
- mensagem do assistant salva com `model_provider = claude`
- mensagem do assistant salva com `model_name =` o modelo configurado
- evento `llm_claude_response_generated` registrado

## Geocoding

`GEOCODING_PROVIDER` aceita `mock` (default, determinístico) e `nominatim` (OpenStreetMap, gratuito, sem chave — exige `User-Agent`, configurável via `NOMINATIM_USER_AGENT`). A análise geoespacial é disparada quando o usuário autoriza explicitamente ("autorizo", "pode analisar") e o lead já tem endereço; o resultado é gravado em `geospatial_analysis` e registrado no evento `geospatial_analysis_completed`.

Após o geocoding, quando há coordenadas, o agente estima o potencial solar preliminar (faixa de painéis, kWp, nível de confiança e necessidade de revisão técnica) com base na conta de energia do lead — sem conta, cai para uma estimativa determinística por coordenadas. `SOLAR_PROVIDER` aceita `mock` (default); o resultado é gravado nas colunas solares de `geospatial_analysis` e registrado no evento `solar_potential_completed`. É uma pré-análise e não substitui vistoria técnica.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Liveness — `{"status":"ok"}` |
| `GET` | `/health/db` | Checa conexão com o PostgreSQL |
| `POST` | `/chat` | Conversa com o agente (cria/recupera conversa, responde) |
| `GET` | `/conversations/{id}` | Detalhe consolidado (conversa + lead + análise solar + eventos) — **exige login admin** |
| `POST` | `/webhooks/chatwoot` | Recebe mensagens do Chatwoot e responde via API |
| `GET` | `/metrics` | Métricas agregadas (leads, conversas, uso/custo, eventos) — **exige login admin** |
| `POST` | `/admin/login` | Login do painel (senha única → token de sessão Bearer) |
| `POST` | `/admin/logout` | Encerra a sessão admin (revoga o token) |
| `GET` | `/admin/metrics` | Métricas para o painel (reusa `MetricsService`) — exige login |
| `GET` | `/admin/conversations` | Lista de conversas com join do lead (`?limit&offset`) — exige login |
| `GET` | `/admin/conversations/{id}` | Detalhe consolidado para o painel — exige login |
| `GET` `PUT` | `/admin/agent-settings` | Lê / salva as instruções do agente + flag de RAG — exige login |
| `POST` | `/admin/agent-settings/reset` | Restaura as instruções padrão — exige login |
| `GET` `POST` | `/admin/knowledge` | Lista / adiciona documentos (arquivo ou texto) — exige login |
| `PATCH` `DELETE` | `/admin/knowledge/{group_id}` | Ativa-desativa / remove um documento — exige login |
| `GET` | `/ui/` | Chat do cliente final (white-label, SPA estática) |
| `GET` | `/ui/admin/` | Painel interno da equipe (login + dashboard + conversas, só-leitura) |
| `GET` | `/ui/branding.json` | Configuração de marca do chat (editável) |
| `GET` | `/ui/widget.js` | Loader do widget embutível (uma linha de `<script>`) |
| `GET` | `/ui/embed-demo.html` | Página de demo com o widget embutido |

> **Acesso admin:** defina `ADMIN_PASSWORD` no `.env` para habilitar o login (sem ela, `/admin/login` responde 503 e o painel fica inacessível). O token de sessão fica no Redis com TTL `ADMIN_SESSION_TTL_SECONDS` (padrão **3600s / 1h**). `/metrics` e `/conversations/{id}` deixaram de ser públicos; para monitoramento externo use `GET /health`.

Docs interativas (Swagger) em `http://localhost:8010/docs`.

## Interface web

São duas telas estáticas (HTML/CSS/JS vanilla, sem build) servidas pelo próprio FastAPI.

### Chat do cliente — `http://localhost:8010/ui/`

O **chat do cliente final** (a raiz `/` redireciona para lá): um cartão centralizado, limpo e responsivo (vira tela cheia no mobile), com indicador de "digitando…", mensagem de boas-vindas na carga e persistência da conversa em `localStorage` (recarregar a página mantém o histórico; o botão ↺ recomeça). Todo conteúdo é renderizado via `textContent` (imune a XSS).

#### White-label via `branding.json`

A marca é configurada em **`backend/app/static/branding.json`** — **sem editar código**. Campos:

| Campo | Efeito |
|---|---|
| `brand_name` | Nome no header, título da aba e rodapé "Powered by" |
| `logo_url` | URL/caminho do logo (vazio → emoji ☀️) |
| `primary_color` / `text_on_primary` | Cor de destaque (header, bolhas do usuário, botão) |
| `subtitle` | Texto secundário no header |
| `welcome_message` | Bolha de boas-vindas inicial |
| `input_placeholder` | Placeholder do campo de mensagem |
| `show_powered_by` | Liga/desliga o rodapé "Powered by {brand_name}" |

Campos ausentes ou JSON inválido caem em defaults — a UI nunca quebra. Como o `backend` roda uma imagem buildada, rode `docker compose -p solar-ai-support-agent up --build -d backend` após editar (ou monte o arquivo por volume).

### Painel interno (admin) — `http://localhost:8010/ui/admin/`

A visão de **equipe**, protegida por **login** (acesso por URL direta, sem link na tela do cliente). Substitui o antigo inspector público. Só-leitura nesta versão. Defina `ADMIN_PASSWORD` no `.env`, abra a página e informe a senha — o token de sessão fica no `localStorage` e expira conforme `ADMIN_SESSION_TTL_SECONDS`.

- **Dashboard:** cards do `/admin/metrics` — leads por temperatura, total de conversas e % com humano, uso/custo de LLM e o evento mais comum.
- **Conversas:** tabela com nome, cidade, conta média, **score + temperatura** (badge hot/warm/cold), canal, data e flag de atendimento humano. Clicar numa linha abre o **detalhe**.
- **Detalhe da conversa:** conversa (estado/canal/status/humano), **dados do lead** coletados, **análise solar** com a **imagem de satélite do imóvel** (Esri World Imagery, via lat/lon geocodificada — **clique para ampliar**), faixa de placas/kWp/confiança e a flag "requer revisão técnica", e a **transcrição completa** do atendimento (cliente × IA).
- **Sair:** revoga o token (`/admin/logout`) e volta à tela de login.

Roteiro para popular dados: pelo chat do cliente (`/ui/`) envie (1) "Olá, sou a Ana de Natal, moro na Rua das Flores 123, minha conta vem R$ 800 e quero energia solar" → lead criado e pontuado; (2) "Autorizo a análise, pode verificar meu endereço" → geocoding + potencial solar + (lead quente) encaminhamento para humano. Depois abra o painel para ver tudo agregado.

### Widget embutível — uma linha de `<script>`

Para colocar o chat em **qualquer site**, a empresa adiciona uma linha apontando para a instância dela (modelo **self-host**: 1 empresa = 1 instância):

```html
<script src="https://SEU-HOST/ui/widget.js"
        data-teaser="Precisa de ajuda com energia solar?"></script>
```

Isso injeta um **botão flutuante** (canto inferior direito); ao clicar, abre o chat (`/ui/`) dentro de um **iframe**. Como o iframe é servido pelo próprio host, o `fetch('/chat')` é **same-origin — não há CORS** envolvido. A cor do botão sincroniza com `branding.json` via `postMessage` (o chat posta a marca para a página pai), e o botão ✕ do chat recolhe o painel.

- `data-teaser` é **opcional**: ausente → texto padrão; `data-teaser="off"` desliga o balão-convite; o balão aparece uma vez por visitante (`localStorage`).
- Posição fixa no canto inferior direito.
- Demonstração pronta em **`http://localhost:8010/ui/embed-demo.html`** (uma página fictícia de empresa com o widget embutido).

## Instruções e base de conhecimento

Pelo **painel admin** (`/ui/admin/`), a empresa personaliza o agente **sem editar código** — duas abas novas:

- **Instruções:** reescreva o prompt de sistema do agente. O editor vem pré-carregado com o prompt padrão; ao salvar, ele **substitui** o padrão por inteiro (há "Restaurar padrão" para voltar). Persistido na tabela singleton `agent_settings`.
- **Conhecimento:** anexe documentos (**PDF, DOCX, TXT, MD** ou **cole texto**). Cada documento é extraído, normalizado e quebrado em **trechos (chunks)** salvos em `knowledge_documents`. A cada resposta, o agente busca os trechos mais relevantes para a mensagem do cliente via **full-text search do PostgreSQL** (`tsvector`/`ts_rank`, índice GIN — sem embeddings nem serviço externo) e os injeta no prompt como **material de referência delimitado** (mitiga prompt injection), citando a fonte.

Parâmetros (env, com defaults): `KNOWLEDGE_TOP_K=4`, `KNOWLEDGE_MIN_RANK=0.01`, `KNOWLEDGE_CHUNK_SIZE=800`, `KNOWLEDGE_CHUNK_OVERLAP=100`, `KNOWLEDGE_MAX_CHUNKS=400`, `KNOWLEDGE_MAX_FILE_MB=10`.

> **Ressalva — modo mock:** as respostas em modo `mock` são roteadas por regra e **não usam prompt/LLM**, então instruções customizadas e base de conhecimento **só afetam os modos `openai`/`claude`/`hybrid`**. Os dados são salvos do mesmo jeito; o efeito aparece com um LLM real. O custo dos trechos injetados entra na contagem de tokens por turno (visível no dashboard).

## Testes

A suíte unitária roda com `pytest` dentro do container; os scripts de integração batem em PostgreSQL + Redis reais e limpam o que criam.

```bash
# Unitários (rápidos, sem I/O externo)
docker compose -p solar-ai-support-agent exec backend python -m pytest tests/unit -q

# Integração (exigem a stack de pé e o schema aplicado)
docker compose -p solar-ai-support-agent exec backend python tests/repository_smoke_test.py
docker compose -p solar-ai-support-agent exec backend python tests/agent_turn_event_test.py
docker compose -p solar-ai-support-agent exec backend python tests/metrics_test.py
docker compose -p solar-ai-support-agent exec backend python tests/session_test.py
docker compose -p solar-ai-support-agent exec backend python tests/chatwoot_test.py
```

> O serviço `backend` roda uma imagem buildada (sem volume mount do código). Após editar `backend/`, rode `docker compose -p solar-ai-support-agent up --build -d backend` antes de testar.

### Qualidade de código

As dependências de runtime ficam fixadas (pinned) em `backend/requirements.txt`; as ferramentas de desenvolvimento (pytest, ruff, mypy, pytest-cov, pip-audit) ficam em `backend/requirements-dev.txt` (a imagem instala ambas). A configuração das ferramentas mora em `backend/pyproject.toml`.

```bash
# Lint + formatação (ruff)
docker compose -p solar-ai-support-agent exec backend sh -c "cd /app && ruff check . && ruff format --check ."

# Type-checking (mypy, pacote app/)
docker compose -p solar-ai-support-agent exec backend sh -c "cd /app && mypy"

# Cobertura (gate de regressão em 74%)
docker compose -p solar-ai-support-agent exec backend sh -c "cd /app && python -m pytest tests/unit -q --cov=app --cov-fail-under=74"

# Auditoria de vulnerabilidades das deps de runtime
docker compose -p solar-ai-support-agent exec backend sh -c "cd /app && pip-audit -r requirements.txt --strict"
```

### Integração contínua (CI)

O GitHub Actions (`.github/workflows/ci.yml`) roda a cada push/PR:

- **lint** — `ruff check` + `ruff format --check`.
- **typecheck** — `mypy` sobre o pacote `app/`.
- **unit** — roda `pytest tests/unit` com cobertura e gate de regressão (`--cov-fail-under=74`).
- **security** — `pip-audit` sobre as deps de runtime fixadas.
- **integration** — sobe serviços Postgres + Redis, aplica o schema com `python database/apply_schema.py` e executa os scripts de integração.

## Decisões técnicas

- **SQL manual em vez de ORM:** os repositories usam `SQLAlchemy text()` com `commit/rollback` por método; os schemas Pydantic são a única representação tipada (`Model.model_validate(dict(row))`). Mantém o controle do SQL explícito e o projeto enxuto.
- **`agent_events` como trilha de auditoria:** cada passo relevante emite um evento, e cada turno é resumido em `agent_turn_completed` (tokens/modelo/custo/nº de eventos) — a base do `GET /metrics`.
- **Provider de LLM plugável:** `BaseLLMProvider` + factory por `LLM_PROVIDER` (`mock`/`openai`/`claude`/`hybrid`), com fallback para `mock`; trocar de modelo é trocar uma env var. A pré-análise geoespacial/solar é injetada no prompt (`llm/context.py`), então o LLM cita a **faixa de placas e kWp reais** do pipeline em vez de inventar.
- **Extração de lead provider-agnóstica:** uma camada própria (`llm/extraction/`, factory por `LEAD_EXTRACTION_PROVIDER`) extrai os campos do lead via LLM barato usando o histórico completo da conversa, com **fallback regex** se a API falhar. O provider de extração é independente do provider de resposta (extrair com OpenAI e responder com Claude, ou o inverso, para baratear).
- **PostgreSQL como fonte da verdade, Redis como cache:** a sessão da conversa e o mapa Chatwoot→conversa vivem no Redis com TTL; se o Redis cair, o fluxo continua e registra `session_store_unavailable`.
- **Webhook idempotente:** o `POST /webhooks/chatwoot` sempre responde `200` (mesmo se o envio da resposta falhar), evitando reentregas em loop do Chatwoot; mensagens `outgoing` são ignoradas para não responder a si mesmo.
- **Pré-análise geoespacial, não vistoria:** geocoding + potencial solar produzem uma estimativa preliminar e disparam handoff por `technical_review` quando necessário.
- **Português no domínio, inglês no código:** respostas do agente, prompts e termos de negócio em pt-BR; identificadores e comentários em inglês.

## Demonstração

> _Prints/GIF da API em ação (Swagger `/docs`, um `POST /chat` e o `GET /metrics`) podem ser adicionados aqui._ Veja o roteiro de demonstração em [`docs/demo-script.md`](docs/demo-script.md).

## Documentação disponível

- `docs/specs/001-solar-ai-support-agent/requirements.md`
- `docs/specs/001-solar-ai-support-agent/design.md`
- `docs/specs/001-solar-ai-support-agent/agent-behavior.md`
- `docs/specs/001-solar-ai-support-agent/geospatial-module.md`
- `docs/specs/001-solar-ai-support-agent/data-model.md`
- `docs/specs/001-solar-ai-support-agent/evaluation-plan.md`
- `docs/specs/001-solar-ai-support-agent/test-plan.md`
- `docs/specs/001-solar-ai-support-agent/tasks.md`

## Roadmap

O núcleo (spec **001**) está **100% concluído** e o projeto evoluiu além dele com três iniciativas adicionais (distribuição, footprint solar e hardening). Detalhe das tarefas do núcleo em [`docs/specs/001-solar-ai-support-agent/tasks.md`](docs/specs/001-solar-ai-support-agent/tasks.md).

**Núcleo — spec 001 (agente, geoespacial, monitoramento, integrações):**

| Fase | Tarefas | Status |
|---|---|---|
| Setup, modelo de dados, agente básico | T001–T011 | ✅ |
| Function calling (tools + extração estruturada) | T012–T015 | ✅ |
| Geoespacial (geocoding, solar, score) | T016–T018 | ✅ |
| Monitoramento (custos, métricas) | T019–T020 | ✅ |
| Integrações (Redis, Chatwoot) | T021–T022 | ✅ |
| Documentação e portfólio | T023–T024 | ✅ |
| Frontend (chat + inspector) e CI | T025–T026 | ✅ |

**Iniciativas além do núcleo:**

| Iniciativa | Entregue | Status |
|---|---|---|
| **002 — Distribuição plug-and-play** | chat white-label (`branding.json`), widget embutível (1 linha de `<script>`), painel admin com login, empacotamento | ✅ |
| **003 — Footprint solar** | provider solar `footprint` (área de telhado via OSM/Overpass + consumo) | ✅ |
| **Extração de leads por LLM** | camada provider-agnóstica (OpenAI/Claude/regex) com memória conversacional | ✅ |
| **004 — Hardening & qualidade** | deps pinadas, ruff (lint+format), mypy, cobertura com gate, pip-audit — tudo no CI | ✅ |
