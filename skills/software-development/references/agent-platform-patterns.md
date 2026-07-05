# Padrões de Plataforma de Agentes (inspirado no Agno 41k★)

## Repositório de referência
- **Agno (ex-phidata):** https://github.com/agno-agi/agno (41k★, 5.7k commits)
- **ECC (affaan-m):** https://github.com/affaan-m/ECC (211k★)

## Trifecta de Arquivos Determinísticos

Separar responsabilidades em 3 arquivos, não 1 monolítico:

| Arquivo | O que contém | Exemplo |
|:--------|:-------------|:--------|
| `.cursorrules` | Padrões de código (snippets, regras técnicas) | FastAPI patterns, type hints obrigatórios |
| `AGENTS.md` | Instruções para agentes de IA (Team pattern) | Revisores rodam em paralelo, solucionador pesquisa |
| `CLAUDE.md` / `DETERMINISTICO.md` | Estrutura do projeto, workflow, CI/CD | Regras de ferro, arquitetura imutável |

## Team Pattern (orquestração multi-agente)

Em vez de disparar agentes um por um, usar `Team(members=[...])`:

```python
# Em vez disso:
await agente1.revisar(contexto)
await agente2.revisar(contexto)
await agente3.resolver(problema)

# Faça isso:
class ReviewTeam:
    members = [Agente("Código", revisar_codigo), Agente("Arquitetura", revisar_arquitetura)]
    solver = Agente("Solucionador", resolver)
    
    async def review_and_fix(self, contexto):
        resultados = await self.review(contexto)  # paralelo
        for r in resultados:
            if not r.aprovado:
                await self.solver.funcao(r.problemas, contexto)
```

## Workflow Pattern (passos sequenciais)

Para fluxos determinísticos (não autônomos):

```python
# Workflow com passos explícitos
async def pipeline(contexto):
    # Passo 1: Revisão paralela
    r1, r2 = await asyncio.gather(revisar_codigo(ctx), revisar_arquitetura(ctx))
    # Passo 2: Se reprovou, solucionador
    if not r1.aprovado or not r2.aprovado:
        solucoes = await solucionador(r1.problemas + r2.problemas, ctx)
    # Passo 3: Correção automática
    return aplicar_correcoes(solucoes)
```

## Adicionar ao projeto
- `.cursorrules` na raiz do projeto
- `AGENTS.md` com descrição dos agentes disponíveis
- `DETERMINISTICO.md` com regras de ferro

## Referências salvas via API
```
POST /api/v1/referencias?titulo=...&url=...&tags=...&aprendizado=...
GET  /api/v1/referencias?tag=...
```
