---
name: roteador-economico
description: "ROTEAMENTO AUTOMÁTICO S3/S2/S1 + compressão via Ollama. Integrado ao shellz.py + skill-router. NUNCA perguntar — SEMPRE classificar antes de agir. REGRA ABSOLUTA: verificar antes de afirmar. REPO: ambiente→neo-hermes, projeto→jusplatform."
category: software-development
tags: [economia, roteamento, automatico, s3, s2, s1, shellz, custo, repo, compressao, ollama]
---
# Roteador Econômico — AUTOMÁTICO E INTEGRADO

## 🔴 ATIVADO AUTOMATICAMENTE — NÃO PERGUNTAR

## Classificação de Roteamento

| Categoria | Motor | Custo |
|:----------|:------|:------|
| Análise / Raciocínio / Estudo (sem web) | DeepSeek S3 | US$ 0.15/1M |
| Código simples / Comando local | Ollama S1 | **GRÁTIS** |
| Requer web / browser / integração externa | DeepSeek S3 | US$ 0.15/1M |
| **Compressão de contexto** | **Ollama S1** | **GRÁTIS ← FIXO** |
| **Gerar código (qualquer linguagem)** | **Ollama S1** | **GRÁTIS** |
| **Revisar código gerado** | **DeepSeek S3** | **US$ 0.15/1M** |

### 📌 Workflow validado: Gerar com Ollama, Revisar com DeepSeek

**Custo total de uma iteração de código: ZERO (geração) + US$ ~0,001 (revisão).**

Regra prática:
1. **Gerar código** → Ollama qwen2.5-coder:7b (S1, custo ZERO)
2. **Revisar** → DeepSeek V4 Flash (S3, ~US$ 0,001 por revisão)
3. **Corrigir bugs** → Se for simples, Ollama novamente; se for arquitetural, DeepSeek

> O usuário validou: "revisar é mais barato que criar, depois o deepseek revisa."

**⚠️ Atenção:** Ollama alucina APIs, nomes de namespace, e pacotes — especialmente em .NET/Avalonia.
Sempre verifique o código gerado. Consulte `references/dotnet-ollama-pitfalls.md` para os bugs mais comuns.

## 🔴 REGRA ABSOLUTA: Compressão DEVE usar Ollama

Compressão de contexto NUNCA deve usar DeepSeek (pago).
Sempre configurar `auxiliary.compression.provider=ollama` e `auxiliary.compression.model=qwen2.5-coder:7b`.

### Config ideal de compressão:
```yaml
compression:
  enabled: true
  threshold: 0.35       # Comprime quando 35% do limite atingido
  target_ratio: 0.15    # Comprime para 15% do original
  protect_last_n: 15    # Protege últimas 15 mensagens
  protect_first_n: 2    # Protege primeiras 2 mensagens
auxiliary:
  compression:
    provider: ollama     # ← OBRIGATÓRIO: grátis
    model: qwen2.5-coder:7b  # ← OBRIGATÓRIO: local
```

**Custo:** Antes DeepSeek = US$ 0.15/1M. Depois Ollama = **ZERO**.

## 🔴 REGRA: Footer de custo OBRIGATÓRIO

Toda resposta DEVE incluir footer de custo:
```
⚡ [X]k tokens | Régua US$ 1/1M → US$ [Y] | DeepSeek → US$ [Z] | Cache → US$ [W] | 🏆 Economia: US$ [E]
```

## 📦 SEPARAÇÃO DE REPOSITÓRIOS (Convenção Jul/2026)

| Tipo de mudança | Repositório | Path local |
|:----------------|:------------|:-----------|
| **Ambiente Hermes** (skills, configs, scripts) | `guilhermecrepaldi/neo-hermes` | `D:/projetos/gh-neo-hermes/` |
| **Projeto LegiData** | `guilhermecrepaldi/jusplatform` | `D:/projetos/jusplatform/` |

**NUNCA misture.** Antes de qualquer commit, verifique:
- Mudou skill/config/script de ambiente? → `gh-neo-hermes`
- Mudou API/produto/código do projeto? → `jusplatform`

## 🐫 Ollama: Markdown Fence Wrapping (Pitfall Crítico)

**Sintoma:** Ao pedir JSON/código para o Ollama (mesmo com "Retorne APENAS JSON"), ele frequentemente envolve a saída em ```json ou ``` markers.

**Exemplo:**
```json
{"comprimido": "...dados..."}
```
(perceba que Ollama adicionou ```json antes e ``` depois)

**Solução:** SEMPRE aplicar StripMarkdownWrapper() pós-geração:
```csharp
private static string StripMarkdownWrapper(string text)
{
    var lines = text.Split('\n')
        .Where(l => !l.Trim().StartsWith("```") && !l.Trim().StartsWith("~~~"))
        .ToArray();
    return string.Join("\n", lines).Trim();
}
```

**Detecção:** Ao receber JSON do Ollama que falhou parse, verifique se há ``` no texto. Teste com:
```python
import json, re
text = re.sub(r'```(?:json)?\n?', '', text).strip()
data = json.loads(text)
```

**Regra:** TODO código que consome saída do Ollama DEVE ter strip de markdown. Não confie que "sem explicacao" no prompt resolve.

## 🔴 REGRA ARQUITETURAL: Compressão Ollama NÃO é para o produto

**Contexto (Jul/2026):** A compressão via Ollama é EXCLUSIVAMENTE para o **sistema Hermes/DeepSeek** — economia de tokens de contexto entre o agente e o modelo. Não tem relação com o transporte de dados do produto telemetry.

| Sistema | Onde usar Ollama | Onde NÃO usar |
|:--------|:-----------------|:--------------|
| **Hermes/DeepSeek** (agente) | ✅ Compressão de contexto | — |
| **Performance Suite** (produto) | ❌ NUNCA | ✅ Só Brotli nível 11 |

O Performance Suite usa ONLY BrotliStream nível 11 para compressão de dados. Qualquer tentativa de inserir Ollama no pipeline de transporte do produto deve ser rejeitada.

## 📊 Avalonia: Drill-Down Dashboard com Zoom In/Out

Padrão de navegação para dashboards com múltiplos níveis de granularidade:

### Arquitetura
```
Level 0: MÁQUINAS     (visão geral, KPIs)
  → clique (ZoomInMachine)
Level 1: APPS         (aplicativos da máquina)
  → clique (ZoomInApp)
Level 2: TIMELINE     (registros minuto a minuto)
  → botão "← Voltar" (ZoomOut)
```

### Implementação no ViewModel
```csharp
private int _navLevel;  // 0=Maquinas, 1=Apps, 2=Timeline

public int NavLevel { get => _navLevel; set { ... RaisePropertyChanged(...); } }
public bool ShowMachines => NavLevel == 0;
public bool ShowApps => NavLevel == 1;
public bool ShowTimeline => NavLevel == 2;
public bool HasBack => NavLevel > 0;

public void ZoomInMachine(string id) { /* seta coleção Apps, NavLevel=1 */ }
public void ZoomInApp(string app) { /* seta coleção Timeline, NavLevel=2 */ }
public void ZoomOut() { /* NavLevel--, recarrega coleção anterior */ }
```

### No XAML
```xml
<ListBox IsVisible="{Binding ShowMachines}" SelectionChanged="..." />
<ListBox IsVisible="{Binding ShowApps}" SelectionChanged="..." />
<Grid IsVisible="{Binding ShowTimeline}">...</Grid>
<Button Content="← Voltar" IsVisible="{Binding HasBack}" Click="..." />
```

### No code-behind
```csharp
MachinesList.SelectionChanged += (_, e) => {
    if (MachinesList.SelectedItem is MachineCard m)
        (DataContext as DashboardViewModel)?.ZoomInMachine(m.MachineId);
    MachinesList.SelectedItem = null;  // limpa seleção
};
```

### Pitfalls Específicos do Dashboard
- **Opacidade excessiva**: `Opacity="0.5"` + fundo claro = texto ilegível. Use cores sólidas com alpha em backgrounds, não em texto. Prefira `Background="#14...."` e texto com `Opacity="1.0"`.
- **Seleção acumulada**: SEMPRE resetar `SelectedItem = null` após navegar, senão o ListBox mantém seleção fantasma.
- **DataContext nulo no code-behind**: Se o DataContext não for herdado corretamente (Avalonia TabControl), configure explicitamente no construtor da View.

## ⚠ Pitfalls

- **Compressão via DeepSeek é CARO.** `auxiliary.compression` SEMPRE deve usar Ollama. Verificar config.yaml se gasto de tokens estiver alto.
- **`hermes config set`** para alterar config.yaml. Não editar diretamente (ferramenta patch bloqueia).
- **Mudanças no config.yaml só valem na próxima sessão.** Execute `/new` para recarregar.
- **Ollama alucina em código .NET/Avalonia.** Consulte `references/dotnet-ollama-pitfalls.md` antes de aceitar código gerado sem revisão.
- **NUNCA assuma que código gerado pelo Ollama compila.** Namespaces, pacotes e APIs são frequentemente inventados. Sempre verifique com verificação estática antes de commit.
- **Verificação ad-hoc pós-ciclo:** Script Python descartável em `C:\Users\Home\AppData\Local\Temp\hermes-verify-*.py`, foco nos arquivos alterados no ciclo atual. Nunca script enorme — pequeno, rápido, deletado após passar.
- **dotnet build após cada correção:** O build real do .NET SDK é o único verificador definitivo. Scripts estáticos pegam ~70% dos bugs; `dotnet build` pega 100%.
