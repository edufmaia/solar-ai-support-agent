# Guia de instalação no site da empresa

Este guia mostra como **hospedar** o Solar AI Support Agent e **embutir o chat**
no site da sua empresa. Ao final você terá:

- um **chat de atendimento** acessível em `https://SEU-HOST/ui/`;
- um **widget flutuante** que pode ser adicionado a qualquer página com **uma linha de `<script>`**;
- um **painel interno** (`/ui/admin/`) com dashboard, conversas e a pré-análise geoespacial.

> Para personalizar marca, cores e mensagens, veja o **[Guia de white-label](WHITE-LABEL.md)**.

---

## 1. Pré-requisitos

- Um servidor (VPS, máquina na nuvem, etc.) com **Docker** e **Docker Compose**.
- Um **domínio** apontando para o servidor (ex.: `atendimento.suaempresa.com.br`).
- _(Opcional)_ Chave de API de um provedor de LLM (**OpenAI** ou **Anthropic/Claude**)
  para respostas com IA real. Sem isso, a stack roda em modo `mock` (respostas roteirizadas).

---

## 2. Subir a stack

```bash
git clone https://github.com/edufmaia/solar-ai-support-agent.git
cd solar-ai-support-agent
cp .env.example .env      # edite o .env antes de subir (veja o passo 3)
docker compose up -d --build
```

O schema do banco é aplicado automaticamente e o backend sobe com healthcheck.
Por padrão a API responde na porta **8010** do host:

- Chat: `http://localhost:8010/ui/`
- Painel: `http://localhost:8010/ui/admin/`
- API (Swagger): `http://localhost:8010/docs`

---

## 3. Configurar para produção (`.env`)

Edite o arquivo `.env` **antes** de expor o serviço. Os pontos críticos:

| Variável | Para quê | Recomendação em produção |
|---|---|---|
| `ADMIN_PASSWORD` | Habilita e protege o painel `/ui/admin/` | Defina uma **senha forte**. Vazio = painel desabilitado. |
| `DATABASE_PASSWORD` | Senha do PostgreSQL | **Troque** o valor padrão (`solar_password`) por um segredo forte. |
| `LLM_PROVIDER` | Motor de resposta (`mock` / `openai` / `claude` / `hybrid`) | `hybrid` equilibra custo e qualidade. |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Credenciais do LLM | Necessárias se não usar `mock`. |
| `GEOCODING_PROVIDER` | `mock` ou `nominatim` (OpenStreetMap) | `nominatim` para geocoding real. |
| `SOLAR_PROVIDER` | `mock` ou `footprint` (telhado via OSM/Overpass) | `footprint` para a pré-análise real. |

> ⚠️ **Nunca** faça commit do arquivo `.env` — ele já está no `.gitignore`. O
> `.env.example` contém apenas valores de exemplo (a senha `solar_password` é um
> **padrão de desenvolvimento local**; troque-a em produção).

---

## 4. Colocar atrás de HTTPS

Coloque um **reverse proxy** (Nginx, Caddy, Traefik) na frente do serviço,
terminando TLS no seu domínio e encaminhando para a porta `8010`.

Exemplo mínimo com **Caddy** (`Caddyfile`):

```
atendimento.suaempresa.com.br {
    reverse_proxy localhost:8010
}
```

O Caddy provisiona o certificado HTTPS automaticamente. A partir daí o chat fica
em `https://atendimento.suaempresa.com.br/ui/`.

---

## 5. Embutir o chat no site

Adicione **uma linha** antes do `</body>` de qualquer página do seu site:

```html
<script src="https://atendimento.suaempresa.com.br/ui/widget.js"
        data-teaser="Quer simular sua economia com energia solar?"></script>
```

Isso injeta um **botão flutuante** no canto inferior direito; ao clicar, o chat
abre dentro de um **iframe** servido pelo seu host.

- `data-teaser` é **opcional**: ausente → texto padrão; `data-teaser="off"` desliga
  o balão-convite. O balão aparece uma vez por visitante (guardado em `localStorage`).
- A cor do botão sincroniza automaticamente com a sua marca (veja o
  [Guia de white-label](WHITE-LABEL.md)).
- Como o iframe é servido pelo **mesmo host**, a chamada interna `fetch('/chat')` é
  **same-origin** — não há configuração de CORS envolvida.

Há uma página de exemplo pronta em `https://SEU-HOST/ui/embed-demo.html`.

---

## 6. Validar

```bash
# saúde da API
curl https://SEU-HOST/health

# uma mensagem de teste no agente
curl -X POST https://SEU-HOST/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Quero saber sobre energia solar"}'
```

Abra `https://SEU-HOST/ui/` e converse; depois entre em `https://SEU-HOST/ui/admin/`
com a `ADMIN_PASSWORD` para ver a conversa, o lead e a pré-análise geoespacial.

---

## 7. Checklist de segurança em produção

- [ ] `ADMIN_PASSWORD` forte definida (e não compartilhada).
- [ ] `DATABASE_PASSWORD` trocada do padrão.
- [ ] `.env` **fora** do controle de versão.
- [ ] Serviço **somente via HTTPS** (reverse proxy com TLS).
- [ ] Portas do banco/Redis **não** expostas publicamente (no `docker-compose.yml`
      remova os mapeamentos `5434:5432` e `6381:6379` se o servidor for público).
- [ ] Backups regulares do volume do PostgreSQL.

---

## 8. Manutenção

```bash
git pull
docker compose up -d --build     # aplica atualizações
docker compose logs -f backend   # acompanha logs
docker compose down              # para a stack (use 'down -v' para apagar os dados)
```
