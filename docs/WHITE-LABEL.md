# Guia de white-label

Personalize **marca, cores, mensagens e comportamento** do agente para a sua
empresa — na maior parte **sem editar código**. Há duas camadas:

1. **Aparência** (marca, cores, textos da interface) → arquivo `branding.json`.
2. **Comportamento do agente** (instruções/prompt e base de conhecimento) →
   pelo **painel admin**, em tempo real.

---

## 1. Aparência — `branding.json`

A marca do chat é configurada em **`backend/app/static/branding.json`** e servida
em `GET /ui/branding.json`. Exemplo:

```json
{
  "brand_name": "EnergiaSol",
  "logo_url": "https://suaempresa.com.br/logo.png",
  "primary_color": "#0ea5e9",
  "text_on_primary": "#ffffff",
  "subtitle": "Atendimento inteligente",
  "welcome_message": "Olá! 👋 Vamos calcular sua economia com energia solar?",
  "input_placeholder": "Escreva sua mensagem...",
  "show_powered_by": false
}
```

### Campos

| Campo | O que controla |
|---|---|
| `brand_name` | Nome exibido no topo do chat e na aba do navegador. |
| `logo_url` | URL de uma imagem de logo (substitui o ícone ☀️). Vazio = ícone padrão. |
| `primary_color` | Cor principal (cabeçalho, bolhas do usuário, botões, launcher do widget). |
| `text_on_primary` | Cor do texto sobre a cor principal. |
| `subtitle` | Linha secundária no cabeçalho. |
| `welcome_message` | Primeira mensagem que o cliente vê. |
| `input_placeholder` | Texto do campo de digitação. |
| `show_powered_by` | `false` remove o rodapé "Powered by …". |

### Como aplicar as mudanças

A interface estática é **embutida na imagem** do backend. Depois de editar o
`branding.json`, reconstrua:

```bash
docker compose up -d --build backend
```

> **Dica (edição ao vivo):** para ajustar a marca sem rebuild, monte o arquivo como
> volume no serviço `backend` do `docker-compose.yml`:
> ```yaml
>     volumes:
>       - ./backend/app/static/branding.json:/app/app/static/branding.json:ro
> ```
> Assim, basta editar o arquivo e recarregar a página (o chat busca o
> `branding.json` com `cache: no-store`).

A cor principal também é propagada **automaticamente** para o botão flutuante do
widget embutível, via `postMessage` — não é preciso configurar nada na página que
hospeda o widget.

---

## 2. Mensagem-convite do widget (`data-teaser`)

No `<script>` de embed, o atributo `data-teaser` define o balão-convite:

```html
<!-- texto personalizado -->
<script src="https://SEU-HOST/ui/widget.js"
        data-teaser="Precisa de ajuda com energia solar?"></script>

<!-- sem balão-convite -->
<script src="https://SEU-HOST/ui/widget.js" data-teaser="off"></script>
```

---

## 3. Comportamento do agente — painel admin

Entre em `https://SEU-HOST/ui/admin/` (requer `ADMIN_PASSWORD`) para ajustar,
**sem reiniciar a stack**:

- **Instruções** — edite o _system prompt_ do agente (tom, regras, o que perguntar,
  quando encaminhar para um humano). Vale para os modos `openai`/`claude`.
- **Conhecimento** — suba documentos (PDF, DOCX, TXT, MD) ou cole texto. O conteúdo
  alimenta as respostas via busca (RAG) quando "Usar base de conhecimento" está ligado.

> O modo `mock` ignora instruções e base de conhecimento (respostas roteirizadas).
> Para que essas personalizações tenham efeito, use `LLM_PROVIDER=openai`, `claude`
> ou `hybrid` (veja o [Guia de instalação](INTEGRACAO-SITE.md)).

---

## 4. Resumo

| Quero mudar… | Onde |
|---|---|
| Nome, logo, cores, textos da interface | `branding.json` (+ rebuild ou volume) |
| Balão-convite do widget | atributo `data-teaser` no `<script>` |
| Rodapé "Powered by" | `show_powered_by` no `branding.json` |
| Tom e regras do agente | Painel admin → **Instruções** |
| Conhecimento da empresa nas respostas | Painel admin → **Conhecimento** |
