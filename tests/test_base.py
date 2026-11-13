"""Base de conhecimento (13/11/2026): fichas P1 a P26, respostas-limite F1 a F5 e coerência com o prompt.

Também confere os números citados nos verbetes do Conteúdo IV com as mesmas hipóteses do texto.
"""
import math
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
BASE = (RAIZ / "conhecimento" / "base.md").read_text(encoding="utf-8")
PROMPT = (RAIZ / "prompt_sistema.md").read_text(encoding="utf-8")


def blocos():
    """Divide a base em {"P11": texto, "F1": texto, ...}."""
    partes = re.split(r"\n## ", "\n" + BASE)
    saida = {}
    for parte in partes:
        m = re.match(r"(?:Ficha (P\d+)|Resposta-limite (F\d+)) — ", parte)
        if m:
            saida[m.group(1) or m.group(2)] = parte
    return saida


def test_fichas_p1_a_p26_e_limites_f1_a_f5():
    b = blocos()
    assert [k for k in b if k.startswith("P")] == [f"P{i}" for i in range(1, 27)]
    assert [k for k in b if k.startswith("F")] == [f"F{i}" for i in range(1, 6)]


@pytest.mark.parametrize("n", range(11, 27))
def test_verbetes_do_conteudo_iv_tem_todas_as_partes(n):
    texto = blocos()[f"P{n}"]
    for parte in ("**Conceitos:**", "**Pergunta:**", "**Resposta:**", "**Quer entender melhor?**", "**Fontes:**"):
        assert parte in texto, (n, parte)
    fontes = texto.split("**Fontes:**")[1]
    assert re.search(r"^- \S", fontes, re.M), n


def test_prompt_so_cita_fichas_que_existem():
    b = blocos()
    citadas = set(re.findall(r"\b([PF]\d{1,2})\b", PROMPT))
    for faixa in re.findall(r"\bP(\d+) a P(\d+)\b", PROMPT):
        citadas |= {f"P{i}" for i in range(int(faixa[0]), int(faixa[1]) + 1)}
    assert citadas, "o prompt deveria citar fichas"
    assert citadas <= set(b), citadas - set(b)
    assert "P1 a P26" in PROMPT and "F1 a F5" in PROMPT


@pytest.mark.parametrize("conceito", [
    "ilusão de controle", "excesso de confiança", "falácia do apostador", "custo de oportunidade",
    "Kelly", "aversão à perda", "loss chasing", "near-miss", "house money", "ancoragem", "viés do presente",
    "disponibilidade", "taxa-base", "Lei dos Grandes Números", "Teorema Central do Limite", "Binomial",
])
def test_conceitos_do_workbook_estao_na_base(conceito):
    assert conceito.lower() in BASE.lower(), conceito


def test_numeros_dos_verbetes():
    # P11: odd 1,90 dos dois lados → soma 105,3%; chance sem margem 50%
    soma = 2 / 1.90
    assert round(soma * 100, 1) == 105.3
    assert (1 / 1.90) / soma == pytest.approx(0.5)
    # P12/P21: E[X] = p·o − 1 = −5%; equilíbrio 1/1,90 = 52,6%
    assert 0.5 * 1.90 - 1 == pytest.approx(-0.05)
    assert round(100 / 1.90, 1) == 52.6
    # P15: múltipla de seis seleções de 50%
    assert round(0.5 ** 6 * 100, 1) == 1.6
    # P19: odd 15,00 → 6,7%
    assert round(100 / 15, 1) == 6.7
    # P18/P23: R$ 20, cinco vezes por semana, aproximação normal (TCL)
    phi = lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2)))
    for apostas, esperado in ((260, 0.20), (1300, 0.03)):
        media = apostas * 20 * (0.5 * 1.90 - 1)
        dp = 20 * 1.90 * math.sqrt(0.25) * math.sqrt(apostas)
        assert 1 - phi(-media / dp) == pytest.approx(esperado, abs=0.005)
    # P22: R$ 433/mês por 60 meses a 13,75% a.a. líquido de 17,5% de IR → cerca de R$ 34 mil
    aporte = 5 * 52 / 12 * 20
    r = (1 + 0.1375 * (1 - 0.175)) ** (1 / 12) - 1
    assert round(aporte) == 433 and round(r * 100, 2) == 0.90
    assert 34_000 <= aporte * ((1 + r) ** 60 - 1) / r < 35_000
    assert 260 * 5 * 20 * 0.05 == pytest.approx(1300)
    # P26: rollover de 5× um bônus de R$ 100 a 5% de margem → cerca de R$ 25
    assert 5 * 100 * 0.05 / 1.05 == pytest.approx(23.8, abs=0.1)
    # F3: sete perdas seguidas a partir de R$ 10
    assert sum(10 * 2 ** i for i in range(7)) == 1270 and 10 * 2 ** 7 == 1280
    assert "R$ 1.270" in blocos()["F3"] and "R$ 1.280" in blocos()["F3"]
