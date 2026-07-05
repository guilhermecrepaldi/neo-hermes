# Dual-Context Router — Implementação (CodeWriter)

> Padrão de arquitetura: Ollama S1 para desenvolvimento, DeepSeek exclusivo para app final.

## Estrutura

```
handlers/router.go       ← Roteador inteligente (dev context)
handlers/handlers.go     ← callDeepSeek() (app context)
```

## Regra

- `SmartGenerate()` — tenta Ollama primeiro, fallback DeepSeek. **Só existe no router.go.**
- `callDeepSeek()` — sempre nuvem. **Usado por TODAS as funções do app.**
- Nenhuma função do app (discussão, flashcard, pesquisa, final review) chama `SmartGenerate()`. Todas chamam `callDeepSeek()` diretamente.

## Código (router.go)

```go
// ClassificarTarefa — só chamada durante desenvolvimento (Hermes)
// Dentro do app, usa-se callGenerate() que chama DeepSeek diretamente.
func ClassificarTarefa(prompt string) (provider AIProvider, modelo string) {
    if !OllamaDisponivel() {
        return ProviderCloud, "deepseek-chat"
    }
    p := strings.ToLower(prompt)
    mustCloud := []string{
        "crie um material de estudo", "faça uma revisão final",
        "gere um questionário completo", "analise o código e aponte erros",
        "compare e contraste",
    }
    for _, keyword := range mustCloud {
        if strings.Contains(p, keyword) { return ProviderCloud, "deepseek-chat" }
    }
    return ProviderLocal, "qwen2.5-coder:7b"
}

// GenerateChatResponse — usada APENAS no mini-chat do app.
// DeepSeek como PROVEDOR ÚNICO. Ollama NÃO serve app final.
func GenerateChatResponse(systemMsg, userMsg string, maxTokens int) (string, error) {
    return callDeepSeek(prompt, 0.7, maxTokens)
}
```

## Sinais de alerta (você misturou os contextos)

- O usuário diz "HERMES USAR O OLLAMA como S1" — significa que você ESTAVA usando DeepSeek para tudo no dev, e ele quer que você use Ollama para economizar.
- O usuário diz "ollama s1 é para a construção do app" — você colocou código de Ollama DENTRO do app, e ele está lembrando que o app final só usa API key.

**Se isso acontecer, pare e reverta:**
1. Remova qualquer chamada a Ollama do backend do app
2. Crie `router.go` separado (apenas utilidade para dev)
3. Todas as funções do app chamam `callDeepSeek()` diretamente
