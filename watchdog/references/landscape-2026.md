# 🌐 Landscape Open Source 2026 — Referências do Ecossistema

> Salvo em: 2026-07-05
> Fonte: Análise pattern-absorb de 8 repos top do GitHub
> Licenças verificadas individualmente

---

## 📊 Tabela Comparativa

| # | Projeto | ⭐ Stars | Stack | Licença | Telemetria? | API Key? | Categoria |
|---|---------|---------|-------|---------|-------------|----------|-----------|
| 1 | **Langflow** | 151.2K | Python/React Flow | MIT ✅ | ❌ | ❌ | AI Workflows Visuais |
| 2 | **Open WebUI** | 144.3K | Python/Svelte | Custom (≤50 users free) 🟡 | ❌ (config) | ❌ | UI para LLMs |
| 3 | **Dify** | 147.8K | TypeScript/Next.js | Apache-2.0 modificado 🟡 | ❌ | ❌ | Plataforma LLM Apps |
| 4 | **Supabase** | 105.8K | TypeScript/Postgres | Apache-2.0 ✅ | ❌ | ❌ | Backend-as-a-Service |
| 5 | **Browser Use** | 102.9K | Python/Playwright | MIT ✅ | ❌ | Opcional (cloud) | Automação Browser p/ AI |
| 6 | **OpenHands** | 79.5K | Python/Node.js | MIT ✅ (core) | ❌ | ❌ | Control Center Coding Agents |
| 7 | **Crawl4AI** | 71.0K | Python/Playwright | Apache-2.0 ✅ | ❌ | ❌ | Web Crawler p/ LLMs |
| 8 | **Coolify** | 57.9K | PHP/Laravel/Svelte | Apache-2.0 ✅ | ❌ | ❌ | Self-hosted PaaS |

## 🔍 Análise Detalhada por Repo

---

### 1. Langflow (151.2K ⭐) — MIT
**O que é**: Plataforma visual para construir e deployar agentes e workflows de IA.
**Stack**: Python + React Flow (visual node editor)
**Destaques**:
- 🎨 **Visual Builder**: Interface drag-and-drop de nós para construir pipelines de IA
- 🐍 **Código acessível**: Cada componente pode ser customizado em Python
- 🎮 **Playground interativo**: Teste flows passo-a-passo
- 🤖 **Multi-agent orchestration**: Com gerenciamento de conversação e retrieval
- 🚀 **Deploy como API ou MCP Server**: Cada flow vira uma ferramenta consumível
- 🔍 **Observability**: LangSmith, LangFuse integrados
- 🖥️ **Desktop App**: Windows/macOS nativo

**Padrões extraídos**:
```
- Visual node editor + code-behind pattern (React Flow + Python execution)
- Component-as-API: cada flow vira automaticamente endpoint REST + MCP tool
- Playground step-by-step execution para debugging visual
- Multi-agent conversation management pattern
```

---

### 2. Open WebUI (144.3K ⭐) — Custom License (≤50 users free)
**O que é**: Plataforma self-hosted para interagir com LLMs (Ollama + OpenAI-compatible).
**Stack**: Python (FastAPI) + Svelte + SQLite/PostgreSQL
**⚠️ Licença**: Free só até 50 usuários/mês rolling. Acima precisa licença comercial.

**Destaques**:
- 🚀 **Conecta qualquer LLM**: Ollama, OpenAI, LMStudio, GroqCloud, OpenRouter, vLLM
- 🧩 **Plugin System**: Filters, Actions, Pipes, Tools, Skills + MCP/MCPO/OpenAPI
- 🧠 **Persistent Memory**: O AI lembra fatos entre conversas
- 📚 **RAG local**: 9 vector databases, múltiplos extractors (Tika, Docling, Mistral OCR)
- 🔍 **Web Search**: 20+ providers de busca web
- 🌐 **Web Browsing**: `#` + URL puxa sites direto no chat
- 🎨 **Image Generation**: DALL·E, Gemini, ComfyUI, AUTOMATIC1111
- 📊 **Usage Analytics**: Dashboards de admin (tokens, custos, avaliação de modelos)
- 📅 **Calendar & AI Scheduling**: Agendamento de prompts recorrentes
- 📢 **Channels**: Espaços colaborativos em tempo real
- 🔐 **RBAC**: Roles, grupos, permissões granulares
- 🪪 **Enterprise Auth**: LDAP/AD, SSO, SCIM 2.0
- ☁️ **Cloud-Native File**: Google Drive, OneDrive integrados
- 🔭 **OpenTelemetry**: Observabilidade
- ⚖️ **Horizontal Scalability**: Redis + WebSocket multi-worker

**Padrões extraídos**:
```
- Plugin system extensível (Filters → Actions → Pipes → Tools → Skills)
- MCP protocol como backbone de integração externa
- Persistent memory cross-session (chat-to-chat context carry)
- Document pipeline: ingest → chunk → embed → hybrid search (BM25+vector) → rerank
- Automation/scheduling system: prompts recorrentes viram calendário
- RBAC multi-camada: roles + groups + permissions granulares
```

---

### 3. Dify (147.8K ⭐) — Modified Apache 2.0 🟡
**O que é**: Plataforma open-source de desenvolvimento de apps LLM.
**Stack**: TypeScript (Next.js) + Python (Flask) + PostgreSQL + Redis + Weaviate/Qdrant
**⚠️ Licença**: Apache-2.0 modificado — sem multi-tenant sem permissão, não pode remover branding. Free para uso pessoal/empresarial single-tenant.

**Destaques**:
- 🔧 **Workflow Visual**: Canvas para construir pipelines de IA
- 🤖 **Agent capabilities**: Function Calling + ReAct + 50+ built-in tools
- 📚 **RAG Pipeline**: Document ingestion → chunking → embedding → retrieval
- 💬 **Prompt IDE**: Interface para crafting, comparar modelos
- 🔍 **Observability integrada**: Opik, Langfuse, Arize Phoenix
- 🚀 **Backend-as-a-Service**: Tudo tem API REST

**Padrões extraídos**:
```
- Visual workflow canvas + agent orchestration
- 50+ built-in tools catalog (Google Search, DALL·E, Stable Diffusion, WolframAlpha)
- Document ingestion pipeline modular
- LLMOps: log + monitor + annotate → improve loop
```

---

### 4. Supabase (105.8K ⭐) — Apache-2.0 ✅
**O que é**: Plataforma de desenvolvimento Postgres — alternativa open-source ao Firebase.
**Stack**: TypeScript + PostgreSQL + Go + Elixir + Deno + Kong
**Destaques**:
- 🗄️ **Postgres Database**: Hosted, com replicação, Row Level Security
- 🔐 **Auth + Authorization**: JWT, OAuth2, SSO
- 📡 **Realtime**: WebSocket subscriptions sobre PostgreSQL replication
- 🔄 **Auto-generated APIs**: REST + GraphQL automáticos
- 🧠 **AI Toolkit**: pgvector, embeddings, semantic search
- 📁 **File Storage**: S3-compatible + Postgres permissions
- 🚀 **Edge Functions**: Deno-based, serverless
- 🖥️ **Dashboard**: UI completa para gerenciar tudo

**Padrões extraídos**:
```
- PostgreSQL como plataforma (não só banco) — Row Level Security, replication, pgvector
- Modular client libraries (supabase-js, supabase-py, supabase-csharp, supabase-swift...)
- Realtime subscriptions sobre PostgreSQL native replication
- Auto-generated REST/GraphQL do schema do banco
- Edge Functions (Deno) como compute layer
```

---

### 5. Browser Use (102.9K ⭐) — MIT ✅
**O que é**: Framework para agentes de IA controlarem navegadores.
**Stack**: Python + Playwright + LLM integration
**Destaques**:
- 🌐 **Browser automation**: Agentes controlam navegador real via Playwright
- 🔌 **CLI + Python API**: `browser-use` CLI + `from browser_use import Agent`
- 🎮 **Multiple LLMs**: OpenAI, Anthropic, Google, Browser Use Cloud
- 🛡️ **Allowed domains**: Restrição granular por domínio
- 🏗️ **Browser Harness**: Arquitetura que dá liberdade ao modelo (não abstrai complexidade)
- 📊 **Benchmark**: 100 tarefas reais de browser
- ☁️ **Cloud option**: Stealth, proxy rotation, captcha solving

**Padrões extraídos**:
```
- Browser automation via Playwright como backbone
- "Give freedom, don't abstract" — agent harness philosophy
- Allowed domains security pattern
- Skill pattern: skill registrável via CLI ("register the skill from `browser-use skill`")
```

---

### 6. OpenHands Agent Canvas (79.5K ⭐) — MIT ✅
**O que é**: Self-hosted control center para coding agents e automações.
**Stack**: Node.js (agent-canvas) + Python (software-agent-sdk) + Docker
**Destaques**:
- 🎮 **Agent Canvas**: UI para gerenciar coding agents (OpenHands, Claude Code, Codex, Gemini)
- 🔄 **Multiple backends**: Local, Docker, VM, Cloud
- 🤖 **ACP Protocol**: Agent-Client Protocol — conecta qualquer agente compatível
- ⏰ **Automations**: Agendamentos, webhooks → Slack, GitHub, Linear, Notion
- 🔀 **Multi-environment**: Switch entre backends sem perder contexto
- 🧩 **Pluggable**: Qualquer agente que implemente ACP

**Padrões extraídos**:
```
- ACP (Agent-Client Protocol) — padrão aberto para comunicação entre agentes
- Agent control center: hub central que gerencia N agentes em N backends
- Automation engine: schedule + event-driven + webhook → 3rd party services
- Multi-backend architecture: local ↔ Docker ↔ VM ↔ Cloud switchável
```

---

### 7. Crawl4AI (71K ⭐) — Apache-2.0 ✅
**O que é**: Web crawler open-source preparado para LLMs.
**Stack**: Python + Playwright + aiohttp
**Destaques**:
- 🧹 **LLM-ready Markdown**: Output limpo com headings, tables, code, citations
- 🚀 **Async browser pool**: Múltiplos navegadores assíncronos
- 🔄 **Session management**: Preserva estado entre páginas
- 🧩 **Hooks system**: Customizável em cada etapa do crawl
- 💾 **Caching**: Cache inteligente para evitar refetch
- 🔍 **Deep crawl**: Estratégias BFS, DFS, exploration modes
- 🤖 **LLM extraction**: Extração estruturada via qualquer LLM
- 🧱 **Chunking strategies**: Topic-based, regex, sentence-level
- 🔎 **Cosine similarity**: Busca semântica nos chunks
- 🔧 **CSS/LLM extractors**: Schema-based com XPath/CSS selectors

**Padrões extraídos**:
```
- Async browser pool architecture (N browsers concorrentes)
- Chunking strategies para preparação de conteúdo LLM
- Hooks pipeline: pre-hook → crawl → post-hook
- Cache-first: reduz custos e latência
- Deep crawl com crash recovery + resume_state
- CLI `crwl` + Python API dual interface
```

---

### 8. Coolify (57.9K ⭐) — Apache-2.0 ✅
**O que é**: PaaS self-hostable alternativo a Heroku/Netlify/Vercel.
**Stack**: PHP (Laravel) + Svelte + Inertia.js + Docker
**Destaques**:
- 🚀 **One-click deploy**: 280+ serviços (apps, databases, static sites)
- 🔐 **SSH-based management**: Gerencia VPS, Bare Metal, Raspberry Pi
- 🪄 **No vendor lock-in**: Configs salvas no servidor, não no Coolify
- 📦 **Docker Compose nativo**: Deployment via docker-compose
- 📊 **Server monitoring**: Uso de CPU, RAM, disco, rede

**Padrões extraídos**:
```
- Self-hosted PaaS architecture: SSH-based server management
- 280+ one-click services catalog
- Proxy/reverse proxy pattern (Traefik/Caddy) 
- Docker Compose as deployment primitive
```

---

## 🏆 Síntese: O QUE TRAZER PARA O NEO HERMES

### PRIORIDADE ALTA (IMPLEMENTAR AGORA)

#### 1. 🧠 ACP Protocol + Multi-Agent Control Center
**Inspirado em**: OpenHands Agent Canvas
**O que implementar**:
- Skill `acp-agent-controller` — hub central que gerencia coding agents (Hermes, Claude Code, Codex, Gemini)
- Protocolo ACP (Agent-Client Protocol) para comunicação padronizada
- Multi-backend: Hermes subagents ↔ ACP-compatible agents ↔ Ollama local ↔ DeepSeek

#### 2. 🧩 Plugin System (Filters → Actions → Pipes → Tools → Skills)
**Inspirado em**: Open WebUI
**O que implementar**:
- **Filters**: Hooks pre/post tool call (já temos `hermes-hooks` skill — expandir)
- **Actions**: Comandos customizáveis do usuário
- **Pipes**: Cadeias de transformação de dados
- **Tools**: Ferramentas registráveis via MCP/MCPO
- **Skills**: Já temos — expandir com searchable catalog

#### 3. 🌐 Browser Automation Skill (Browser Use)
**Inspirado em**: Browser Use
**O que implementar**:
- Skill `browser-automation` usando Playwright + Python
- Registrável via `browser-use skill` pattern
- Controle granular de domínios permitidos
- Headless mode configurável

#### 4. 🧹 Web Crawler LLM-Ready (Crawl4AI)
**Inspirado em**: Crawl4AI
**O que implementar**:
- Skill `web-crawler-llm` com chunking + markdown extraction
- Async browser pool (Playwright)
- Caching inteligente + hooks pipeline
- CLI + Python API dual interface

#### 5. 📚 Supabase como Backend Platform
**Inspirado em**: Supabase
**O que implementar**:
- PostgreSQL + pgvector para memória persistente do Hermes
- Row Level Security para multi-tenant
- Realtime subscriptions para notificações
- Auto-generated REST/GraphQL das tabelas de memória

### PRIORIDADE MÉDIA (PRÓXIMAS SEMANAS)

#### 6. 🎨 Visual AI Workflow Builder
**Inspirado em**: Langflow + Dify
**O que implementar**:
- Skill `visual-workflow-builder` (React Flow)
- Cada skill vira um nó arrastável
- Playground step-by-step execution

#### 7. 📊 Dashboard de Análise + RBAC
**Inspirado em**: Open WebUI + Dify
**O que implementar**:
- Dashboards de uso de tokens, custos, performance
- RBAC granulares (roles + groups + permissions)
- LLMOps: log + monitor + annotate → improve loop

#### 8. ⏰ Automation/Scheduling Engine
**Inspirado em**: Open WebUI + OpenHands
**O que implementar**:
- Já temos `cronjob` — expandir com:
  - Calendário visual de jobs
  - Webhook triggers (GitHub, Slack, Linear)
  - Event-driven automations
  - Multi-step workflows (DAG-based)

#### 9. 🔄 Deploy Pipeline Self-Hosted
**Inspirado em**: Coolify
**O que implementar**:
- Skill `hermes-deploy` para deploy automático via Docker Compose
- Gerenciamento SSH de servidores
- 1-click deploy de apps (Dashboards, APIs, Crawlers)

### PRIORIDADE BAIXA (EXPLORAR)

#### 10. 🖥️ Desktop App Nativo
**Inspirado em**: Langflow Desktop, Open WebUI Desktop
**Já temos**: Hermes Desktop GUI — expandir com:
- System-wide Spotlight search bar
- Screenshot capture integrado
- Push-to-talk voice

#### 11. 🔐 Enterprise Auth
**Inspirado em**: Open WebUI
- LDAP/AD, SSO, SCIM 2.0, OAuth providers
- OpenTelemetry + observabilidade

---

## 📌 Decisões de Absorção (por OSS Absorb A4)

| Repo | Estratégia | Justificativa |
|------|-----------|---------------|
| OpenHands | **pattern-absorb** ⭐ | ACP protocol é padrão aberto, MIT. Criar skill `acp-agent-controller` |
| Open WebUI | **analyze-only** | Licença Custom (restritiva >50 users). Extrair padrões de plugin system + memory + scheduling |
| Browser Use | **pattern-absorb** ⭐ | MIT. Skill `browser-automation` com Playwright |
| Crawl4AI | **pattern-absorb** ⭐ | Apache-2.0. Skill `web-crawler-llm` |
| Langflow | **pattern-absorb** ⭐ | MIT. Visual workflow pattern |
| Dify | **analyze-only** | Licença modificada. Extrair padrões de agente workflow |
| Supabase | **pattern-absorb** ⭐ | Apache-2.0. PostgreSQL backend pattern |
| Coolify | **analyze-only** | PHP/Laravel stack diferente. Extrair deploy patterns |
