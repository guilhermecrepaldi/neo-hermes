# Go Smart Router Implementation — CodeWriter

Built in session 2026-06-19. Covers the dual-context pattern learned from user correction.

## Architecture

Two separate files in `handlers/`:

### `router.go` — Development Router (Ollama S1)
Used ONLY when building the app via Hermes. Never deployed in production.

```go
func SmartGenerate(prompt string, temperature float64, maxTokens int) (string, error) {
    provider, localModel := ClassificarTarefa(prompt)
    if provider == ProviderLocal {
        result, err := OllamaGenerate(localModel, prompt, maxTokens)
        if err == nil && strings.TrimSpace(result) != "" {
            return result, nil
        }
    }
    return callDeepSeek(prompt, temperature, maxTokens)
}
```

### `handlers.go` — Production Router (DeepSeek only)
All app AI calls use `callDeepSeek()` directly. Ollama is never called.

```go
// generateDiscussResponse → callDeepSeek()
// generateFlashcard → callDeepSeek()
// generateFinalReview → callDeepSeek()
// generateStudyContent → callDeepSeek()
```

## Key Functions

### `OllamaDisponivel()` — Health check
```go
func OllamaDisponivel() bool {
    client := &http.Client{Timeout: 2 * time.Second}
    resp, err := client.Get("http://localhost:11434/api/tags")
    if err != nil { return false }
    defer resp.Body.Close()
    return resp.StatusCode == 200
}
```

### `OllamaGenerate()` — Local inference
```go
func OllamaGenerate(model, prompt string, maxTokens int) (string, error) {
    reqBody := OllamaRequest{
        Model: model, Prompt: prompt,
        Stream: false, MaxTokens: maxTokens,
    }
    body, _ := json.Marshal(reqBody)
    client := &http.Client{Timeout: 120 * time.Second}
    resp, err := client.Post("http://localhost:11434/api/generate", ...)
    // parse OllamaResponse.Response
}
```

### `ClassificarTarefa()` — Route decision
```go
func ClassificarTarefa(prompt string) (AIProvider, string) {
    if !OllamaDisponivel() { return ProviderCloud, "deepseek-chat" }
    p := strings.ToLower(prompt)
    
    mustCloud := []string{
        "crie um material de estudo", "faça uma revisão final",
        "gere um questionário completo", "analise o código e aponte erros",
        "compare e contraste",
    }
    for _, kw := range mustCloud {
        if strings.Contains(p, kw) { return ProviderCloud, "deepseek-chat" }
    }
    
    return ProviderLocal, "qwen2.5-coder:7b"  // Everything else → Ollama
}
```

## Reescrita Evaluation (Feynman Method)

Three API endpoints in `handlers.go`:

### `POST /api/reescrita/avaliar`
AI compares original vs user's rewrite. Returns:
```json
{
  "assertividade": 0.75,
  "feedback": "Você capturou bem...",
  "precisa_rever": false,
  "conceitos_faltantes": ["conceito X"],
  "sugestao": "Tente incluir..."
}
```

### `POST /api/reescrita/salvar`
Persists to SQLite + localStorage (dual-write).

### `POST /api/reescrita/pergunta`
AI generates a reflective question about the text.

### Fallback (`generateFallbackAvaliacao`)
Word-count ratio when DeepSeek is unavailable. Thresholds: <0.3 = muito curto, <0.6 = parcial, <0.85 = bom, ≥0.85 = excelente.

## Available Local Models (this user's Ollama)
- qwen2.5-coder:7b (7.6B, 58 tok/s) — default S1
- mistral:latest (7.2B, 10.7 tok/s)
- llama3.1:8b (8.0B, 8.5 tok/s)
- deepseek-coder-v2:lite (15.7B, 4.6 tok/s)
- qwen3-vl:4b (4.4B) — vision
