import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import simulador as s


# --- Exemplo do Conteúdo IV: R$ 50, odd 1,80, p = 0,50, 52 apostas -----------

def test_exemplo_conteudo_iv():
    r = s.resumo_cenario(50, 1.80, 0.50, 52, taxa_mensal=0.8, periodicidade="semanal")
    assert r["prob_implicita"] == pytest.approx(0.5556, abs=1e-4)
    assert r["lucro_se_acertar"] == pytest.approx(40)
    assert r["perda_se_errar"] == 50
    assert r["valor_esperado"] == pytest.approx(-5.00)
    assert r["perda_esperada"] == pytest.approx(-260.00)
    assert r["total_apostado"] == 2600
    assert r["kelly"] == 0
    assert "menor ou igual" in r["mensagem"]
    assert r["retorno_por_100"] == pytest.approx(90)
    assert r["custo_oportunidade"]["total_acumulado"] > 2600


# --- Chance de acerto tirada da odd (sem pedir palpite) ---------------------------

def test_margem_das_odds_exemplo_da_ficha():
    assert s.margem_das_odds(s.ODDS_EXEMPLO_1X2) == pytest.approx(0.0479, abs=1e-3)


def test_prob_justa_tira_a_margem():
    assert s.prob_justa(1.80, 0.05) == pytest.approx((1 / 1.80) / 1.05)
    assert s.prob_justa(2.0, 0.0) == pytest.approx(0.5)


def test_sem_margem_valor_esperado_zero_e_com_margem_negativo():
    assert s.aposta_unica(100, 2.5, s.prob_justa(2.5, 0.0))["valor_esperado"] == pytest.approx(0)
    # com margem m, de cada R$ 100 voltam 100 / (1 + m), qualquer que seja a odd
    for odd in (1.30, 2.20, 7.00):
        r = s.aposta_unica(100, odd, s.prob_justa(odd, 0.05))
        assert r["retorno_por_100"] == pytest.approx(100 / 1.05)
        assert r["valor_esperado"] < 0


def test_resumo_sem_prob_usa_a_odd():
    r = s.resumo_cenario(20, 2.20, None, 38, margem=0.05)
    assert r["prob"] == pytest.approx((1 / 2.2) / 1.05)
    assert r["perda_esperada"] == pytest.approx(20 * 38 * (1 / 1.05 - 1))


@pytest.mark.parametrize("odds", [(2.0,), (4.0, 4.0, 4.0), (1.0, 2.0, 3.0)])
def test_margem_das_odds_invalida(odds):
    with pytest.raises(s.ErroValidacao):
        s.margem_das_odds(odds)


def test_custo_oportunidade_com_curva_apostando():
    r = s.custo_oportunidade(50, "semanal", 52, 0, fator_retorno=0.9)
    assert r["total_apostando"] == pytest.approx(2340)
    assert r["diferenca"] == pytest.approx(260)


def test_kelly_positivo_quando_ve_positivo():
    r = s.aposta_unica(10, 2.0, 0.6)  # VE = 10*(1.2-1) = 2
    assert r["valor_esperado"] == pytest.approx(2.0)
    assert r["kelly"] == pytest.approx(0.2)  # (0,6*2-1)/(2-1)


# --- Monte Carlo ---------------------------------------------------------------

def test_media_simulada_proxima_do_ve_analitico():
    r = s.monte_carlo(50, 1.80, 0.50, 52, semente=1)
    esperado = 52 * s.aposta_unica(50, 1.80, 0.50)["valor_esperado"]
    assert r["resultado_medio"] == pytest.approx(esperado, abs=20)  # erro-padrão ~ R$ 3


def test_mesma_semente_mesmo_resultado():
    a = s.monte_carlo(50, 1.80, 0.50, 52, banca=500, semente=42)
    b = s.monte_carlo(50, 1.80, 0.50, 52, banca=500, semente=42)
    c = s.monte_carlo(50, 1.80, 0.50, 52, banca=500, semente=43)
    assert np.array_equal(a["saldo_final"], b["saldo_final"])
    assert a["media"] == b["media"]
    assert a["media"] != c["media"]


def test_probabilidade_zero_perde_tudo():
    r = s.monte_carlo(10, 2.0, 0.0, 5, semente=1)
    assert np.all(r["saldo_final"] == -50)
    assert r["prob_abaixo_inicial"] == 1


def test_probabilidade_um_ganha_sempre():
    r = s.monte_carlo(10, 2.0, 1.0, 5, semente=1)
    assert np.all(r["saldo_final"] == 50)
    assert r["prob_abaixo_inicial"] == 0
    assert r["drawdown_maximo"] == 0


def test_ruina_com_banca_curta():
    r = s.monte_carlo(100, 2.0, 0.0, 10, banca=250, semente=1)
    assert r["prob_ruina"] == 1  # perde 2 apostas e o saldo (50) não cobre a terceira
    assert np.all(r["saldo_final"] == 50)
    assert r["total_apostado_medio"] == 200


def test_percentual_da_banca():
    r = s.monte_carlo(0, 2.0, 0.0, 2, modo="percentual", banca=1000, pct_banca=0.10, semente=1)
    assert np.all(r["saldo_final"] == pytest.approx(810))  # 1000 -> 900 -> 810


def test_martingale_dobra_apos_perda():
    r = s.monte_carlo(10, 2.0, 0.0, 3, modo="martingale", semente=1)
    assert np.all(r["saldo_final"] == -70)  # 10 + 20 + 40


def test_martingale_para_sem_saldo():
    r = s.monte_carlo(10, 2.0, 0.0, 6, modo="martingale", banca=100, semente=1)
    assert r["prob_ruina"] == 1
    assert np.all(r["saldo_final"] == 30)  # 10+20+40 = 70 apostados; 30 não cobre os 80


def test_comparar_padroes_devolve_tres_linhas():
    linhas = s.comparar_padroes(50, 1.80, 0.50, 20, banca=500, n_sim=500, semente=1)
    assert [l["Padrão"][:5] for l in linhas] == ["Stake", "Perce", "Marti"]


# --- Custo de oportunidade --------------------------------------------------------

def test_custo_oportunidade_taxa_zero():
    r = s.custo_oportunidade(50, "semanal", 52, 0)
    assert r["total_apostado"] == r["total_acumulado"] == 2600


def test_custo_oportunidade_mensal():
    r = s.custo_oportunidade(100, "mensal", 12, 1.0)
    assert r["total_acumulado"] == pytest.approx(100 * ((1.01**12 - 1) / 0.01))


# --- Validação ---------------------------------------------------------------------

@pytest.mark.parametrize("kwargs", [
    dict(valor=50, odd=1.0, prob=0.5),
    dict(valor=50, odd=0.8, prob=0.5),
    dict(valor=50, odd=2.0, prob=-0.1),
    dict(valor=50, odd=2.0, prob=1.2),
    dict(valor=-5, odd=2.0, prob=0.5),
])
def test_entradas_invalidas_aposta_unica(kwargs):
    with pytest.raises(s.ErroValidacao):
        s.aposta_unica(**kwargs)


def test_zero_apostas_bloqueado():
    with pytest.raises(s.ErroValidacao):
        s.monte_carlo(50, 2.0, 0.5, 0)
    with pytest.raises(s.ErroValidacao):
        s.monte_carlo(-50, 2.0, 0.5, 10)


def test_percentual_exige_banca():
    with pytest.raises(s.ErroValidacao):
        s.monte_carlo(0, 2.0, 0.5, 10, modo="percentual", pct_banca=0.05)


# --- Linha [SIMULAR ...] -----------------------------------------------------------

def test_extrair_simular():
    texto = "Vamos calcular.\n[SIMULAR valor=50 odd=1,80 prob=0.50 apostas=52 taxa=0.8 banca=500 modo=fixo]"
    limpo, p = s.extrair_simular(texto)
    assert limpo == "Vamos calcular."
    assert p == dict(valor=50, odd=1.8, prob=0.5, apostas=52, taxa=0.8, banca=500, modo="fixo")


def test_extrair_simular_campos_ausentes_e_percentual():
    _, p = s.extrair_simular("[SIMULAR valor=20 odd=2.20 prob=40 apostas=38]")
    assert p == dict(valor=20, odd=2.2, prob=0.4, apostas=38)


def test_extrair_simular_sem_prob_com_margem():
    _, p = s.extrair_simular("Texto\n[SIMULAR valor=20 odd=2.20 apostas=38 margem=4.8]")
    assert p == dict(valor=20, odd=2.2, apostas=38, margem=pytest.approx(0.048))


def test_sem_linha_simular():
    texto = "Resposta normal."
    assert s.extrair_simular(texto) == (texto, None)


# --- Simulador para leigos ---------------------------------------------------------

def test_distribuicao_exata_bate_com_valor_esperado_e_monte_carlo():
    p = s.prob_justa(2.2, 0.05)
    d = s.distribuicao(20, 2.2, p, 38)
    assert d["resultado_medio"] == pytest.approx(20 * 38 * (p * 2.2 - 1))
    assert d["chance_lucro"] + d["chance_perda"] + d["chance_empate"] == pytest.approx(1)
    mc = s.monte_carlo(20, 2.2, p, 38, n_sim=20_000, semente=3)
    assert d["chance_perda"] == pytest.approx(mc["prob_abaixo_inicial"], abs=0.02)


def test_distribuicao_casos_extremos():
    assert s.distribuicao(10, 2.0, 0.0, 5)["chance_perda"] == 1
    d = s.distribuicao(10, 2.0, 1.0, 5)
    assert d["chance_lucro"] == 1 and d["resultado_medio"] == pytest.approx(50)
    assert s.distribuicao(10, 2.0, 0.5, 2)["chance_empate"] == pytest.approx(0.5)  # 1 acerto e 1 erro


def test_pessoas_em_100_somam_100():
    d = s.distribuicao(50, 1.8, s.prob_justa(1.8), 52)
    g = s.pessoas_em_100(d)
    assert sum(g.values()) == 100 and g["perderam"] > g["ganharam"]


def test_quanto_mais_tempo_menos_gente_no_lucro():
    linhas = s.lucro_ao_longo_do_tempo(20, 2.2, s.prob_justa(2.2), 2)
    assert len(linhas) == 60 and linhas[-1]["apostas"] == 520
    tend = [l["tendencia"] for l in linhas]
    assert tend[-1] < tend[0] * 0.5
    assert linhas[-1]["resultado_medio"] < linhas[0]["resultado_medio"] < 0


def test_cenario_do_chat():
    assert s.cenario_do_chat(38) == (1, "1 Brasileirão")
    assert s.cenario_do_chat(52) == (1, "1 ano")
    assert s.cenario_do_chat(104) == (1, "2 anos")


def test_estrategias_nenhuma_vence_a_margem():
    p = s.prob_justa(2.0)
    linhas = {l["chave"]: l for l in s.comparar_estrategias(20, 2.0, p, 100, banca=400, n_sim=4000, semente=7)}
    assert set(linhas) == set(s.ESTRATEGIAS)
    for l in linhas.values():
        assert l["resultado_medio"] < 0  # ninguém vence a margem, em média
        assert l["retorno_por_100"] < 100.5
    assert linhas["martingale"]["perderam_tudo"] > linhas["fixo"]["perderam_tudo"]
    assert linhas["recuperar"]["perderam_tudo"] > linhas["fixo"]["perderam_tudo"]
    # o limite de perda reduz a perda média em relação a apostar sem parar
    assert linhas["limite_perda"]["resultado_medio"] > linhas["fixo"]["resultado_medio"]


def test_estrategias_ninguem_aposta_mais_do_que_tem():
    linhas = s.comparar_estrategias(50, 2.0, 0.0, 10, banca=120, n_sim=10, semente=1)
    for l in linhas:
        assert l["resultado_medio"] >= -120 - 1e-9


def test_bilhete_multiplo_margem_se_multiplica():
    b = s.bilhete_multiplo(1.8, 3, margem=0.05)
    assert b["odd_total"] == pytest.approx(1.8 ** 3)
    assert b["chance_parece"] == pytest.approx((1 / 1.8) ** 3)  # ≈17%, como na ficha
    assert b["retorno_por_100"] == pytest.approx(100 / 1.05 ** 3)


def test_rodada_do_jogo():
    rng = np.random.default_rng(1)
    acertou, saldo, casa = s.rodada_do_jogo(rng, 2.0, 1.0, 10, 200)
    assert acertou and saldo == 210 and casa == pytest.approx(-10000)
    with pytest.raises(s.ErroValidacao):
        s.rodada_do_jogo(rng, 2.0, 0.5, 10, 5)
