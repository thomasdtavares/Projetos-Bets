"""Chamada ao modelo de linguagem: Gemini (camada gratuita) ou Claude, conforme a chave disponível.

Robustez (23/10/2026, após o teste do app publicado): novas tentativas com espera entre elas,
limite de tempo total e aviso quando a resposta vem incompleta (cortada no meio).
"""
import os
import time
from typing import NamedTuple

# Modelos padrão (conferidos na documentação em out/2026). Podem ser trocados por variável/secret.
# Gemini com camada gratuita. O primeiro é o mais rápido; os outros entram se ele estiver sobrecarregado (erro 503).
MODELOS_GEMINI = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.7-flash"]
TEMPO_LIMITE_MS = 20_000   # por tentativa
TEMPO_TOTAL_S = 50         # somando todas as tentativas
TENTATIVAS_POR_MODELO = 2
ESPERA_S = 1.5             # espera antes da 2ª tentativa (dobra a cada nova tentativa)
MODELO_CLAUDE = "claude-haiku-5-5"  # Haiku mais recente
MAX_TOKENS = 4096          # folga para não cortar respostas (o limite antigo, 1500, cortou uma no meio)


class SemChave(Exception):
    """Nenhuma chave de API configurada."""


class Resposta(NamedTuple):
    texto: str
    completa: bool  # False quando o modelo parou antes de terminar (limite de tamanho, filtro etc.)


def _ler(nome):
    """Lê de st.secrets ou de variável de ambiente (vazio -> None)."""
    try:
        import streamlit as st
        valor = st.secrets.get(nome)
        if valor:
            return str(valor)
    except Exception:  # sem secrets.toml, ou fora do Streamlit
        pass
    return os.environ.get(nome) or None


def provedor():
    """'gemini', 'anthropic' ou None. Gemini tem prioridade por ter camada gratuita."""
    if _ler("GEMINI_API_KEY"):
        return "gemini"
    if _ler("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def com_tentativas(funcoes, tentativas=TENTATIVAS_POR_MODELO, espera=ESPERA_S, tempo_total=TEMPO_TOTAL_S,
                   dormir=time.sleep, relogio=time.monotonic):
    """Chama cada função da lista (uma por modelo) até uma devolver Resposta completa.

    Cada função ganha até `tentativas` chances, com espera crescente entre elas. Se só houver respostas
    incompletas, devolve a maior delas (melhor mostrar o que chegou, com aviso, do que nada).
    Se tudo falhar, relança o último erro.
    """
    inicio = relogio()
    erro, parcial = None, None
    for f in funcoes:
        for k in range(tentativas):
            if relogio() - inicio > tempo_total:
                break
            try:
                r = f()
            except Exception as e:  # rede, cota (429), sobrecarga (503), tempo esgotado...
                erro = e
            else:
                if r.texto and r.completa:
                    return r
                if r.texto and (parcial is None or len(r.texto) > len(parcial.texto)):
                    parcial = r
                erro = erro or ValueError("resposta vazia ou incompleta")
            if k < tentativas - 1:
                dormir(espera * (2 ** k))
    if parcial is not None:
        return parcial
    raise erro or ValueError("sem resposta")


def responder(mensagens, prompt_sistema):
    """mensagens: [{"role": "user"|"assistant", "content": str}, ...] -> Resposta(texto, completa)."""
    p = provedor()
    if p == "gemini":
        return _gemini(mensagens, prompt_sistema)
    if p == "anthropic":
        return _claude(mensagens, prompt_sistema)
    raise SemChave("Defina GEMINI_API_KEY (gratuita) ou ANTHROPIC_API_KEY.")


def _gemini(mensagens, prompt_sistema):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_ler("GEMINI_API_KEY"), http_options=types.HttpOptions(timeout=TEMPO_LIMITE_MS))
    conteudo = [
        types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part(text=m["content"])])
        for m in mensagens
    ]
    config = types.GenerateContentConfig(system_instruction=prompt_sistema, max_output_tokens=MAX_TOKENS)
    modelos = [_ler("MODELO")] if _ler("MODELO") else MODELOS_GEMINI

    def chamar(modelo):
        def f():
            resp = client.models.generate_content(model=modelo, contents=conteudo, config=config)
            motivo = ""
            try:
                motivo = str(resp.candidates[0].finish_reason or "")
            except Exception:
                pass
            return Resposta(resp.text or "", motivo == "" or motivo.endswith("STOP"))
        return f

    return com_tentativas([chamar(m) for m in modelos])


def _claude(mensagens, prompt_sistema):
    import anthropic

    client = anthropic.Anthropic(api_key=_ler("ANTHROPIC_API_KEY"), max_retries=0, timeout=TEMPO_LIMITE_MS / 1000)

    def f():
        resp = client.messages.create(
            model=_ler("MODELO") or MODELO_CLAUDE,
            max_tokens=MAX_TOKENS,
            system=prompt_sistema,
            messages=[{"role": m["role"], "content": m["content"]} for m in mensagens],
        )
        texto = "".join(b.text for b in resp.content if b.type == "text")
        return Resposta(texto, resp.stop_reason in ("end_turn", "stop_sequence"))

    return com_tentativas([f], tentativas=3)
