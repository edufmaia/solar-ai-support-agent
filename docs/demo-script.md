# Roteiro de demonstração — Solar AI Support Agent

Roteiro para um vídeo/demo de **~5 minutos** apresentando o projeto. Cada bloco traz o que falar (narração) e o que mostrar na tela (comandos/telas). Os comandos assumem a stack de pé (`docker compose -p solar-ai-support-agent up --build -d`) e o schema aplicado.

> Dica: rode `database/apply_schema.ps1` (ou `.sh`) antes de gravar e abra o Swagger em `http://localhost:8010/docs` numa aba.

---

## 0. Abertura (0:00–0:30)

**Narração:** "Este é o Solar AI Support Agent — um agente de IA para empresas de energia solar que faz atendimento inicial, qualifica leads e ainda entrega uma pré-análise geoespacial do potencial solar do endereço. Backend em FastAPI, PostgreSQL, Redis e Docker, com a lógica de conversa orquestrada e cada passo rastreado por eventos."

**Tela:** README aberto no topo (título + lista "Status atual" + diagrama de Arquitetura).

---

## 1. Subindo a stack (0:30–1:00)

**Narração:** "Tudo sobe com um comando. A API fica na porta 8010, o Postgres na 5434 e o Redis na 6381."

**Tela / comandos:**
```bash
docker compose -p solar-ai-support-agent up --build -d
docker compose -p solar-ai-support-agent ps
curl http://localhost:8010/health
curl http://localhost:8010/health/db
```
Mostrar `{"status":"ok"}` e `{"status":"ok","database":"connected"}`.

---

## 2. Conversa e qualificação de lead (1:00–2:15)

**Narração:** "Vou mandar uma mensagem como se fosse um cliente. O agente extrai os dados do lead, calcula um score e uma temperatura, e responde em português pedindo o que falta."

**Tela / comandos:**
```bash
curl -X POST http://localhost:8010/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Olá, sou a Marina de Mossoró, minha conta vem R$ 650 e quero energia solar na minha casa\",\"channel\":\"api\"}"
```

**Narração:** "Repare no `conversation_id` retornado. Cada mensagem vira histórico, e o lead já foi criado e pontuado no banco."

**Tela / comandos:** mostrar o lead e a conversa criados:
```bash
docker compose -p solar-ai-support-agent exec postgres \
  psql -U solar -d solar_ai_support \
  -c "SELECT name, city, average_energy_bill, lead_score, lead_temperature FROM leads ORDER BY created_at DESC LIMIT 1;"
```

---

## 3. Pré-análise geoespacial + solar (2:15–3:15)

**Narração:** "Agora o diferencial: se o cliente autoriza e informa o endereço, o agente faz o geocoding, estima o potencial solar e reavalia o score. Se o caso exige avaliação técnica, ele escala para um humano."

**Tela / comandos:** (reutilize o `conversation_id` da etapa 2)
```bash
curl -X POST http://localhost:8010/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"Autorizo a análise. Meu endereço é Rua das Flores, 123, Natal\",\"conversation_id\":\"<COLE_O_ID>\",\"channel\":\"api\"}"
```

**Narração:** "Veja a trilha de eventos do agente — é a auditoria completa do que aconteceu no turno: extração, scoring, geocoding, potencial solar, reavaliação do score e o resumo do turno."

**Tela / comandos:**
```bash
docker compose -p solar-ai-support-agent exec postgres \
  psql -U solar -d solar_ai_support \
  -c "SELECT event_type FROM agent_events WHERE conversation_id='<COLE_O_ID>' ORDER BY created_at;"
```
Apontar `geospatial_analysis_completed`, `solar_potential_completed`, `lead_score_updated` e `agent_turn_completed`.

---

## 4. Monitoramento e custos (3:15–4:00)

**Narração:** "Cada turno registra tokens, modelo e custo estimado. O endpoint de métricas agrega tudo: leads por temperatura, conversas em atendimento humano, uso/custo por modelo e a contagem de eventos."

**Tela / comandos:**
```bash
curl http://localhost:8010/metrics
```
Mostrar o JSON com `leads`, `conversations`, `usage` e `events`.

---

## 5. Canal Chatwoot (4:00–4:30)

**Narração:** "O mesmo agente atende um webhook do Chatwoot. Uma mensagem recebida é processada e a resposta volta pela API do Chatwoot. Mensagens enviadas por nós mesmos são ignoradas, evitando loop, e a continuidade da conversa fica no Redis."

**Tela / comandos:**
```bash
curl -X POST http://localhost:8010/webhooks/chatwoot \
  -H "Content-Type: application/json" \
  -d "{\"event\":\"message_created\",\"message_type\":\"incoming\",\"content\":\"Quero energia solar em Natal\",\"conversation\":{\"id\":42},\"account\":{\"id\":1}}"
```
Mostrar `{"status":"handled", ...}`.

---

## 6. Qualidade e fechamento (4:30–5:00)

**Narração:** "O projeto tem providers de LLM plugáveis — mock, OpenAI e Claude, trocáveis por variável de ambiente — uma suíte de testes unitários e scripts de integração contra banco e Redis reais, e documentação de arquitetura e decisões técnicas no README."

**Tela / comandos:**
```bash
docker compose -p solar-ai-support-agent exec backend python -m pytest tests/unit -q
```

**Narração de encerramento:** "Backend completo: atendimento, qualificação, pré-análise solar, monitoramento de custos e integração omnichannel — tudo rastreável e pronto para escalar de mock para LLMs reais. Obrigado!"

---

## Checklist de gravação

- [ ] Stack no ar e schema aplicado.
- [ ] `.env` em modo `mock` (não expõe chaves) — ou `openai`/`claude` se quiser mostrar resposta real.
- [ ] Swagger (`/docs`) aberto numa aba.
- [ ] Terminal com fonte grande e histórico limpo.
- [ ] Substituir `<COLE_O_ID>` pelo `conversation_id` real entre as etapas 2 e 3.
- [ ] (Opcional) capturar prints do `/docs`, do `POST /chat` e do `/metrics` para colar na seção "Demonstração" do README.
