"""Cálculos do simulador de apostas (funções puras, sem Streamlit).

Convenções:
- odd decimal O (> 1), probabilidade p em [0, 1], stake s em R$.
- A chance de acerto NÃO é pedida ao usuário: ela sai da própria odd, tirando a
  margem da casa (overround). p = (1/O) / (1 + margem). Ex.: odd 1,80 e margem
  de 5% -> p = 55,56% / 1,05 = 52,91%. A margem pode vir de um valor de
  referência ou ser calculada com as três odds do jogo (1X2).
- taxa mensal em fração (0,008 = 0,8% ao mês) dentro das funções; a interface
  e a linha [SIMULAR ...] usam percentual (taxa=0.8).
- Hipóteses: apostas independentes, odd e p constantes, sem bônus nem impostos.
"""
import math
import re

import numpy as np

MAX_APOSTAS = 5000
MODOS = ("fixo", "percentual", "martingale")
PERIODOS_POR_MES = {"diária": 365 / 12, "semanal": 52 / 12, "quinzenal": 26 / 12, "mensal": 1.0}
# Margem de referência: próxima do exemplo da ficha sobre vantagem da casa
# (odds 2,10 / 3,40 / 3,60 -> soma 104,8%, margem de 4,8%). O usuário pode mudar.
MARGEM_PADRAO = 0.05
ODDS_EXEMPLO_1X2 = (2.10, 3.40, 3.60)


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


def _brl(x):
    return "R$ " + f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------------------------------------- chance de acerto a partir da odd

def margem_das_odds(odds):
    """Margem da casa (overround) de um mercado: soma de 1/odd de todos os resultados, menos 1.

    Ex.: (2,10; 3,40; 3,60) -> 47,6% + 29,4% + 27,8% = 104,8% -> margem de 4,8%.
    """
    odds = [float(o) for o in odds]
    if len(odds) < 2:
        raise ErroValidacao("Informe as odds de todos os resultados do jogo (no 1X2 são três).")
    for o in odds:
        validar(odd=o)
    margem = sum(1 / o for o in odds) - 1
    if margem < 0:
        raise ErroValidacao("Essas odds somam menos de 100%: confira se digitou as três odds do mesmo jogo.")
    return margem


def prob_justa(odd, margem=MARGEM_PADRAO):
    """Chance de acerto estimada a partir da odd, retirando a margem da casa.

    É a melhor estimativa neutra disponível sem palpite: a probabilidade implícita
    (1/odd) dividida pela soma do mercado (1 + margem).
    """
    validar(odd=odd)
    if margem is None or not 0 <= margem < 0.5:
        raise ErroValidacao("A margem da casa deve estar entre 0% e 50%.")
    return min((1 / odd) / (1 + margem), 1.0)


def retorno_por_100(odd, prob):
    """Quanto volta, em média, de cada R$ 100 apostados."""
    return 100 * prob * odd


# ---------------------------------------------------------------- aposta única

def aposta_unica(valor, odd, prob):
    """Probabilidade implícita, lucro, valor esperado, equilíbrio e Kelly de uma aposta."""
    validar(valor=valor, odd=odd, prob=prob)
    ve_unitario = prob * odd - 1  # VE por R$ 1 apostado
    ve = valor * ve_unitario
    kelly = ve_unitario / (odd - 1) if ve_unitario > 0 else 0.0
    prob_implicita = 1 / odd
    volta = retorno_por_100(odd, prob)
    if prob <= prob_implicita:
        mensagem = (
            f"A chance de acerto usada ({_pct(prob)}) é menor ou igual à chance que a odd paga "
            f"({_pct(prob_implicita)}). Por isso o valor esperado é negativo ou nulo: de cada R$ 100 "
            f"apostados, voltam em média {_brl(volta)}. A diferença é a margem da casa. "
            "Isso não é uma previsão do jogo, é a conta feita com as hipóteses do cenário."
        )
    else:
        mensagem = (
            f"A chance de acerto usada ({_pct(prob)}) é maior que a chance que a odd paga "
            f"({_pct(prob_implicita)}), então o valor esperado sai positivo. Isso só acontece se você "
            "estimar o jogo melhor do que a casa, de forma consistente e com folga para superar a margem. "
            "A estimativa é um cenário, não uma probabilidade verdadeira: se estiver otimista, a conta muda de sinal."
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
        "retorno_por_100": volta,
        "mensagem": mensagem,
    }


def resumo_cenario(valor, odd, prob, apostas, taxa_mensal=None, periodicidade="semanal",
                   margem=MARGEM_PADRAO):
    """Números analíticos de um cenário (usados no resumo do chat).

    prob=None -> a chance de acerto sai da odd sem a margem (prob_justa).
    """
    if prob is None:
        prob = prob_justa(odd, margem)
    r = aposta_unica(valor, odd, prob)
    r["prob"] = prob
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
    media_passo = np.empty(n + 1)  # média de todas as simulações em cada passo
    media_passo[0] = inicial

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
        media_passo[t + 1] = saldo.mean()

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
        "media_passo": media_passo,
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

def custo_oportunidade(valor, periodicidade, n_periodos, taxa_mensal_pct, fator_retorno=None):
    """Total apostado x total acumulado se o mesmo fluxo fosse guardado a uma taxa mensal.

    taxa_mensal_pct em percentual ao mês (0,8 = 0,8% a.m.). Aportes no fim de cada período.
    fator_retorno (opcional) = p x odd, quanto volta em média por R$ 1 apostado: gera a
    curva "apostando" (o que sobra, em média, se o mesmo dinheiro for apostado).
    """
    validar(valor=valor, apostas=n_periodos, taxa_mensal=taxa_mensal_pct / 100)
    if periodicidade not in PERIODOS_POR_MES:
        raise ErroValidacao("Periodicidade desconhecida.")
    n = int(n_periodos)
    r = (1 + taxa_mensal_pct / 100) ** (1 / PERIODOS_POR_MES[periodicidade]) - 1
    periodos = np.arange(0, n + 1)
    apostado = valor * periodos
    acumulado = valor * periodos if r == 0 else valor * ((1 + r) ** periodos - 1) / r
    saida = {
        "periodos": periodos,
        "apostado": apostado,
        "acumulado": acumulado,
        "total_apostado": float(apostado[-1]),
        "total_acumulado": float(acumulado[-1]),
        "rendimento": float(acumulado[-1] - apostado[-1]),
    }
    if fator_retorno is not None:
        apostando = apostado * fator_retorno
        saida["apostando"] = apostando
        saida["total_apostando"] = float(apostando[-1])
        saida["diferenca"] = float(acumulado[-1] - apostando[-1])
    return saida


# ---------------------------------------------- integração com o chat ([SIMULAR])

_RE_SIMULAR = re.compile(r"`{0,3}\[\s*SIMULAR\b([^\]]*)\]`{0,3}", re.IGNORECASE)
_CAMPOS = {"valor", "odd", "prob", "apostas", "taxa", "banca", "pct", "modo", "margem"}


def extrair_simular(texto):
    """Separa a linha [SIMULAR ...] do texto. Retorna (texto_limpo, params ou None).

    params: dict com valor, odd, apostas, taxa (% a.m.), banca, pct (fração), modo,
    margem (fração) e, só se o usuário insistir numa estimativa própria, prob (fração).
    Sem prob, o app calcula a chance a partir da odd sem a margem.
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
        if chave == "margem":  # sempre em percentual na linha (margem=4.8 -> 4,8%)
            v = v / 100 if v >= 0.5 else v
        if chave == "apostas":
            v = int(v)
        params[chave] = v
    return limpo, params or None



# ============================================================================
# Simulador para leigos (15/10/2026): cenário em linguagem do dia a dia,
# conta exata (binomial), "quanto mais tempo, mais gente perde", estratégias,
# jogo rodada a rodada e bilhete múltiplo.
# ============================================================================

# Tipos de aposta oferecidos na tela (odds ilustrativas, sem relação com jogos reais)
TIPOS_ODD = {"Favorito": 1.50, "Jogo equilibrado": 2.20, "Zebra": 5.00}
# Horizontes de tempo, em semanas
HORIZONTES = {"1 mês": 4, "3 meses": 13, "6 meses": 26, "1 Brasileirão": 38,
              "1 ano": 52, "2 anos": 104, "5 anos": 260}
APOSTAS_POR_SEMANA = (1, 2, 3, 5, 10)
# Rendimento de "guardar" (% ao mês, bruto). Referências consultadas em 16/10/2026:
# - Poupança: 0,6698% para depósitos com aniversário em 1º/10/2026 (taxas divulgadas pelo Banco Central).
# - Tesouro Selic / CDB 100% do CDI: Selic de 13,75% ao ano (Copom, 16/09/2026) -> (1,1375)^(1/12) - 1 = 1,08% ao mês.
TAXAS_GUARDAR = {
    "Poupança": (0.67, "0,67% ao mês: rendimento da poupança em outubro de 2026 (Banco Central)"),
    "Tesouro Selic ou CDB 100% do CDI": (1.08, "1,08% ao mês: equivale à Selic de 13,75% ao ano (Copom, 16/09/2026), antes do imposto de renda"),
}
TAXA_GUARDAR = TAXAS_GUARDAR["Poupança"][0]
MARGEM_MIN, MARGEM_MAX = 0.03, 0.12


def cenario_do_chat(apostas):
    """Converte um número de apostas em (apostas por semana, horizonte) mais próximo."""
    validar(apostas=apostas)
    melhor = min(((pw, nome) for pw in APOSTAS_POR_SEMANA for nome in HORIZONTES),
                 key=lambda c: (abs(c[0] * HORIZONTES[c[1]] - apostas), c[0]))
    return melhor


def distribuicao(valor, odd, prob, n):
    """Distribuição EXATA do resultado de n apostas iguais (número de acertos ~ Binomial(n, p)).

    Retorna chance de terminar no lucro / no prejuízo / empatado, perda média de quem perdeu,
    ganho médio de quem ganhou e o resultado médio (valor esperado).
    """
    validar(valor=valor, odd=odd, prob=prob, apostas=n)
    n = int(n)
    k = np.arange(n + 1)
    if prob <= 0:
        pmf = (k == 0).astype(float)
    elif prob >= 1:
        pmf = (k == n).astype(float)
    else:
        logc = np.array([math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) for i in k])
        logp = logc + k * math.log(prob) + (n - k) * math.log1p(-prob)
        pmf = np.exp(logp - logp.max())
        pmf /= pmf.sum()
    resultado = k * valor * (odd - 1) - (n - k) * valor
    lucro, perda = resultado > 1e-9, resultado < -1e-9
    p_lucro, p_perda = float(pmf[lucro].sum()), float(pmf[perda].sum())
    return {
        "apostas": n,
        "total_apostado": valor * n,
        "chance_lucro": p_lucro,
        "chance_perda": p_perda,
        "chance_empate": max(0.0, 1 - p_lucro - p_perda),
        "perda_media": float((resultado[perda] * pmf[perda]).sum() / p_perda) if p_perda > 0 else 0.0,
        "ganho_medio": float((resultado[lucro] * pmf[lucro]).sum() / p_lucro) if p_lucro > 0 else 0.0,
        "resultado_medio": float((resultado * pmf).sum()),
        "acertos_medios": n * prob,
    }


def pessoas_em_100(d):
    """Arredonda as chances para '100 pessoas' somando exatamente 100."""
    perderam = int(round(d["chance_perda"] * 100))
    ganharam = int(round(d["chance_lucro"] * 100))
    ganharam = min(ganharam, 100 - perderam)
    return {"perderam": perderam, "ganharam": ganharam, "empataram": 100 - perderam - ganharam}


def lucro_ao_longo_do_tempo(valor, odd, prob, por_semana, meses=60):
    """Mês a mês (1 a 'meses'), a chance EXATA de estar no lucro e o resultado médio.

    A chance oscila um pouco de um mês para outro (o número de acertos é inteiro), por isso
    também devolvemos a tendência: média móvel de 5 meses.
    """
    linhas = []
    for m in range(1, meses + 1):
        n = max(1, int(round(por_semana * m * 52 / 12)))
        if n > MAX_APOSTAS:
            break
        d = distribuicao(valor, odd, prob, n)
        linhas.append({"mes": m, "apostas": n, "chance_lucro": d["chance_lucro"],
                       "resultado_medio": d["resultado_medio"]})
    ch = np.array([l["chance_lucro"] for l in linhas])
    for i, l in enumerate(linhas):
        l["tendencia"] = float(ch[max(0, i - 2):i + 3].mean())
    return linhas


# ------------------------------------------------------------------ estratégias

ESTRATEGIAS = {
    "fixo": ("Sempre o mesmo valor", "Aposta sempre o mesmo valor, ganhando ou perdendo."),
    "martingale": ("Dobrar depois de perder", "Depois de cada derrota, dobra a aposta para recuperar tudo de uma vez."),
    "deixar_correr": ("Dobrar depois de ganhar", "Quando ganha, dobra a próxima aposta para aproveitar a \"boa fase\"."),
    "recuperar": ("Apostar alto para recuperar", "Quando está no prejuízo, aposta o necessário para zerar a perda numa vitória só."),
    "parar_no_lucro": ("Parar quando lucrar", "Aposta sempre o mesmo valor e para assim que alcança um lucro."),
    "limite_perda": ("Limite de perda", "Aposta sempre o mesmo valor e para quando a perda chega ao limite definido antes."),
}


def comparar_estrategias(valor, odd, prob, apostas, banca, meta=None, limite=None, n_sim=10_000, semente=None):
    """Simula as estratégias com OS MESMOS sorteios e devolve uma linha por estratégia.

    banca: dinheiro reservado. Ninguém aposta mais do que tem: se a aposta pedida passa do
    saldo, aposta o que sobrou; com saldo zerado, a pessoa 'perdeu tudo' e para.
    meta (parar no lucro) e limite (limite de perda) em R$; padrão: metade da banca.
    """
    validar(valor=valor, odd=odd, prob=prob, apostas=apostas, banca=banca)
    if not banca or banca < valor:
        raise ErroValidacao("O dinheiro reservado precisa ser pelo menos o valor de uma aposta.")
    meta = banca * 0.5 if meta is None else meta
    limite = banca * 0.5 if limite is None else limite
    n = int(apostas)
    acertos = np.random.default_rng(semente).random((n_sim, n)) < prob
    linhas = []
    for chave, (nome, descricao) in ESTRATEGIAS.items():
        saldo = np.full(n_sim, float(banca))
        ultima = np.full(n_sim, float(valor))
        ganhou_ultima = np.zeros(n_sim, dtype=bool)
        primeira = True
        parou = np.zeros(n_sim, dtype=bool)
        apostado = np.zeros(n_sim)
        for t in range(n):
            if chave == "martingale":
                stake = valor if primeira else np.where(ganhou_ultima, valor, ultima * 2)
            elif chave == "deixar_correr":
                stake = valor if primeira else np.where(ganhou_ultima, ultima * 2, valor)
            elif chave == "recuperar":
                deficit = banca - saldo
                stake = np.where(deficit > 0, np.maximum(valor, deficit / (odd - 1)), valor)
            else:
                stake = valor
            stake = np.broadcast_to(np.asarray(stake, dtype=float), (n_sim,))
            if chave == "parar_no_lucro":
                parou |= saldo - banca >= meta
            elif chave == "limite_perda":
                parou |= banca - saldo >= limite
            ativo = ~parou & (saldo > 0.005)
            stake = np.where(ativo, np.minimum(stake, saldo), 0.0)
            ganho = np.where(acertos[:, t], stake * (odd - 1), -stake)
            saldo = saldo + ganho
            apostado += stake
            ultima = np.where(ativo, stake, ultima)
            ganhou_ultima = np.where(ativo, acertos[:, t], ganhou_ultima)
            primeira = False
        resultado = saldo - banca
        linhas.append({
            "chave": chave, "nome": nome, "descricao": descricao,
            "resultado_medio": float(resultado.mean()),
            "perderam": float((resultado < -0.005).mean()),
            "ganharam": float((resultado > 0.005).mean()),
            "perderam_tudo": float((saldo <= 0.005).mean()),
            "apostado_medio": float(apostado.mean()),
            "retorno_por_100": float(100 * (1 + resultado.sum() / apostado.sum())) if apostado.sum() > 0 else 100.0,
        })
    return linhas


# ------------------------------------------------------------- bilhete múltiplo

def bilhete_multiplo(odd, jogos, margem=MARGEM_PADRAO):
    """Bilhete com 'jogos' palpites de mesma odd: odds se multiplicam, chances também.

    A margem também se multiplica: de cada R$ 100, voltam 100 / (1 + margem)^jogos.
    """
    validar(odd=odd)
    if int(jogos) != jogos or not 1 <= jogos <= 20:
        raise ErroValidacao("O bilhete deve ter de 1 a 20 jogos.")
    p = prob_justa(odd, margem)
    return {
        "jogos": int(jogos),
        "odd_total": odd ** jogos,
        "chance": p ** jogos,
        "chance_parece": (1 / odd) ** jogos,
        "retorno_por_100": 100 * (p * odd) ** jogos,
    }


# ------------------------------------------------------------- jogo rodada a rodada

def rodada_do_jogo(rng, odd, prob, valor, saldo, n_outros=1000):
    """Uma aposta do jogo: o resultado do usuário e o que a casa ganha com n_outros apostadores
    fazendo a mesma aposta ao mesmo tempo. Retorna (acertou, novo_saldo, ganho_da_casa)."""
    validar(odd=odd, prob=prob, valor=valor)
    if saldo < valor:
        raise ErroValidacao("Seu dinheiro do jogo acabou.")
    acertou = bool(rng.random() < prob)
    novo = saldo + (valor * (odd - 1) if acertou else -valor)
    acertos_outros = int(rng.binomial(n_outros, prob))
    casa = n_outros * valor - acertos_outros * valor * odd
    return acertou, novo, float(casa)


# ------------------------------------------------------------- calculadora de odds

def ler_odds(odds):
    """Para as odds de todos os resultados de um jogo: chance que cada odd 'paga' (1/odd), soma,
    margem da casa e a chance sem a margem (dividindo cada uma pela soma)."""
    margem = margem_das_odds(odds)
    impl = [1 / float(o) for o in odds]
    soma = sum(impl)
    return {"implicitas": impl, "soma": soma, "margem": margem, "justas": [i / soma for i in impl]}


# ------------------------------------------------------------- reapostar o que volta

def reapostar(deposito, fator_retorno, fracao):
    """Média do que acontece quando, do dinheiro que volta das apostas, a pessoa reaposta 'fracao'
    (0 = saca tudo, 1 = reaposta tudo até acabar).

    Cada R$ 1 apostado devolve, em média, fator_retorno (= p x odd, ex.: 0,9524). Somando a série:
    total apostado = depósito / (1 - fracao x r) e sobra = depósito x (1 - fracao) x r / (1 - fracao x r).
    """
    if not 0 <= fracao <= 1:
        raise ErroValidacao("A fração reapostada deve estar entre 0 e 1.")
    if not 0 < fator_retorno < 1:
        raise ErroValidacao("O retorno médio por real apostado deve estar entre 0 e 1 (há margem da casa).")
    validar(valor=deposito)
    q = fracao * fator_retorno
    apostado = deposito / (1 - q)
    sobra = deposito * (1 - fracao) * fator_retorno / (1 - q)
    return {"depositado": deposito, "apostado": apostado, "vezes": apostado / deposito, "sobra": sobra,
            "perda": deposito - sobra}
