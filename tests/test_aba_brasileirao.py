"""Fluxos reais de widgets, sem rede e sem chamadas a modelos."""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brasileirao as b

INICIO = """
import streamlit as st
import aba_brasileirao as ui
ui.preservar_estado()
ui.renderizar()
"""


def abrir():
    at = AppTest.from_string(INICIO, default_timeout=30).run()
    assert not at.exception
    return at


def test_bilhete_resultado_e_historico_persistem():
    at = abrir()
    at.radio(key="bra_escolha").set_value("X")
    at.number_input(key="bra_valor").set_value(35.50)
    at.button(key="bra_simular").click().run()
    assert not at.exception
    h = at.session_state["bra_historico"]
    assert len(h) == 1
    assert h[0]["escolha"] == "X" and h[0]["valor"] == 35.50
    assert any(m.label == "Retorno total" for m in at.metric)
    anterior = dict(h[0])
    at.selectbox(key="bra_mandante").select("Santos").run()
    at.number_input(key="bra_valor").set_value(100).run()
    assert not at.exception
    assert at.session_state["bra_historico"] == [anterior]
    assert at.session_state["bra_escolha"] == "X"


def test_confronto_sem_odd_desabilita_simulacao():
    at = abrir()
    ausente = next(j for j in b.carregar_jogos() if j["odd_1"] is None)
    at.selectbox(key="bra_mandante").select(ausente["mandante"]).run()
    at.selectbox(key="bra_visitante").select(ausente["visitante"]).run()
    assert not at.exception
    assert at.button(key="bra_simular").disabled
    assert at.radio(key="bra_escolha").disabled
    assert at.number_input(key="bra_valor").disabled
    assert at.session_state["bra_historico"] == []


def test_troca_de_mandante_nao_permite_jogar_contra_si():
    at = abrir()
    at.selectbox(key="bra_mandante").select("Fluminense").run()
    assert not at.exception
    assert "Fluminense" not in at.selectbox(key="bra_visitante").options
    assert at.selectbox(key="bra_visitante").value != "Fluminense"


def test_historico_limitado_sem_perder_numero_da_simulacao():
    at = abrir()
    r = b.simular_jogo(b.carregar_jogos()[0], "1", 20)
    at.session_state["bra_historico"] = [{**r, "numero": n} for n in range(20, 0, -1)]
    at.session_state["bra_contador"] = 20
    at.button(key="bra_simular").click().run()
    assert not at.exception
    assert len(at.session_state["bra_historico"]) == 20
    assert at.session_state["bra_historico"][0]["numero"] == 21


def test_integracao_no_app_e_preservacao_entre_abas():
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=60).run()
    assert not at.exception
    assert "Apostas Brasileirão" in [tab.label for tab in at.tabs]
    at.session_state["abas"] = "Apostas Brasileirão"
    at.run(timeout=60)
    at.number_input(key="bra_valor").set_value(75).run(timeout=60)
    at.button(key="bra_simular").click().run(timeout=60)
    anterior = dict(at.session_state["bra_historico"][0])
    at.session_state["abas"] = "ℹ️ Sobre"
    at.run(timeout=60)
    at.session_state["abas"] = "Apostas Brasileirão"
    at.run(timeout=60)
    assert not at.exception
    assert at.number_input(key="bra_valor").value == 75
    assert at.session_state["bra_historico"] == [anterior]
