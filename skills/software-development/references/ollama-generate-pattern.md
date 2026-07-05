# Ollama Generate — Padrão de Implementação

## Como usar IA local para classificar e executar tarefas

### Funções Core (watchdog/core.py)

```python
import json
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "qwen2.5-coder:7b"    # 58 tok/s, $0

def ollama_disponivel() -> bool:
    """Verifica se Ollama esta rodando localmente."""
    try:
        req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return len(json.loads(req.read()).get("models", [])) > 0
    except Exception:
        return False

def ollama_generate(prompt: str, model=LOCAL_MODEL,
                    max_tokens: int = 512) -> Optional[str]:
    """Gera texto via Ollama local. Custo: $0."""
    try:
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens}
        }).encode()
        req = urllib.request.Request(OLLAMA_URL, data=payload,
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=60)
        return json.loads(resp.read()).get("response", "").strip()
    except Exception:
        return None

def classificar_tarefa_local(tarefa: str) -> Dict[str, Any]:
    """Usa IA local para classificar antes de gastar em API paga."""
    prompt = (
        "Classifique a tarefa abaixo em UMA das categorias:\n"
        "- 'leitura': ler arquivos, buscar informacao\n"
        "- 'codigo': escrever, editar, refatorar codigo\n"
        "- 'shell': comandos de terminal, instalar\n"
        "- 'arquitetura': planejar, desenhar, projetar\n"
        "- 'pesado': analise complexa, seguranca\n\n"
        f"Tarefa: {tarefa}\n\nResponda apenas com a categoria."
    )
    resposta = ollama_generate(prompt, max_tokens=20)
    if resposta:
        cat = resposta.strip().lower()
        if cat in ("leitura", "codigo", "shell"):
            return {"shell": "S1", "modelo": LOCAL_MODEL, "custo": "$0"}
        elif cat == "arquitetura":
            return {"shell": "S2", "modelo": "deepseek-v4-flash", "custo": "~$0.15/M"}
        elif cat == "pesado":
            return {"shell": "S3", "modelo": "deepseek-v4-pro", "custo": "~$0.50/M"}
    return {"shell": "S1", "modelo": LOCAL_MODEL, "custo": "$0"}  # fallback local
```

### Testes (tests/test_economy.py)

```python
def test_ollama_check():
    """Pula se Ollama nao estiver rodando (CI)."""
    if not ollama_disponivel():
        pytest.skip("Ollama offline")

def test_classificador_local_retorna_dict():
    resultado = classificar_tarefa_local("criar funcao em python")
    assert resultado["shell"] in ("S1", "S2", "S3")

def test_classificador_tarefa_simples_vai_local():
    resultado = classificar_tarefa_local("criar um site")
    assert resultado["shell"] == "S1"
    assert "0,00" in resultado["custo"]
```

### Economia Real

| Cenário | Só Nuvem | Com Ollama | Economia |
|---------|:-------:|:----------:|:--------:|
| 10 tarefas/dia | $0.02 | **$0.005** | **75%** |
| 300 tarefas/dia | $0.60 | **$0.03** | **95%** |
