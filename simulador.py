"""Cálculos do simulador de apostas (funções puras, sem Streamlit).

Convenções:
- odd decimal O (> 1), probabilidade p em [0, 1], stake s em R$.
- taxa mensal em fração (0,008 = 0,8% ao mês) dentro das funções; a interface
  e a linha [SIMULAR ...] usam percentual (taxa=0.8).
- Hipóteses: apostas independentes, odd e p constantes, sem bônus nem impostos.
"""
import re

import numpy as np

MAX_APOSTAS = 5000
MODOS = ("fixo", "percentual", "martingale")
PERIODOS_POR_MES = {"diária": 365 / 12, "semanal": 52 / 12, "quinzenal": 26 / 12, "mensal": 1.0}


class ErroValidacao(ValueError):
    """Entrada inválida, com mensagem pronta para mostrar ao usuário."""


def validar(valor=None, odd=None, prob=None, apostas=None, banca=None, taxa_mensal=None):
    """Bloqueia entradas inválidas. Campos None são ignorados."""
    if odd is not None and not odd > 1:
        raise ErroValidacao("A odd precisa ser maior que 1 (por exemplo, 1,80). Com odd 1 ou menos, acertar não gera lucro.")
    if prob is not None and not 0 <= prob <= 1:
        raise ErroValidacao("A probabilidade deve estar entre 0% e 100%.")
    if valor is not None and not valor > 0:
        raise ErroValidacao("O valor da aposta deve ser maior que zero (não pode ser negativo).")
    if apostas is not None:
        if int(apostas) != apostas or apostas < 1:
            raise ErroValidacao("O número de apostas precisa ser um inteiro de pelo menos 1: com zero apostas não há o que simular.")
        if apostas > MAX_APOSTAS:
            raise ErroValidacao(f"O número de apostas está limitado a {MAX_APOSTAS} nesta versão.")
    if banca is not None and banca < 0:
        raise ErroValidacao("A banca inicial não pode ser negativa.")
    if taxa_mensal is not None and taxa_mensal <= -1:
        raise ErroValidacao("A taxa mensal precisa ser maior que -100%.")


def _pct(x):
    return f"{x * 100:.2f}%".replace(".", ",")


# ---------------------------------------------------------------- aposta única

def aposta_unica(valor, odd, prob):
    """Probabilidade implícita, lucro, valor esperado, equilíbrio e Kelly de uma aposta."""
    validar(valor=valor, odd=odd, prob=prob)
    ve_unitario = prob * odd - 1  # VE por R$ 1 apostado
    ve = valor * ve_unitario
    kelly = ve_unitario / (odd - 1) if ve_unitario > 0 else 0.0
    prob_implicita = 1 / odd
    if prob <= prob_implicita:
        mensagem = (
            f"Pelas hipóteses que você inseriu, sua probabilidade ({_pct(prob)}) é menor ou igual à "
            f"probabilidade implícita da odd ({_pct(prob_implicita)}). Isso significa valor esperado "
            "negativo ou nulo: em média, cada aposta devolve menos do que foi colocada. "
            "Isso não é uma previsão do jogo, é só a conta feita com os números que você informou."
        )
    else:
        mensagem = (
            f"Pelas hipóteses que você inseriu, sua probabilidade ({_pct(prob)}) é maior que a "
            f"probabilidade implícita da odd ({_pct(prob_implicita)}), então o valor esperado sai positivo. "
            "Lembre: odds já embutem a margem da casa, e sua estimativa é só um cenário, "
            "não uma probabilidade verdadeira. Se ela estiver otimista, a conta muda de sinal."
        )
    return {
        "prob_implicita": prob_implicita,
        "retorno_bruto": valor * odd,
        "lucro_se_acertar": valor * (odd - 1),
        "perda_se_errar": valor,
        "valor_esperado": ve,
        "ve_pct": ve_unitario,
        "prob_equilibrio": prob_implicita,
        "kelly": kelly,
        "mensagem": mensagem,
    }


def resumo_cenario(valor, odd, prob, apostas, taxa_mensal=None, periodicidade="semanal"):
    """Números analíticos de um cenário (usados no resumo do chat)."""
    r = aposta_unica(valor, odd, prob)
    validar(apostas=apostas)
    r["apostas"] = int(apostas)
    r["total_apostado"] = valor * apostas
    r["perda_esperada"] = r["valor_esperado"] * apostas  # negativo = perda
    if taxa_mensal is not None:
        r["custo_oportunidade"] = custo_oportunidade(valor, periodicidade, apostas, taxa_mensal)
    return r


# ----------------------------------------------------------------- Monte Carlo

def monte_carlo(valor, odd, prob, apostas, modo="fixo", banca=None, pct_banca=None,
                n_sim=10_000, semente=None, n_amostra=50):
    """Simula n_sim trajetórias (vetorizado). Retorna estatísticas e dados para gráficos.

    modo: "fixo" (R$ fixo), "percentual" (fração da banca atual; exige banca) ou
    "martingale" (dobra a stake após cada perda e volta à base após um acerto).
    Sem banca, o "saldo" é o resultado acumulado (começa em 0) e não há ruína.
    Com banca, quando o saldo não cobre a próxima stake a trajetória para: ruína.
    """
    if modo not in MODOS:
        raise ErroValidacao(f"Modo de aposta desconhecido: {modo}.")
    validar(odd=odd, prob=prob, apostas=apostas, banca=banca)
    if modo == "percentual":
        if not banca:
            raise ErroValidacao("Para apostar um percentual da banca, informe a banca inicial.")
        if pct_banca is None or not 0 < pct_banca <= 1:
            raise ErroValidacao("O percentual da banca deve estar entre 0% (exclusive) e 100%.")
    else:
        validar(valor=valor)
    n = int(apostas)
    rng = np.random.default_rng(semente)
    acertos = rng.random((n_sim, n)) < prob

    tem_banca = bool(banca)
    saldo = np.full(n_sim, float(banca) if tem_banca else 0.0)
    inicial = saldo[0]
    stake_base = valor
    stake_mart = np.full(n_sim, float(valor))
    pico = saldo.copy()
    dd_max = np.zeros(n_sim)
    ruina = np.zeros(n_sim, dtype=bool)
    total_apostado = np.zeros(n_sim)
    amostra = np.empty((min(n_amostra, n_sim), n + 1))
    amostra[:, 0] = saldo[:len(amostra)]
    faixa = np.empty((3, n + 1))  # P10, mediana, P90 em cada passo
    faixa[:, 0] = inicial

    for t in range(n):
        if modo == "percentual":
            stake = saldo * pct_banca
        elif modo == "martingale":
            stake = stake_mart
        else:
            stake = np.full(n_sim, float(stake_base))
        if tem_banca:
            ruina |= (saldo < stake) | (saldo <= 0.005)  # sem dinheiro para a próxima aposta
        joga = ~ruina
        stake = np.where(joga, stake, 0.0)
        ganho = np.where(acertos[:, t], stake * (odd - 1), -stake)
        saldo = saldo + ganho
        total_apostado += stake
        if modo == "martingale":
            stake_mart = np.where(acertos[:, t], float(stake_base), np.minimum(stake_mart * 2, 1e15))
        pico = np.maximum(pico, saldo)
        dd_max = np.maximum(dd_max, pico - saldo)
        amostra[:, t + 1] = saldo[:len(amostra)]
        faixa[:, t + 1] = np.percentile(saldo, [10, 50, 90])

    if tem_banca:
        ruina |= saldo <= 0.005
    p10, p50, p90 = np.percentile(saldo, [10, 50, 90])
    resultado = saldo - inicial
    return {
        "modo": modo,
        "n_sim": n_sim,
        "apostas": n,
        "banca": float(banca) if tem_banca else None,
        "saldo_final": saldo,
        "media": float(saldo.mean()),
        "mediana": float(p50),
        "p10": float(p10),
        "p90": float(p90),
        "resultado_medio": float(resultado.mean()),
        "prob_abaixo_inicial": float((resultado < 0).mean()),
        "prob_ruina": float(ruina.mean()) if tem_banca else None,
        "drawdown_medio": float(dd_max.mean()),
        "drawdown_maximo": float(dd_max.max()),
        "total_apostado_medio": float(total_apostado.mean()),
        "inicial": float(inicial),
        "amostra": amostra,
        "faixa": faixa,
    }


def comparar_padroes(valor, odd, prob, apostas, banca, n_sim=10_000, semente=None):
    """Tabela (lista de dicts) comparando stake fixa, percentual da banca e martingale.

    O percentual é escolhido para a primeira aposta ser igual à stake fixa.
    """
    validar(valor=valor, odd=odd, prob=prob, apostas=apostas, banca=banca)
    if not banca:
        raise ErroValidacao("A comparação de padrões precisa da banca inicial.")
    pct = min(valor / banca, 1.0)
    linhas = []
    for modo, nome in (("fixo", "Stake fixa"), ("percentual", "Percentual da banca"), ("martingale", "Martingale (dobra após perda)")):
        r = monte_carlo(valor, odd, prob, apostas, modo=modo, banca=banca, pct_banca=pct,
                        n_sim=n_sim, semente=semente, n_amostra=0)
        linhas.append({
            "Padrão": nome,
            "Resultado médio (R$)": r["resultado_medio"],
            "Mediana do saldo (R$)": r["mediana"],
            "P10 (R$)": r["p10"],
            "P90 (R$)": r["p90"],
            "Abaixo da banca inicial": r["prob_abaixo_inicial"],
            "Ruína / saldo insuficiente": r["prob_ruina"],
            "Drawdown máximo médio (R$)": r["drawdown_medio"],
        })
    return linhas


# ------------------------------------------------------- custo de oportunidade

def custo_oportunidade(valor, periodicidade, n_periodos, taxa_mensal_pct):
    """Total apostado x total acumulado se o mesmo fluxo fosse guardado a uma taxa mensal.

    taxa_mensal_pct em percentual ao mês (0,8 = 0,8% a.m.). Aportes no fim de cada período.
    """
    validar(valor=valor, apostas=n_periodos, taxa_mensal=taxa_mensal_pct / 100)
    if periodicidade not in PERIODOS_POR_MES:
        raise ErroValidacao("Periodicidade desconhecida.")
    n = int(n_periodos)
    r = (1 + taxa_mensal_pct / 100) ** (1 / PERIODOS_POR_MES[periodicidade]) - 1
    periodos = np.arange(0, n + 1)
    apostado = valor * periodos
    acumulado = valor * periodos if r == 0 else valor * ((1 + r) ** periodos - 1) / r
    return {
        "periodos": periodos,
        "apostado": apostado,
        "acumulado": acumulado,
        "total_apostado": float(apostado[-1]),
        "total_acumulado": float(acumulado[-1]),
        "rendimento": float(acumulado[-1] - apostado[-1]),
    }


# ---------------------------------------------- integração com o chat ([SIMULAR])

_RE_SIMULAR = re.compile(r"`{0,3}\[\s*SIMULAR\b([^\]]*)\]`{0,3}", re.IGNORECASE)
_CAMPOS = {"valor", "odd", "prob", "apostas", "taxa", "banca", "pct", "modo"}


def extrair_simular(texto):
    """Separa a linha [SIMULAR ...] do texto. Retorna (texto_limpo, params ou None).

    params: dict com valor, odd, prob (fração), apostas, taxa (% a.m.), banca, pct (fração), modo.
    Campos ausentes ou ilegíveis ficam de fora.
    """
    achados = _RE_SIMULAR.findall(texto)
    limpo = _RE_SIMULAR.sub("", texto).rstrip()
    if not achados:
        return texto, None
    params = {}
    for chave, bruto in re.findall(r"(\w+)\s*=\s*([^\s\]]+)", achados[-1]):
        chave = chave.lower()
        if chave not in _CAMPOS:
            continue
        bruto = bruto.strip(".,;")
        if chave == "modo":
            if bruto.lower() in MODOS:
                params["modo"] = bruto.lower()
            continue
        try:
            v = float(bruto.replace(",", "."))
        except ValueError:
            continue
        if chave in ("prob", "pct") and v > 1:  # o modelo às vezes escreve 40 em vez de 0.40
            v = v / 100
        if chave == "apostas":
            v = int(v)
        params[chave] = v
    return limpo, params or None

