# Solar AI Support Agent

Agente de IA para atendimento inicial, qualificação de leads e pré-análise geoespacial para empresas de energia solar.

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
- endpoint `GET /metrics` com dados agregados (leads, conversas, uso/custo, eventos)
- sessão de conversa efêmera em Redis (cache com TTL; Postgres continua a fonte da verdade) com recuperação por turno e degradação graciosa
- webhook do Chatwoot (`POST /webhooks/chatwoot`): recebe mensagens `incoming`, processa pelo agente e responde via API do Chatwoot

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

```
                         ┌──────────────────────────────────────────┐
   POST /chat ───────────►                                          │
   POST /webhooks/chatwoot ─► api/  ──►  MockAgentOrchestrator       │
   GET  /metrics ─────────►  (FastAPI)        (agents/)              │
   GET  /health[/db] ─────►        │             │                   │
                         │         │             ├─► services/  (extração, scoring, métricas)
                         │         │             ├─► tools/     (save/update/classify/handoff)
                         │         │             ├─► llm/       (mock | openai | claude)
                         │         │             ├─► geocoding/ (mock | nominatim)
                         │         │             ├─► solar/     (mock)
                         │         │             └─► integrations/chatwoot/
                         │         ▼             ▼
                         │   repositories/ (SQL)   session/ (Redis)
                         └─────────┬───────────────────┬────────────┘
                                   ▼                   ▼
                            PostgreSQL            Redis (cache/TTL)
                         (fonte da verdade)   (sessão + mapa Chatwoot)
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

- `LLM_PROVIDER` aceita atualmente `mock`, `openai` e `claude`.
- Se `LLM_PROVIDER=openai` e `OPENAI_API_KEY` não estiver definida, `POST /chat` retorna erro claro de configuração.
- O fallback padrão continua sendo `mock`.

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

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Liveness — `{"status":"ok"}` |
| `GET` | `/health/db` | Checa conexão com o PostgreSQL |
| `POST` | `/chat` | Conversa com o agente (cria/recupera conversa, responde) |
| `POST` | `/webhooks/chatwoot` | Recebe mensagens do Chatwoot e responde via API |
| `GET` | `/metrics` | Métricas agregadas (leads, conversas, uso/custo, eventos) |

Docs interativas (Swagger) em `http://localhost:8010/docs`.

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

## Decisões técnicas

- **SQL manual em vez de ORM:** os repositories usam `SQLAlchemy text()` com `commit/rollback` por método; os schemas Pydantic são a única representação tipada (`Model.model_validate(dict(row))`). Mantém o controle do SQL explícito e o projeto enxuto.
- **`agent_events` como trilha de auditoria:** cada passo relevante emite um evento, e cada turno é resumido em `agent_turn_completed` (tokens/modelo/custo/nº de eventos) — a base do `GET /metrics`.
- **Provider de LLM plugável:** `BaseLLMProvider` + factory por `LLM_PROVIDER` (`mock`/`openai`/`claude`), com fallback para `mock`; trocar de modelo é trocar uma env var.
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

## Roadmap

Progresso: **24/25 tarefas (96%)** — backend completo e documentado. Detalhe em [`docs/specs/001-solar-ai-support-agent/tasks.md`](docs/specs/001-solar-ai-support-agent/tasks.md).

| Fase | Tarefas | Status |
|---|---|---|
| Setup, modelo de dados, agente básico | T001–T011 | ✅ |
| Function calling (tools + extração estruturada) | T012–T015 | ✅ |
| Geoespacial (geocoding, solar, score) | T016–T018 | ✅ |
| Monitoramento (custos, métricas) | T019–T020 | ✅ |
| Integrações (Redis, Chatwoot) | T021–T022 | ✅ |
| Documentação e portfólio | T023–T024 | T023 ✅ · T024 ⏳ |
