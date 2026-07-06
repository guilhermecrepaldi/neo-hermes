# 🏠 AMBIENTE — NEO HERMES (Source of Truth)
> **Criado:** 2026-07-01 | **Última verificação:** 2026-07-05
> **Propósito:** Toda sessão nova deve ler este documento primeiro.
> **Regra:** Se algo estiver diferente do descrito aqui, corrija ou atualize este documento.

---

## ⚔️ REGRAS DE OPERAÇÃO (CORE — NÃO NEGOCIÁVEL)

### 🔴 R1: COMPRESSÃO VIA OLLAMA — OBRIGATÓRIA E GLOBAL

> **TODO contexto >= 500 tokens DEVE ser comprimido via Ollama qwen2.5-coder:7b ANTES de qualquer chamada DeepSeek.**
> Config: `auxiliary.compression.provider: ollama`, `model: qwen2.5-coder:7b`
> Skill pinned global: `token-compressor` (carregada em 1º lugar em TODAS as sessões).
> Script: `D:/projetos/hermes-watchdog/compressor_local.py`

| Situação | Ação | Custo |
|:---------|:-----|:------|
| Contexto < 500 tok | ✅ Passa direto | $0 |
| Contexto >= 500 tok | ✅ Comprime via Ollama (~73% redução) | $0 |
| Cache hit | ✅ Usa cache (~7 dias) | $0 |
| Ollama offline | ⚠️ Passa direto com log de aviso | varia |

**Esta regra vale para TODAS as mensagens, TODAS as sessões, para SEMPRE.**
Compressão NUNCA usa DeepSeek (pago). Sempre Ollama (grátis).

### 🔴 R2: NUNCA USAR HEADROOM

> Headroom está **EXTERMINADO**. pip desinstalado, scripts deletados, skills limpas.
> Provider: deepseek direto. Proxy: nenhum. Porta :8787: morta.

### 🔴 R3: ROTEAMENTO S1/S3

> Classificar ANTES de agir. S1 (Ollama, $0) para código simples/compressão/tarefas locais.
> S3 (DeepSeek) só para arquitetura, pesquisa web, debug complexo.

---

## 1. ARQUITETURA
```
S3 (DeepSeek V4 Flash) = cérebro principal → fala DIRETO com DeepSeek
S1 (Ollama qwen2.5-coder:7b) = trabalhador local → tarefas $0

SEM HEADROOM. SEM PROXY. SEM :8787. SEM PONTO ÚNICO DE FALHA.
DeepSeek direto + Ollama compress inline (>=500 tok).
```

## 2. CONFIG HERMES

**Arquivo:** `~/AppData/Local/hermes/config.yaml`

| Chave | Valor |
|-------|-------|
| `model.default` | `deepseek-v4-flash` |
| `model.provider` | `deepseek` |
| `compression.enabled` | `true` |
| `auxiliary.compression.provider` | `ollama` |
| `auxiliary.compression.model` | `qwen2.5-coder:7b` |
| `delegation.provider` | `ollama` |
| `delegation.model` | `qwen2.5-coder:7b` |
| `delegation.base_url` | `http://localhost:11434/v1` |
| `autoload_skills` | `caveman-hermes,agent-reach,shellz-environment` |
| `skills.pinned` | `token-compressor` |

## 3. ORQUESTRAÇÃO S1/S3

| Tarefa | Rota | Custo |
|--------|:----:|:-----:|
| `ls, git, pip, criar arquivo, compilar, testar` | **S1** → terminal + Ollama | **$0** |
| `ajustar CSS, verificar, formatar, contar LOC` | **S1** → Ollama qwen2.5-coder | **$0** |
| **comprimir contexto (>=500 tok)** | **S1** → `compressor_local.py` | **$0** |
| `delegate_task` (subagentes) | **S1** → Ollama (configurado) | **$0** |
| Arquitetura, debug complexo, análise, pesquisa | **S3** → DeepSeek V4 Flash | $0.15/M |

> **Regra:** Classificar ANTES de agir. Toda tarefa é S1 ou S3. Se for S1, não gaste tokens do DeepSeek.

## 4. OLLAMA

| Item | Valor |
|------|-------|
| **Versão** | 0.30.7 |
| **Porta** | 11434 |
| **Modelo S1** | `qwen2.5-coder:7b` (7.6B, Q4_K_M) |
| **Iniciar** | `ollama serve` (background) |
| **Compressão** | `D:/projetos/hermes-watchdog/compressor_local.py` — ~73% economia |

### Modelos instalados (14)
- **ESSENCIAIS:** `qwen2.5-coder:7b`, `qwen3-vl:4b`, `deepseek-coder:6.7b`
- **EXTRAS (manter?):** mistral, llama3.1, qwen2.5, qwen2.5:14b, gemma3, llama3.2, deepseek-coder-v2:lite, nomic-embed-text, qwen2.5-coder:1.5b-base, llama3

## 5. AGENT REACH

| Item | Caminho / Comando |
|------|-------------------|
| **Venv** | `~/.agent-reach-venv/` |
| **Ativar** | `source ~/.agent-reach-venv/Scripts/activate` |
| **Versão** | 1.5.0 |
| **Canais** | 11/15 ativos |
| **Diagnóstico** | `agent-reach doctor` |

### OpenCLI (backbone browser)
| Item | Valor |
|------|-------|
| **Versão** | 1.8.5 |
| **Instalação** | `npm install -g @jackwener/opencli` |
| **Extensão Chrome** | `C:\opencli-extension\` (carregar sem compactação) |
| **Daemon** | Porta 19825 |
| **Status** | `opencli doctor` |

### ⚠️ REGRA DE RAM (sempre usar)
```bash
opencli instagram profile "x" -f yaml --window background --site-session persistent
# Aliases (definidos em ~/.bashrc):
oi="opencli instagram --window background --site-session persistent"
ot="opencli twitter --window background --site-session persistent"
of="opencli facebook --window background --site-session persistent"
or="opencli reddit --window background --site-session persistent"
ob="opencli bilibili --window background --site-session persistent"
ox="opencli xiaohongshu --window background --site-session persistent"
```

## 6. REPO NEO-HERMES

| Item | Valor |
|------|-------|
| **Local** | `~/neo-hermes/` |
| **GitHub** | `guilhermecrepaldi/neo-hermes` |
| **Branch** | `main` |
| **Commits** | 115+ |
| **Skills trackeadas** | 27 skills |
| **Testes** | 20 arquivos, 219+ testes |

### Comandos úteis
```bash
cd ~/neo-hermes
python -m pytest tests/ -v                                   # Todos os testes
python -m pytest tests/test_shellz.py -v                     # Só roteamento
python -c "import sys; sys.path.insert(0,'watchdog'); from shellz import shellz; print(shellz.rotear('sua tarefa'))"
```

## 7. TELEMETRIA (OBRIGATÓRIA)

**Toda resposta** DEVE terminar com:
```
── telemetria ───────────────
  S1 ollama: N tok (economia $X.XXXX)
  S3 deep:   N tok = $X.XXXX
```

Formato completo (padrão):
```bash
⚡ [X]k tokens | Régua US$ 1/1M → US$ [Y] | DeepSeek → US$ [Z] | Cache → US$ [W] | 🏆 Economia: US$ [E]
```

## 8. DEPENDÊNCIAS PYTHON

### Venv do Hermes (principal — `/c/Users/Home/AppData/Local/hermes/hermes-agent/venv/`)
✅ feedparser ✅ yt_dlp ✅ requests ✅ rich ✅ pyyaml ✅ Pillow ✅ pytest
❌ openpyxl ❌ loguru ❌ flask

Instalar se precisar: `pip install openpyxl loguru flask`

### Venv Agent Reach (`~/.agent-reach-venv/`)
Tem suas próprias deps (agent-reach, loguru, win32-setctime)

## 9. AUTO-START (Windows)

### O que inicia com o Windows

| Item | Arquivo | O que faz |
|------|---------|-----------|
| **Ollama** | `startup\hermes_ollama.vbs` | Inicia Ollama em background (invisível) |
| **Ambiente** | `startup\start_ambiente.bat` | Verifica Ollama, modelo S1, OpenCLI |
| **Gateway** | `startup\Hermes_Gateway.vbs` | Gateway do Hermes |

**Headroom removido.** Não inicia mais.

### Startup folder
```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
├── Hermes_Gateway.vbs      ← Gateway Hermes
├── hermes_ollama.vbs        ← Ollama invisível
└── start_ambiente.bat       ← Verificação do ambiente
```

### Verificação manual
```bash
start_ambiente.bat                           # Iniciar ambiente
cd ~/neo-hermes && python watchdog/health_check.py   # Saúde detalhada
```

### Cron job ativo
- **Nome:** `saude-ambiente`
- **Frequência:** A cada 30 minutos
- **Tipo:** Script puro (sem LLM) — verifica Ollama, modelo S1, OpenCLI, repo
- **Visualizar:** `cronjob action=list`

## 10. SETUP PÓS-FORMAÇÃO

**Script automático:**
```powershell
powershell -ExecutionPolicy Bypass -File "~/neo-hermes/watchdog/setup_novo_pc.ps1"
```

Ou siga manual:
1. Instalar Hermes Desktop
2. Clonar repo: `git clone https://github.com/guilhermecrepaldi/neo-hermes.git`
3. Rodar: `cd neo-hermes && powershell -File watchdog/setup_novo_pc.ps1`
4. Instalar Agent Reach: `pip install https://github.com/Panniantong/agent-reach/archive/main.zip`
5. Instalar OpenCLI: `npm install -g @jackwener/opencli`
6. Seguir `AMBIENTE.md` para verificar tudo

## 11. DEPENDÊNCIAS PYTHON

```bash
# Saúde
agent-reach doctor           # Status dos 15 canais
opencli doctor               # Status OpenCLI bridge
curl -s http://localhost:11434/api/version   # Ollama UP?

# Compressão via Ollama
cd ~/neo-hermes && python -c "import sys; sys.path.insert(0,'watchdog'); from compressor_local import doctor; d=doctor(); print(f'Ollama: {d[\"ollama\"]}, Compress: {d[\"compress_ok\"]}')"

# Prospecção Instagram
source ~/.agent-reach-venv/Scripts/activate
oi profile "username" -f yaml     # Perfil
oi search "landing page" -f yaml  # Buscar novos
oi user "username" -f yaml        # Posts

# Testes
cd ~/neo-hermes && python -m pytest tests/test_shellz.py tests/test_compressor_local.py tests/test_economy.py tests/test_telemetry.py -v
```
