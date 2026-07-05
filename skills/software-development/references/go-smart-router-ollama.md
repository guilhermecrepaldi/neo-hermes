# Go Smart Router — Dual Context: Ollama + DeepSeek

## ⚠️ REGRA ABSOLUTA: Dois contextos, NUNCA misturar

### Contexto 1: Desenvolvimento (Hermes)
O Ollama S1 é usado para ECONOMIA durante a construção do app.

```
SmartGenerate() → ClassificarTarefa()
  ├── "criar material", "revisão final", "questionário completo", "analisar código"
  │     → DeepSeek Cloud (qualidade)
  └── TODO O RESTO
        → qwen2.5-coder:7b (Ollama local, 58 tok/s, $0)

Fallback: se Ollama falhar → DeepSeek Cloud (não interrompe)
```

### Contexto 2: App Final (CodeWriter SaaS)
Dentro do app, TODAS as chamadas de IA usam DeepSeek via API key.

```
callGenerate() → callDeepSeek()  (sempre nuvem)
GenerateChatResponse() → callDeepSeek() (sempre nuvem)
```

**NUNCA usar Ollama dentro do app.** O usuário final não tem Ollama instalado.

### ❌ Pitfall Crítico
```
ERRADO: "O Ollama está rodando, vou usar ele no app também"
CORRETO: "Ollama é para eu desenvolver. O app sempre usa DeepSeek."
```

## Arquitetura do Roteador (router.go)

```go
// ─── Router (para DESENVOLVIMENTO / Hermes) ───

func SmartGenerate(prompt string, temperature float64, maxTokens int) (string, error) {
    // Só tenta Ollama se for desenvolvimento
    if !OllamaDisponivel() {
        return callDeepSeek(prompt, temperature, maxTokens)
    }
    p := strings.ToLower(prompt)
    
    // Só DeepSeek para tarefas realmente pesadas
    mustCloud := []string{
        "crie um material de estudo", "faça uma revisão final",
        "gere um questionário completo", "analise o código e aponte erros",
    }
    for _, kw := range mustCloud {
        if strings.Contains(p, kw) {
            return callDeepSeek(prompt, temperature, maxTokens)
        }
    }
    
    // TODO o resto → Ollama
    return OllamaGenerate("qwen2.5-coder:7b", prompt, maxTokens)
}

// ─── App (para o SaaS CodeWriter) ───
// Chamadas diretas a callDeepSeek() em todos os handlers:
//   generateStudyContent       → callDeepSeek
//   generateDiscussResponse    → callDeepSeek
//   generateFlashcard          → callDeepSeek
//   generateFinalReview        → callDeepSeek
```

## Funções base

### OllamaDisponivel()
```go
func OllamaDisponivel() bool {
    client := &http.Client{Timeout: 2 * time.Second}
    resp, err := client.Get("http://localhost:11434/api/tags")
    if err != nil { return false }
    defer resp.Body.Close()
    return resp.StatusCode == 200
}
```
Timeout curto (2s) para não travar o app se o Ollama estiver offline.

### OllamaGenerate()
```go
func OllamaGenerate(model, prompt string, maxTokens int) (string, error) {
    reqBody := OllamaRequest{
        Model: model, Prompt: prompt,
        Stream: false, MaxTokens: maxTokens,
    }
    body, _ := json.Marshal(reqBody)
    client := &http.Client{Timeout: 120 * time.Second}
    resp, err := client.Post("http://localhost:11434/api/generate", "application/json", bytes.NewReader(body))
    // parse OllamaResponse.Response
}
```
Timeout longo (120s) porque modelos locais podem ser lentos.

### callDeepSeek() — em handlers.go
```go
func callDeepSeek(prompt string, temperature float64, maxTokens int) (string, error) {
    apiKey := os.Getenv("DEEPSEEK_API_KEY")
    // POST para https://api.deepseek.com/v1/chat/completions
    // Parse choices[0].message.content
}
```

## Pitfalls

- **NUNCA** timeout baixo no OllamaGenerate — 120s é seguro
- **NUNCA** travar o app se Ollama estiver offline — fallback silencioso
- **NUNCA** redeclarar `callDeepSeek` no router.go — ela já existe em handlers.go
- **SEMPRE** verificar `strings.TrimSpace(result) != ""` antes de aceitar resposta local
- **SEMPRE** separar: SmartGenerate() é para dev, handlers.go chama callDeepSeek() direto
- **SEMPRE** que o usuário disser "OLLAMA S1 É PARA CONSTRUÇÃO DO APP" → verificar se você misturou os contextos
