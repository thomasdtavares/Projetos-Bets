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


def aposta(jogo, valor=20, escolha="1"):
    return {"jogo":jogo,"escolha":escolha,"valor":valor}


def test_saldo_e_resumo_em_centavos(jogo):
    inicial = b.nova_sessao()
    s = b.executar_rodada(inicial,[aposta(jogo,35.50)],Sorteio(0))
    assert inicial == b.nova_sessao()  # função não altera a sessão anterior
    assert s["saldo"] == 53550
    s = b.executar_rodada(s,[aposta(jogo,100)],Sorteio(0.99))
    assert b.resumo_sessao(s) == {"saldo":43550,"liquido":-6450,"apostado":13550,
                                 "retorno":7100,"jogos":2,"acertos":1,"rodadas":2}


def test_rodada_liquida_apostas_separadas(jogo):
    outro = {**jogo,"id":"outro"}
    s = b.executar_rodada(b.nova_sessao(),[aposta(jogo,100),aposta(outro,50,"X")],Sorteio(0))
    assert s["saldo"] == 55000
    assert len(s["rodadas"]) == 1
    assert [r["liquido"] for r in s["rodadas"][0]["resultados"]] == [100,-50]


def test_nao_financia_rodada_com_ganhos_futuros(jogo):
    class NaoSortear:
        def random(self):
            raise AssertionError("A rodada inválida não pode iniciar um sorteio")
    s = b.nova_sessao()
    with pytest.raises(b.ErroBrasileirao,match="saldo"):
        b.executar_rodada(s,[aposta(jogo,300),aposta({**jogo,"id":"outro"},250)],NaoSortear())
    assert s == b.nova_sessao()


def test_zero_encerra_sem_reposicao(jogo):
    s = b.executar_rodada(b.nova_sessao(),[aposta(jogo,500)],Sorteio(.999))
    assert s["saldo"] == 0 and s["encerrada"]
    with pytest.raises(b.ErroBrasileirao,match="terminou"):
        b.executar_rodada(s,[aposta(jogo,.01)])
    assert b.nova_sessao() == {"saldo":50000,"rodadas":[],"encerrada":False}


def test_historico_completo_acima_de_vinte(jogo):
    s = b.nova_sessao()
    for _ in range(25):
        s = b.executar_rodada(s,[aposta(jogo,1)],Sorteio(.99))
    assert len(s["rodadas"]) == 25 and s["saldo"] == 47500
    assert b.resumo_sessao(s)["apostado"] == 2500


@pytest.mark.parametrize("caso",["vazia","duplicada","onze","sem_odds"])
def test_rodadas_invalidas(jogo,caso):
    apostas = [] if caso == "vazia" else [aposta(jogo)]*2 if caso == "duplicada" else [aposta({**jogo,"id":str(i)}) for i in range(11)] if caso == "onze" else [aposta({**jogo,"odd_X":None})]
    with pytest.raises(b.ErroBrasileirao):
        b.executar_rodada(b.nova_sessao(),apostas)


def test_monte_carlo_valores_exatos_e_frequencias(jogo):
    s = b.executar_rodada(b.nova_sessao(),[aposta(jogo,100)],Sorteio(0))
    c = b.comparar_sessoes(s)
    assert c == b.comparar_sessoes(s)
    assert c["n"] == len(c["saldos"]) == 1000
    assert set(c["saldos"]) == {40000,60000}
    assert sum(c[k] for k in ("lucro","prejuizo","zeradas","empate")) == 1000
    assert c["lucro"]/1000 == pytest.approx(6/13,abs=.04)
    assert c["impedidas"] == 0


def test_monte_carlo_para_sem_saldo_para_rodada_e_nao_volta(jogo):
    s = b.nova_sessao()
    for valor in (100,450,20):
        s = b.executar_rodada(s,[aposta(jogo,valor)],Sorteio(0))
    c = b.comparar_sessoes(s)
    # Perdeu a primeira: fica em 400 e não aposta 450 nem volta na rodada de 20.
    assert c["impedidas"] == c["saldos"].count(40000) > 0
    assert min(c["saldos"]) >= 0


def test_comparacao_sem_rodadas_rejeitada():
    with pytest.raises(b.ErroBrasileirao):
        b.comparar_sessoes(b.nova_sessao())
