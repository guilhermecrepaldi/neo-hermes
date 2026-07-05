# Referência de Implementação Go: tryOllama + callDeepSeek

Implementação de referência do padrão "tentar local primeiro, fallback cloud" em Go.

## Arquivo: handlers/research.go

### callDeepSeek()

```go
func callDeepSeek(prompt string, temperature float64, maxTokens int) (string, error) {
    // 1. Tenta Ollama local primeiro
    localModel := os.Getenv("OLLAMA_MODEL") // default: "qwen2.5:7b"
    if resp, err := tryOllama(prompt, localModel, temperature, maxTokens); err == nil {
        recordLocalTelemetry(estPrompt, estCompletion, estTotal)
        return resp, nil
    }
    // 2. Fallback: DeepSeek cloud
    apiKey := os.Getenv("DEEPSEEK_API_KEY")
    // ... requisição HTTP com timeout 60s ...
    recordCloudTelemetry(result.Usage.PromptTokens, result.Usage.CompletionTokens, result.Usage.TotalTokens)
    return result.Choices[0].Message.Content, nil
}
```

### tryOllama()

```go
func tryOllama(prompt, model string, temperature float64, maxTokens int) (string, error) {
    payload := map[string]interface{}{
        "model": model,
        "messages": []map[string]string{{"role": "user", "content": prompt}},
        "options": map[string]interface{}{
            "temperature": temperature,
            "num_predict": maxTokens,
        },
        "stream": false,
    }
    body, _ := json.Marshal(payload)
    req, _ := http.NewRequest("POST", "http://localhost:11434/api/chat", bytes.NewReader(body))
    req.Header.Set("Content-Type", "application/json")
    client := &http.Client{Timeout: 120 * time.Second}
    resp, err := client.Do(req)
    // ...
    var result struct {
        Message struct { Content string `json:"content"` } `json:"message"`
        Done bool `json:"done"`
    }
    json.Unmarshal(respBody, &result)
    return result.Message.Content, nil
}
```

## Telemetria Diferencial

| Tipo | Função | Custo |
|------|--------|-------|
| Local | `recordLocalTelemetry()` | $0.00 |
| Cloud | `recordCloudTelemetry()` | calculado por token |

O footer do app mostra 🏠 (local) ou ☁️ (cloud) no indicador de telemetria.

## Configuração

- `OLLAMA_MODEL` env var (default: `qwen2.5:7b`)
- Sem API key necessária para modo local
- Fallback silencioso: se Ollama offline, usa DeepSeek sem avisar

## Modelos Recomendados

| Modelo | Tamanho | Uso |
|--------|---------|-----|
| qwen2.5:7b | 4.7GB | Geral, recomendado |
| qwen2.5-coder:7b | 4.7GB | Código |
| deepseek-coder-v2:lite | 8.9GB | Código (melhor) |
| llama3.1:8b | 4.9GB | Geral |
