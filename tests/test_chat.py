"""Testes da robustez do chat (sem chamar nenhum modelo de verdade)."""
import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import llm
import registro
import simulador as s
from respostas_prontas import RESPOSTAS_PRONTAS

R = llm.Resposta


def sem_espera(_):
    pass


# --- novas tentativas -----------------------------------------------------------------

def test_tenta_de_novo_depois_de_erro():
    chamadas = []

    def f():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("503 sobrecarregado")
        return R("ok", True)

    assert llm.com_tentativas([f], dormir=sem_espera) == R("ok", True)
    assert len(chamadas) == 2


def test_passa_para_o_proximo_modelo():
    def falha():
        raise TimeoutError

    assert llm.com_tentativas([falha, lambda: R("modelo 2", True)], dormir=sem_espera).texto == "modelo 2"


def test_resposta_cortada_e_trocada_por_completa():
    respostas = iter([R("Imagine que você faça **1", False), R("resposta inteira", True)])
    assert llm.com_tentativas([lambda: next(respostas)], dormir=sem_espera) == R("resposta inteira", True)


def test_se_so_houver_resposta_cortada_devolve_a_maior_marcada_como_incompleta():
    respostas = iter([R("curta", False), R("um pouco maior", False)])
    r = llm.com_tentativas([lambda: next(respostas)], dormir=sem_espera)
    assert r == R("um pouco maior", False)


def test_tudo_falhou_relanca_o_erro():
    def falha():
        raise ConnectionError("sem rede")

    with pytest.raises(ConnectionError):
        llm.com_tentativas([falha, falha], dormir=sem_espera)


def test_respeita_o_tempo_total():
    tempo = iter([0, 0, 100, 100, 100, 100])
    chamadas = []

    def falha():
        chamadas.append(1)
        raise TimeoutError

    with pytest.raises(TimeoutError):
        llm.com_tentativas([falha, falha], tempo_total=50, dormir=sem_espera, relogio=lambda: next(tempo))
    assert len(chamadas) == 1


# --- respostas prontas ----------------------------------------------------------------

def test_quatro_respostas_prontas_com_fonte():
    assert len(RESPOSTAS_PRONTAS) == 4
    for pergunta, texto in RESPOSTAS_PRONTAS.items():
        limpo, _ = s.extrair_simular(texto)
        assert limpo.strip().splitlines()[-1].startswith("Fonte:"), pergunta


def test_exemplos_da_tela_tem_resposta_pronta():
    import ast
    import pathlib
    codigo = pathlib.Path(__file__).parents[1].joinpath("app.py").read_text(encoding="utf-8")
    inicio = codigo.index("EXEMPLOS = [")
    exemplos = ast.literal_eval(codigo[inicio + len("EXEMPLOS = "):codigo.index("]", inicio) + 1])
    assert set(exemplos) == set(RESPOSTAS_PRONTAS)


def test_resposta_do_cenario_aciona_o_simulador_sem_chamar_gasto():
    texto = RESPOSTAS_PRONTAS["Se eu apostar R$ 20 por rodada do Brasileirão numa odd 2,20, quanto isso pode custar?"]
    _, p = s.extrair_simular(texto)
    assert p == dict(valor=20, odd=2.2, apostas=38)
    assert "gasto" not in texto.lower()
    assert "margem" in texto


# --- registro anônimo -----------------------------------------------------------------

def test_registro_grava_csv(tmp_path):
    arq = tmp_path / "r" / "interacoes.csv"
    registro.registrar("abc123", "pergunta", "Como funciona?", "pronta", arquivo=arq)
    registro.registrar("abc123", "avaliacao", "Como funciona?", "pronta", "positiva", arquivo=arq)
    linhas = list(csv.DictReader(arq.open(encoding="utf-8")))
    assert [l["evento"] for l in linhas] == ["pergunta", "avaliacao"]
    assert set(linhas[0]) == set(registro.CAMPOS)
    assert registro.total_linhas(arq) == 2


def test_registro_nunca_derruba_o_app(tmp_path):
    bloqueado = tmp_path / "arquivo"
    bloqueado.write_text("x")
    registro.registrar("s", "pergunta", arquivo=bloqueado / "sub" / "a.csv")  # não lança erro


# --- pedido de palpite (Testes e Validação II, 06/11/2026) --------------------------------

import respostas_prontas as rp

PEDIDOS_DE_PALPITE = [
    "Devo apostar no Palmeiras?",
    "me dá um palpite pro jogo de hoje",
    "Quem ganha Flamengo x Vasco?",
    "Qual time vai ganhar o Brasileirão?",
    "Vale apostar no Corinthians hoje?",
    "qual a aposta mais certa pra hoje",
    "Me passa uma dica de aposta",
    "Qual a melhor casa de apostas?",
    "Quantos gols vai ter no jogo?",
    "O Flamengo vai ganhar hoje?",
    "Em quem eu aposto no clássico?",
]

PERGUNTAS_NORMAIS = [
    "O que significa uma odd de 2,50?",
    "Como bloquear meu CPF nas bets?",
    "Uma odd 2,20 compensa?",
    "Se eu apostar R$ 50 por semana no favorito, quanto perco em um ano?",
    "Como sei se um site é autorizado?",
    "Por que eu sinto que entendo de futebol e mesmo assim perco?",
    "Poderia me explicar o que ocorreu com a regularização das bets no Brasil?",
]


@pytest.mark.parametrize("texto", PEDIDOS_DE_PALPITE)
def test_pedido_de_palpite_e_detectado(texto):
    assert rp.eh_pedido_de_palpite(texto)


@pytest.mark.parametrize("texto", PERGUNTAS_NORMAIS + list(RESPOSTAS_PRONTAS))
def test_pergunta_normal_nao_vira_recusa(texto):
    assert not rp.eh_pedido_de_palpite(texto)


def test_resposta_de_palpite_nao_escolhe_lado_e_tem_fonte():
    limpo, params = s.extrair_simular(rp.PALPITE)
    assert params is None
    assert limpo.strip().splitlines()[-1].startswith("Fonte:")
    assert "margem" in limpo and "48%" in limpo


def test_resposta_sobre_aposta_traduz_odd_em_chance():
    texto = RESPOSTAS_PRONTAS["Como funciona uma aposta esportiva?"]
    assert "56%" in texto and "53%" in texto and "48%" in texto
