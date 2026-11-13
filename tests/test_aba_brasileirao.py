"""Fluxos de sessão, rodadas, gráficos e encerramento sem chamar modelos."""
import sys
from pathlib import Path
from streamlit.testing.v1 import AppTest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import brasileirao as b

INICIO = """
import streamlit as st
import aba_brasileirao as ui
ui.preservar_estado()
ui.renderizar()
"""


def abrir():
    at = AppTest.from_string(INICIO,default_timeout=30).run()
    assert not at.exception
    return at


def test_bilhete_resultado_e_grafico_persistem():
    at = abrir()
    assert at.session_state["bra_sessao"]["saldo"] == 50000
    at.radio(key="bra_escolha").set_value("X")
    at.number_input(key="bra_valor").set_value(35.50)
    at.button(key="bra_simular").click().run()
    assert not at.exception
    s = at.session_state["bra_sessao"]
    r = s["rodadas"][0]["resultados"][0]
    assert r["escolha"] == "X" and r["valor"] == 35.50
    assert s["saldo"] == 50000 + b.centavos(r["liquido"])
    assert len(at.get("plotly_chart")) == 1
    at.selectbox(key="bra_mandante").select("Santos").run()
    assert not at.exception
    assert at.session_state["bra_sessao"] == s
    at.button(key="bra_comparar").click().run()
    assert not at.exception and len(at.get("plotly_chart")) == 2
    assert len(at.session_state["bra_comparacao"]["saldos"]) == 1000


def test_confronto_sem_odds_desabilita_simulacao():
    at = abrir()
    j = next(j for j in b.carregar_jogos() if j["odd_1"] is None)
    at.selectbox(key="bra_mandante").select(j["mandante"]).run()
    at.selectbox(key="bra_visitante").select(j["visitante"]).run()
    assert not at.exception and at.button(key="bra_simular").disabled
    assert at.number_input(key="bra_valor").disabled
    assert at.session_state["bra_sessao"] == b.nova_sessao()


def test_troca_mandante_exclui_proprio_time():
    at = abrir()
    at.selectbox(key="bra_mandante").select("Fluminense").run()
    assert not at.exception
    assert "Fluminense" not in at.selectbox(key="bra_visitante").options


def test_montar_remover_e_simular_rodada():
    at = abrir()
    at.radio(key="bra_modo").set_value("Montar rodada").run()
    at.button(key="bra_adicionar").click().run()
    assert at.button(key="bra_adicionar").disabled  # não duplica confronto
    at.selectbox(key="bra_visitante").select("Corinthians").run()
    at.number_input(key="bra_valor").set_value(35).run()
    at.button(key="bra_adicionar").click().run()
    assert len(at.session_state["bra_fila"]) == 2
    assert at.session_state["bra_sessao"]["saldo"] == 50000
    at.button(key="bra_remover_0").click().run()
    assert len(at.session_state["bra_fila"]) == 1
    at.selectbox(key="bra_visitante").select("Fluminense").run()
    at.button(key="bra_adicionar").click().run()
    at.button(key="bra_simular_rodada").click().run()
    assert not at.exception
    s = at.session_state["bra_sessao"]
    assert len(s["rodadas"]) == 1 and s["rodadas"][0]["apostado"] == 7000
    assert len(s["rodadas"][0]["resultados"]) == 2
    assert at.session_state["bra_fila"] == []


def test_valor_excessivo_bloqueado():
    at = abrir()
    at.number_input(key="bra_valor").set_value(501).run()
    assert not at.exception and at.button(key="bra_simular").disabled


def test_saldo_zero_resumo_e_nova_sessao(monkeypatch):
    class Perder:
        def random(self): return .99999
    executar = b.executar_rodada
    monkeypatch.setattr(b,"executar_rodada",lambda s,a: executar(s,a,Perder()))
    at = abrir()
    at.number_input(key="bra_valor").set_value(500).run()
    at.button(key="bra_simular").click().run()
    assert not at.exception
    assert at.session_state["bra_sessao"]["saldo"] == 0
    assert at.session_state["bra_sessao"]["encerrada"]
    assert any("Resumo da sessão encerrada" in x.value for x in at.markdown)
    at.button(key="bra_reiniciar").click().run()
    assert not at.exception
    assert at.session_state["bra_sessao"] == b.nova_sessao()
    assert at.session_state["bra_fila"] == []
    assert at.session_state["bra_comparacao"] is None
    assert len(at.get("plotly_chart")) == 0


def test_app_preserva_estado_e_melhorias_do_chat():
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=60).run()
    assert not at.exception
    assert "🏟️ Brasileirão (simulação)" in [t.label for t in at.tabs]
    at.session_state["abas"] = "🏟️ Brasileirão (simulação)"
    at.run()
    at.button(key="bra_simular").click().run()
    s = at.session_state["bra_sessao"]
    at.session_state["abas"] = "ℹ️ Sobre"
    at.run()
    at.session_state["abas"] = "🏟️ Brasileirão (simulação)"
    at.run()
    assert not at.exception and at.session_state["bra_sessao"] == s
