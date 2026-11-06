"""Cobertura da coleta, resultados exclusivos e valores monetários da simulação."""
import csv
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import brasileirao as b


class Sorteio:
    def __init__(self, valor):
        self.valor = valor

    def random(self):
        return self.valor


@pytest.fixture
def jogo():
    return {**b.carregar_jogos()[0], "odd_1": 2.0, "odd_X": 3.0, "odd_2": 4.0}


def test_coleta_completa_sem_inventar_odds():
    jogos = b.carregar_jogos()
    assert len(jogos) == 380
    assert set(Counter(j["mandante"] for j in jogos).values()) == {19}
    assert set(Counter(j["visitante"] for j in jogos).values()) == {19}
    assert Counter(j["tipo"] for j in jogos) == {
        "Histórica — fechamento": 309, "Pré-jogo — publicada": 20, "Não encontrado": 51}
    for j in jogos:
        if j["tipo"] == "Não encontrado":
            assert all(j[c] is None for c in b.COLUNAS_ODDS)
        else:
            assert sum(b.probabilidades(j)) == pytest.approx(1)
            assert j["casa"] and j["fonte"] and j["consulta"] and j["data_fonte"]


@pytest.mark.parametrize("mutacao", ["duplicado", "incompleto", "odd_parcial", "tipo_incorreto"])
def test_rejeita_base_corrompida(tmp_path, mutacao):
    with b.CAMINHO_BASE.open(encoding="utf-8-sig", newline="") as arq:
        linhas = list(csv.DictReader(arq, delimiter=";"))
    if mutacao == "duplicado":
        linhas[-1] = linhas[0].copy()
    elif mutacao == "incompleto":
        linhas.pop()
    elif mutacao == "odd_parcial":
        linhas[0]["odd_X"] = ""
    else:
        linhas[0]["tipo"] = "Não encontrado"
    caminho = tmp_path / "base.csv"
    with caminho.open("w", encoding="utf-8", newline="") as arq:
        gravador = csv.DictWriter(arq, fieldnames=linhas[0].keys(), delimiter=";")
        gravador.writeheader()
        gravador.writerows(linhas)
    with pytest.raises(b.ErroBrasileirao):
        b.carregar_jogos(caminho)


def test_chances_sao_inversos_normalizados(jogo):
    assert b.probabilidades(jogo) == pytest.approx((6/13, 4/13, 3/13))


@pytest.mark.parametrize("sorteio,resultado", [(0.0, "1"), (0.5, "X"), (0.999999, "2")])
@pytest.mark.parametrize("escolha", b.RESULTADOS)
def test_vitoria_empate_derrota_e_pagamento(jogo, sorteio, resultado, escolha):
    r = b.simular_jogo(jogo, escolha, 20, Sorteio(sorteio))
    assert r["resultado"] == resultado
    if escolha == resultado:
        assert r["acertou"]
        assert r["retorno"] == 20 * {"1": 2, "X": 3, "2": 4}[escolha]
        assert r["liquido"] == r["retorno"] - 20
    else:
        assert not r["acertou"]
        assert r["retorno"] == 0
        assert r["liquido"] == -20


def test_fronteiras_sem_sobreposicao(jogo):
    p = b.probabilidades(jogo)
    assert b.simular_jogo(jogo, "1", 20, Sorteio(p[0]))["resultado"] == "X"
    assert b.simular_jogo(jogo, "1", 20, Sorteio(sum(p[:2])))["resultado"] == "2"


def test_valor_escolha_e_resultado_anterior_nao_mudam_o_sorteio(jogo):
    resultados = [b.simular_jogo(jogo, escolha, valor, Sorteio(0.6))["resultado"]
                  for escolha in b.RESULTADOS for valor in (0.01, 20, 1000000)]
    assert set(resultados) == {"X"}


def test_arredondamento_e_centavos(jogo):
    jogo["odd_1"] = 2.5
    r = b.simular_jogo(jogo, "1", 0.01, Sorteio(0))
    assert r["retorno"] == 0.03
    assert r["liquido"] == 0.02


@pytest.mark.parametrize("valor", [0, -20, float("nan"), float("inf"), 0.001, 10.123, 1000001, "texto", None])
def test_rejeita_valor_invalido(jogo, valor):
    with pytest.raises(b.ErroBrasileirao):
        b.simular_jogo(jogo, "1", valor)


@pytest.mark.parametrize("odd", [None, "", 0, 1, -5, float("nan"), float("inf"), "texto"])
def test_rejeita_odd_ausente_ou_invalida(jogo, odd):
    jogo["odd_X"] = odd
    with pytest.raises(b.ErroBrasileirao):
        b.simular_jogo(jogo, "1", 20)


def test_rejeita_selecao_invalida(jogo):
    with pytest.raises(b.ErroBrasileirao):
        b.simular_jogo(jogo, "vitória", 20)


def test_distribuicao_do_sorteio(jogo):
    rng = np.random.default_rng(2026)
    contagem = Counter(b.simular_jogo(jogo, "1", 20, rng)["resultado"] for _ in range(10000))
    for codigo, p in zip(b.RESULTADOS, b.probabilidades(jogo)):
        assert contagem[codigo] / 10000 == pytest.approx(p, abs=0.02)
