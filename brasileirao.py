"""Base 1X2 e sorteio de uma partida fictícia, sem dependência da interface."""
import csv
import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

import numpy as np

CAMINHO_BASE = Path(__file__).parent / "dados" / "brasileirao_2026.csv"
RESULTADOS = ("1", "X", "2")
COLUNAS_ODDS = ("odd_1", "odd_X", "odd_2")
CENTAVO = Decimal("0.01")
MAX_VALOR = Decimal("1000000.00")
SALDO_INICIAL = 50000  # centavos; todo o caixa da sessão usa inteiros
MAX_JOGOS_RODADA = 10


class ErroBrasileirao(ValueError):
    """Dado ou entrada que impede a simulação, com mensagem para a interface."""


def odds_do_jogo(jogo):
    valores = [jogo.get(c) for c in COLUNAS_ODDS]
    if any(v is None or v == "" for v in valores):
        raise ErroBrasileirao("Este confronto ainda não tem as três odds na base coletada.")
    try:
        odds = tuple(float(v) for v in valores)
    except (TypeError, ValueError) as exc:
        raise ErroBrasileirao("As odds do confronto são inválidas.") from exc
    if any(not math.isfinite(o) or o <= 1 for o in odds):
        raise ErroBrasileirao("As três odds precisam ser números finitos maiores que 1.")
    return odds


def carregar_jogos(caminho=CAMINHO_BASE):
    """Lê o retrato da coleta; valores ausentes continuam ausentes."""
    with Path(caminho).open(encoding="utf-8-sig", newline="") as arquivo:
        jogos = list(csv.DictReader(arquivo, delimiter=";"))
    pares, ids, times = set(), set(), set()
    for jogo in jogos:
        par = (jogo["mandante"], jogo["visitante"])
        if par[0] == par[1] or par in pares or jogo["id"] in ids:
            raise ErroBrasileirao("A base contém um confronto repetido ou inválido.")
        pares.add(par)
        ids.add(jogo["id"])
        times.update(par)
        campos = [jogo[c] for c in COLUNAS_ODDS]
        if all(v == "" for v in campos):
            if jogo["tipo"] != "Não encontrado":
                raise ErroBrasileirao("Há um confronto sem odds com classificação inconsistente.")
            jogo.update(dict.fromkeys(COLUNAS_ODDS))
        else:
            if jogo["tipo"] == "Não encontrado":
                raise ErroBrasileirao("Há odds em um confronto marcado como não encontrado.")
            jogo.update(zip(COLUNAS_ODDS, odds_do_jogo(jogo)))
    esperados = {(a, b) for a in times for b in times if a != b}
    if len(times) != 20 or len(jogos) != 380 or pares != esperados:
        raise ErroBrasileirao("A base precisa conter os 380 confrontos dos 20 times, nos dois mandos.")
    return jogos


def probabilidades(jogo):
    """Normaliza 1/odd entre os três resultados; hipótese, não previsão."""
    inversas = [1 / odd for odd in odds_do_jogo(jogo)]
    total = sum(inversas)
    return tuple(p / total for p in inversas)


def retorno_medio(jogo, valor=100):
    """Quanto volta, em média, de `valor` colocado em qualquer resultado do jogo (13/11/2026).

    Com p_i = (1/odd_i) / S, onde S = soma dos inversos das odds, o retorno esperado de cada
    resultado é odd_i * p_i * valor = valor / S: igual para vitória, empate e derrota.
    A diferença valor - valor / S é a parte que fica com a casa, em média (margem embutida nas odds).
    """
    soma = sum(1 / odd for odd in odds_do_jogo(jogo))
    medio = valor / soma
    return {"retorno_medio": medio, "perda_media": valor - medio, "soma_chances": soma}


def valor_em_centavos(valor):
    try:
        quantia = Decimal(str(valor))
    except (InvalidOperation, ValueError) as exc:
        raise ErroBrasileirao("Informe um valor fictício válido.") from exc
    if not quantia.is_finite() or not CENTAVO <= quantia <= MAX_VALOR:
        raise ErroBrasileirao("Use um valor entre R$ 0,01 e R$ 1.000.000,00.")
    if quantia != quantia.quantize(CENTAVO):
        raise ErroBrasileirao("O valor pode ter no máximo duas casas decimais.")
    return quantia


def calcular_bilhete(jogo, escolha, valor):
    if escolha not in RESULTADOS:
        raise ErroBrasileirao("Escolha vitória, empate ou derrota do mandante.")
    odds = odds_do_jogo(jogo)
    quantia = valor_em_centavos(valor)
    odd = odds[RESULTADOS.index(escolha)]
    retorno = (quantia * Decimal(str(odd))).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return {"valor": float(quantia), "odd": odd, "retorno_possivel": float(retorno),
            "lucro_possivel": float(retorno - quantia)}


def simular_jogo(jogo, escolha, valor, rng=None):
    """Um sorteio 1/X/2 por clique. O valor e a escolha não alteram o sorteio."""
    bilhete = calcular_bilhete(jogo, escolha, valor)
    chances = probabilidades(jogo)
    rng = rng if rng is not None else np.random.default_rng()
    sorteio = float(rng.random())
    if not 0 <= sorteio < 1:
        raise ErroBrasileirao("O sorteio precisa estar no intervalo de zero a um.")
    resultado = "1" if sorteio < chances[0] else "X" if sorteio < sum(chances[:2]) else "2"
    acertou = escolha == resultado
    retorno = bilhete["retorno_possivel"] if acertou else 0.0
    liquido = bilhete["lucro_possivel"] if acertou else -bilhete["valor"]
    return {**bilhete, "id": jogo["id"], "mandante": jogo["mandante"],
            "visitante": jogo["visitante"], "tipo": jogo["tipo"], "casa": jogo["casa"],
            "data_fonte": jogo["data_fonte"], "consulta": jogo["consulta"],
            "escolha": escolha, "resultado": resultado, "acertou": acertou,
            "retorno": retorno, "liquido": liquido}


def centavos(valor):
    return int(Decimal(str(valor)) * 100)


def nova_sessao():
    return {"saldo": SALDO_INICIAL, "rodadas": [], "encerrada": False}


def preparar_rodada(apostas, saldo):
    """Valida a rodada inteira antes de sortear ou movimentar o caixa."""
    if not 1 <= len(apostas) <= MAX_JOGOS_RODADA:
        raise ErroBrasileirao("Inclua de 1 a 10 confrontos na rodada.")
    ids, total, preparados = set(), 0, []
    for aposta in apostas:
        jogo = aposta["jogo"]
        if jogo["id"] in ids:
            raise ErroBrasileirao("Cada confronto pode aparecer apenas uma vez na mesma rodada.")
        ids.add(jogo["id"])
        bilhete = calcular_bilhete(jogo, aposta["escolha"], aposta["valor"])
        total += centavos(bilhete["valor"])
        preparados.append({"jogo": dict(jogo), "escolha": aposta["escolha"], **bilhete})
    if total > saldo:
        raise ErroBrasileirao("O total das apostas ultrapassa o saldo disponível. Reduza os valores ou remova um jogo.")
    return preparados, total


def executar_rodada(sessao, apostas, rng=None):
    """Liquida todas as apostas de uma rodada sem usar retornos antecipados."""
    if sessao["encerrada"] or sessao["saldo"] <= 0:
        raise ErroBrasileirao("Esta sessão já terminou. Comece uma nova sessão para simular.")
    preparados, total = preparar_rodada(apostas, sessao["saldo"])
    rng = rng if rng is not None else np.random.default_rng()
    resultados = []
    for aposta in preparados:
        r = simular_jogo(aposta["jogo"], aposta["escolha"], aposta["valor"], rng)
        r["prob"] = probabilidades(aposta["jogo"])[RESULTADOS.index(aposta["escolha"])]
        resultados.append(r)
    retornos = sum(centavos(r["retorno"]) for r in resultados)
    saldo = sessao["saldo"] - total + retornos
    rodada = {"numero": len(sessao["rodadas"]) + 1, "antes": sessao["saldo"], "depois": saldo,
              "apostado": total, "retorno": retornos, "resultados": resultados}
    return {"saldo": saldo, "rodadas": [*sessao["rodadas"], rodada], "encerrada": saldo == 0}


def resumo_sessao(sessao):
    resultados = [r for rodada in sessao["rodadas"] for r in rodada["resultados"]]
    return {"saldo": sessao["saldo"], "liquido": sessao["saldo"] - SALDO_INICIAL,
            "apostado": sum(r["apostado"] for r in sessao["rodadas"]),
            "retorno": sum(r["retorno"] for r in sessao["rodadas"]),
            "jogos": len(resultados), "acertos": sum(r["acertou"] for r in resultados),
            "rodadas": len(sessao["rodadas"])}


def comparar_sessoes(sessao, n=1000, semente=2026):
    """Repete o roteiro já realizado, com mesmos valores/odds e limite de caixa.

    Uma réplica para definitivamente se não consegue financiar a próxima rodada
    inteira. Escolhas que na sessão original reagiram a resultados anteriores são
    mantidas fixas aqui: comparação condicional, não previsão do comportamento.
    """
    if not sessao["rodadas"]:
        raise ErroBrasileirao("Simule pelo menos uma aposta antes de comparar.")
    if not isinstance(n, int) or not 1 <= n <= 10000:
        raise ErroBrasileirao("Quantidade de simulações inválida.")
    rng = np.random.default_rng(semente)
    saldos = np.full(n, SALDO_INICIAL, dtype=np.int64)
    ativas = np.ones(n, dtype=bool)
    impedidas = np.zeros(n, dtype=bool)
    for rodada in sessao["rodadas"]:
        total = rodada["apostado"]
        insuficientes = ativas & (saldos < total)
        impedidas |= insuficientes
        ativas &= ~insuficientes
        retorno = np.zeros(n, dtype=np.int64)
        for r in rodada["resultados"]:
            acerto = rng.random(n) < r["prob"]
            retorno += np.where(acerto, centavos(r["retorno_possivel"]), 0)
        saldos[ativas] += retorno[ativas] - total
    return {"saldos": saldos.tolist(), "n": n, "lucro": int(np.sum(saldos > SALDO_INICIAL)),
            "prejuizo": int(np.sum((saldos > 0) & (saldos < SALDO_INICIAL))),
            "zeradas": int(np.sum(saldos == 0)), "empate": int(np.sum(saldos == SALDO_INICIAL)),
            "impedidas": int(impedidas.sum()), "mediana": float(np.median(saldos)),
            "percentil_seu": float(np.mean(saldos <= sessao["saldo"]) * 100)}
