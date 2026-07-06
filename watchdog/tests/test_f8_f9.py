"""Testes: DeterministicCompressor (V3-F8) + TersePolicy (V3-F9)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestDeterministicCompressor:
    """Testes do compressor determinístico — zero LLM, zero custo."""

    def test_import(self):
        from memory.deterministic_compressor import DeterministicCompressor
        dc = DeterministicCompressor()
        assert dc is not None

    def test_small_text_passthrough(self):
        from memory.deterministic_compressor import DeterministicCompressor
        dc = DeterministicCompressor(min_size_to_compress=500)
        text = "texto curto"
        assert dc.compress_tool_output(text) == text

    def test_empty_text(self):
        from memory.deterministic_compressor import DeterministicCompressor
        dc = DeterministicCompressor()
        assert dc.compress_tool_output("") == ""

    def test_none_text(self):
        from memory.deterministic_compressor import DeterministicCompressor
        dc = DeterministicCompressor()
        assert dc.compress_tool_output(None) is None

    def test_json_array_truncation(self):
        from memory.deterministic_compressor import DeterministicCompressor
        dc = DeterministicCompressor(max_array_items=5, min_size_to_compress=50)
        # Lista longa com indent para ultrapassar min_size
        data = list(range(100))
        import json
        compressed = dc.compress_tool_output(json.dumps(data, indent=2))
        result = json.loads(compressed)
        # Result: [0, 1, 2, 3, 4, "... e mais 95 itens"]
        assert len(result) == 6  # 5 itens + string de resumo
        assert result[0] == 0
        assert result[4] == 4
        assert "95" in str(result[-1])

    def test_json_object_nested(self):
        from memory.deterministic_compressor import DeterministicCompressor
        dc = DeterministicCompressor(max_str_len=50)
        data = {
            "name": "teste",
            "description": "a" * 200,
            "values": list(range(100)),
        }
        import json
        compressed = dc.compress_tool_output(json.dumps(data))
        result = json.loads(compressed)
        assert result["name"] == "teste"
        assert len(result["description"]) <= 100  # truncated
        assert len(result["values"]) <= 22  # 20 + summary
        assert "..." in str(result["values"][-1])

    def test_log_lines_preserves_errors(self):
        from memory.deterministic_compressor import DeterministicCompressor
        dc = DeterministicCompressor(max_log_lines=5)
        # Gera 100 linhas de log, com um erro no meio
        lines = [f"linha {i}: info" for i in range(100)]
        lines.insert(50, "ERROR: conexão recusada")
        text = "\n".join(lines)
        
        compressed = dc.compress_tool_output(text)
        # Deve preservar início, fim, e linha de erro
        assert "linha 0" in compressed
        assert "linha 99" in compressed
        assert "ERROR" in compressed

    def test_log_lines_preserves_exception(self):
        from memory.deterministic_compressor import DeterministicCompressor
        dc = DeterministicCompressor(max_log_lines=5)
        lines = [f"item {i}" for i in range(200)]
        lines.insert(100, "Traceback (most recent call last):")
        lines.insert(101, '  File "app.py", line 42, in main')
        lines.insert(102, "    raise ValueError('fail')")
        lines.insert(103, "ValueError: fail")
        text = "\n".join(lines)
        
        compressed = dc.compress_tool_output(text)
        assert "Traceback" in compressed
        assert "ValueError" in compressed
        assert "app.py" in compressed

    def test_long_string_truncation(self):
        from memory.deterministic_compressor import DeterministicCompressor
        dc = DeterministicCompressor(max_str_len=100)
        text = "a" * 1000
        compressed = dc.compress_tool_output(text)
        assert len(compressed) < 200
        assert "truncado" in compressed

    def test_idempotence(self):
        """Comprimir o mesmo texto N vezes produz o mesmo resultado."""
        from memory.deterministic_compressor import DeterministicCompressor
        dc = DeterministicCompressor(max_array_items=5, max_log_lines=5)
        
        # JSON
        big_json = '{"items": ' + str(list(range(50))) + '}'
        r1 = dc.compress_tool_output(big_json)
        r2 = dc.compress_tool_output(r1)  # comprime já comprimido
        assert r1 == r2
        
        # Logs
        big_log = "\n".join(f"linha {i}" for i in range(100))
        r1 = dc.compress_tool_output(big_log)
        r2 = dc.compress_tool_output(r1)
        assert r1 == r2

    def test_compress_fact_short(self):
        from memory.deterministic_compressor import DeterministicCompressor
        dc = DeterministicCompressor()
        text = "Fato curto para teste"
        assert dc.compress_fact(text) == text

    def test_compress_fact_removes_decoration(self):
        from memory.deterministic_compressor import DeterministicCompressor
        dc = DeterministicCompressor()
        # Texto longo o suficiente para ativar compress_fact
        text = "=== TÍTULO ===\nConteúdo importante que deve ser preservado\n" \
               "================" + "\nDetalhe adicional " * 20
        result = dc.compress_fact(text)
        assert "===" not in result
        assert "Conteúdo importante" in result


class TestTersePolicy:
    """Testes da política de concisão — sem afetar respostas para humanos."""

    def test_import(self):
        from core.terse_policy import TersePolicy
        tp = TersePolicy()
        assert tp is not None

    def test_disabled_passthrough(self):
        from core.terse_policy import TersePolicy
        tp = TersePolicy(enabled=False)
        prompt, system = tp.wrap_prompt("teste", role="reviewer")
        assert prompt == "teste"
        assert system is None

    def test_reviewer_prompt_gets_terse(self):
        from core.terse_policy import TersePolicy
        tp = TersePolicy()
        prompt, system = tp.wrap_prompt("Analise isso", role="reviewer")
        assert "Seja CONCISO" in prompt or (system and "Seja CONCISO" in system)

    def test_compressor_prompt_gets_terse(self):
        from core.terse_policy import TersePolicy
        tp = TersePolicy()
        prompt, system = tp.wrap_prompt("Resuma isso", role="compressor")
        assert "Seja CONCISO" in prompt or (system and "Seja CONCISO" in system)

    def test_executor_prompt_gets_terse(self):
        from core.terse_policy import TersePolicy
        tp = TersePolicy()
        prompt, system = tp.wrap_prompt("Implemente X", role="executor")
        assert "Seja direto" in prompt or (system and "Seja direto" in system)

    def test_system_prompt_extension(self):
        from core.terse_policy import TersePolicy
        tp = TersePolicy()
        prompt, system = tp.wrap_prompt("task", system="Você é um revisor.", role="reviewer")
        assert "Seja CONCISO" in system
        assert prompt == "task"

    def test_post_process_removes_greetings(self):
        from core.terse_policy import TersePolicy
        tp = TersePolicy()
        text = "Claro! Aqui está a resposta que você pediu."
        result = tp.post_process(text, role="executor")
        assert "Claro" not in result

    def test_post_process_removes_closings(self):
        from core.terse_policy import TersePolicy
        tp = TersePolicy()
        text = "A resposta é 42. Espero ter ajudado!"
        result = tp.post_process(text, role="executor")
        assert "ajudado" not in result

    def test_post_process_json_cleaning(self):
        from core.terse_policy import TersePolicy
        tp = TersePolicy()
        text = 'Aqui está o JSON:\n{"approved": true, "confidence": 0.9}\nEspero que ajude!'
        result = tp.post_process(text, role="reviewer", is_json=True)
        assert '{"approved": true' in result
        assert "Aqui está" not in result
        assert "ajude" not in result

    def test_post_process_preserves_data(self):
        """Terse não pode remover dados importantes."""
        from core.terse_policy import TersePolicy
        tp = TersePolicy()
        text = '{"issues": ["ERROR 404", "timeout"], "fix": "retry"}'
        result = tp.post_process(text, role="reviewer", is_json=True)
        assert "ERROR 404" in result
        assert "retry" in result

    def test_make_prompt_and_postprocess(self):
        from core.terse_policy import TersePolicy
        tp = TersePolicy()
        result = tp.make_prompt_and_postprocess(
            prompt="Analise isso",
            system=None,
            role="reviewer",
            is_json=True,
        )
        assert result["prompt"] is not None
        assert result["terse_applied"] is True

    def test_role_not_in_list(self):
        from core.terse_policy import TersePolicy
        tp = TersePolicy(roles=["reviewer"])
        prompt, system = tp.wrap_prompt("task", role="executor")
        assert prompt == "task"  # executor não está na lista
        assert system is None
