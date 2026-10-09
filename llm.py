"""Chamada ao modelo de linguagem: Gemini (camada gratuita) ou Claude, conforme a chave disponível."""
import os

# Modelos padrão (conferidos na documentação em out/2026). Podem ser trocados por variável/secret.
# Gemini com camada gratuita. O primeiro é o mais rápido; os outros entram se ele estiver sobrecarregado (erro 503).
MODELOS_GEMINI = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.7-flash"]
TEMPO_LIMITE_MS = 20_000  # por tentativa
MODELO_CLAUDE = "claude-haiku-5-5"  # Haiku mais recente
MAX_TOKENS = 1500


class SemChave(Exception):
    """Nenhuma chave de API configurada."""


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


def responder(mensagens, prompt_sistema):
    """mensagens: [{"role": "user"|"assistant", "content": str}, ...] -> texto da resposta."""
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
    erro = None
    for modelo in modelos:  # tenta o próximo se este estiver sobrecarregado, lento ou vazio
        try:
            texto = client.models.generate_content(model=modelo, contents=conteudo, config=config).text
            if texto:
                return texto
            erro = ValueError("resposta vazia")
        except Exception as e:
            erro = e
    raise erro


def _claude(mensagens, prompt_sistema):
    import anthropic

    client = anthropic.Anthropic(api_key=_ler("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model=_ler("MODELO") or MODELO_CLAUDE,
        max_tokens=MAX_TOKENS,
        system=prompt_sistema,
        messages=[{"role": m["role"], "content": m["content"]} for m in mensagens],
    )
    return "".join(b.text for b in resp.content if b.type == "text")
