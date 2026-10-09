"""Assistente educativo sobre apostas esportivas — abas Chat e Simulador."""
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

import llm
import simulador as sim

RAIZ = Path(__file__).parent
EXEMPLOS = [
    "Como funciona uma aposta esportiva?",
    "Se eu acertar mais da metade das minhas apostas, eu lucro?",
    "Vale a pena dobrar a aposta para recuperar o que perdi?",
    "Se eu apostar R$ 20 por rodada na odd 2,20 achando 40% de chance, quanto perco no campeonato?",
]
MODOS_UI = {"fixo": "Stake fixa (R$)", "percentual": "Percentual da banca", "martingale": "Martingale (dobrar após perda)"}
PERIODICIDADES = list(sim.PERIODOS_POR_MES)

st.set_page_config(page_title="Assistente educativo — apostas", page_icon="🎓", layout="wide")


# ------------------------------------------------------------------ utilidades

def brl(x):
    return "R$ " + f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl_md(x):
    """R$ para usar em markdown/caption (o Streamlit trata $...$ como fórmula)."""
    return brl(x).replace("$", "\\$")


def pc(x, casas=1):
    return f"{x * 100:.{casas}f}%".replace(".", ",")


@st.cache_data
def prompt_completo():
    prompt = (RAIZ / "prompt_sistema.md").read_text(encoding="utf-8")
    base = (RAIZ / "conhecimento" / "base.md").read_text(encoding="utf-8")
    return f"{prompt}\n\n# BASE DE CONHECIMENTO\n\n{base}"


@st.cache_data(show_spinner="Simulando 10.000 trajetórias…")
def rodar_mc(valor, odd, prob, apostas, modo, banca, pct, semente, rodada):
    return sim.monte_carlo(valor, odd, prob, apostas, modo=modo, banca=banca or None,
                           pct_banca=pct, semente=semente)


@st.cache_data
def rodar_comparacao(valor, odd, prob, apostas, banca, semente, rodada):
    return sim.comparar_padroes(valor, odd, prob, apostas, banca, semente=semente)


# ----------------------------------------------------- estado do simulador

PADROES = dict(sim_valor=50.0, sim_odd=1.80, sim_prob=50.0, sim_apostas=52, sim_modo="fixo",
               sim_pct=5.0, sim_banca=500.0, sim_semente=0, sim_taxa=0.8, sim_period="semanal", sim_rodada=0)
for k, v in PADROES.items():
    st.session_state[k] = st.session_state.get(k, v)  # reatribui: mantém o valor mesmo com a aba fechada
st.session_state.setdefault("mensagens", [])
st.session_state.setdefault("abas", "Chat")


def abrir_no_simulador(p):
    """Callback do botão do chat: copia os parâmetros da linha [SIMULAR] para a aba Simulador."""
    s = st.session_state
    if "valor" in p:
        s.sim_valor = float(p["valor"])
    elif "pct" in p and "banca" in p:
        s.sim_valor = float(p["pct"] * p["banca"])
    if "odd" in p:
        s.sim_odd = float(p["odd"])
    if "prob" in p:
        s.sim_prob = float(p["prob"] * 100)
    if "apostas" in p:
        s.sim_apostas = int(p["apostas"])
    if "taxa" in p:
        s.sim_taxa = float(p["taxa"])
    if "banca" in p:
        s.sim_banca = float(p["banca"])
    if "pct" in p:
        s.sim_pct = float(p["pct"] * 100)
    s.sim_modo = p.get("modo", "fixo")
    s.abas = "Simulador"


def pergunta_exemplo(texto):
    st.session_state.pendente = texto


# ------------------------------------------------------------------- Chat

def resumo_chat(p, chave):
    """Resumo calculado em Python (nunca pelo modelo) + botão para abrir o simulador."""
    valor = p.get("valor") or (p["pct"] * p["banca"] if "pct" in p and "banca" in p else None)
    minimo = valor is not None and all(k in p for k in ("odd", "prob", "apostas"))
    with st.container(border=True):
        if minimo:
            try:
                r = sim.resumo_cenario(valor, p["odd"], p["prob"], p["apostas"], p.get("taxa"))
            except sim.ErroValidacao as e:
                st.warning(str(e))
                r = None
            if r:
                st.markdown("**Resumo calculado pelo simulador** (hipóteses: apostas independentes, sem bônus nem impostos)")
                c = st.columns(5)
                c[0].metric("Prob. implícita da odd", pc(r["prob_implicita"], 2))
                c[1].metric("Lucro se acertar", brl(r["lucro_se_acertar"]))
                c[2].metric("Valor esperado por aposta", brl(r["valor_esperado"]))
                c[3].metric("Total apostado", brl(r["total_apostado"]))
                c[4].metric("Resultado esperado no período", brl(r["perda_esperada"]))
                if p.get("modo", "fixo") != "fixo":
                    st.caption("Resumo com a primeira aposta de valor fixo; o simulador mostra o modo escolhido.")
        else:
            st.caption("Ainda faltam dados para o resumo (valor, odd, probabilidade e número de apostas). "
                       "Você pode completá-los direto no simulador.")
        st.button("Abrir no simulador", key=chave, on_click=abrir_no_simulador, args=(p,))


def aba_chat():
    st.caption("Exemplos de perguntas:")
    cols = st.columns(len(EXEMPLOS))
    for i, ex in enumerate(EXEMPLOS):
        cols[i].button(ex, key=f"ex{i}", on_click=pergunta_exemplo, args=(ex,), width="stretch")

    pergunta = st.chat_input("Pergunte sobre odds, probabilidade, riscos...")
    pergunta = pergunta or st.session_state.pop("pendente", None)

    if pergunta:
        if llm.provedor() is None:
            st.warning("Chat indisponível: nenhuma chave de API configurada. Defina `GEMINI_API_KEY` (gratuita) ou "
                       "`ANTHROPIC_API_KEY` em `.streamlit/secrets.toml` ou como variável de ambiente. "
                       "A aba Simulador funciona normalmente.")
        else:
            st.session_state.mensagens.append({"role": "user", "content": pergunta})
            historico = [{"role": m["role"], "content": m["content"]} for m in st.session_state.mensagens]
            try:
                with st.spinner("Pensando…"):
                    bruto = llm.responder(historico, prompt_completo())
            except Exception as e:  # erro de rede, cota, chave inválida...
                st.session_state.mensagens.pop()
                st.error(f"Não consegui obter a resposta do modelo ({type(e).__name__}). "
                         "Verifique a chave de API, a cota e a conexão, e tente de novo.")
            else:
                texto, params = sim.extrair_simular(bruto)
                st.session_state.mensagens.append(
                    {"role": "assistant", "content": bruto, "texto": texto, "simular": params})

    for i, m in enumerate(st.session_state.mensagens):
        with st.chat_message(m["role"]):
            st.markdown(m.get("texto", m["content"]).replace("$", "\\$"))
            if m.get("simular"):
                resumo_chat(m["simular"], f"abrir_{i}")


# --------------------------------------------------------------- Simulador

def grafico_trajetorias(r):
    x = list(range(r["apostas"] + 1))
    fig = go.Figure()
    for linha in r["amostra"]:
        fig.add_scatter(x=x, y=linha, mode="lines", line=dict(width=1, color="rgba(130,130,130,0.35)"),
                        showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=x, y=r["faixa"][2], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=x, y=r["faixa"][0], mode="lines", line=dict(width=0), fill="tonexty",
                    fillcolor="rgba(31,119,180,0.20)", name="Faixa P10–P90")
    fig.add_scatter(x=x, y=r["faixa"][1], mode="lines", line=dict(width=3, color="#1f77b4"), name="Mediana")
    fig.add_hline(y=r["inicial"], line_dash="dash", line_color="gray", annotation_text="ponto de partida")
    fig.update_layout(title="50 trajetórias de exemplo e faixa de percentis", xaxis_title="Número da aposta",
                      yaxis_title="Saldo (R$)", margin=dict(t=50, b=10), legend=dict(orientation="h", y=-0.2))
    return fig


def grafico_histograma(r):
    fig = go.Figure(go.Histogram(x=r["saldo_final"], nbinsx=50, marker_color="#1f77b4"))
    fig.add_vline(x=r["inicial"], line_dash="dash", line_color="gray", annotation_text="ponto de partida")
    fig.add_vline(x=r["mediana"], line_color="#d62728", annotation_text="mediana", annotation_position="top left")
    fig.update_layout(title="Distribuição do saldo final (10.000 simulações)", xaxis_title="Saldo final (R$)",
                      yaxis_title="Nº de simulações", margin=dict(t=50, b=10))
    return fig


def grafico_oportunidade(c):
    fig = go.Figure()
    fig.add_scatter(x=c["periodos"], y=c["apostado"], mode="lines", name="Total apostado", line=dict(color="#d62728", width=3))
    fig.add_scatter(x=c["periodos"], y=c["acumulado"], mode="lines", name="Acumulado se fosse guardado",
                    line=dict(color="#2ca02c", width=3))
    fig.update_layout(title="Apostado x investido (mesmo fluxo)", xaxis_title="Período", yaxis_title="R$",
                      margin=dict(t=50, b=10), legend=dict(orientation="h", y=-0.2))
    return fig


def aba_simulador():
    s = st.session_state
    st.markdown("Ferramenta **educativa**: mostra o que os números dizem sobre um cenário **hipotético** que você define. "
                "Não prevê jogos nem indica em que apostar.")

    st.subheader("Entradas")
    c1, c2, c3, c4 = st.columns(4)
    c1.number_input("Valor por aposta (R$)", step=5.0, key="sim_valor")
    c2.number_input("Odd decimal", step=0.05, format="%.2f", key="sim_odd")
    c3.number_input("Sua probabilidade estimada de acerto (%)", step=1.0, key="sim_prob")
    c4.number_input("Número de apostas", step=1, key="sim_apostas")
    c1, c2, c3, c4 = st.columns(4)
    c1.selectbox("Regra de stake", list(MODOS_UI), format_func=MODOS_UI.get, key="sim_modo")
    c2.number_input("% da banca por aposta", step=1.0, key="sim_pct", disabled=s.sim_modo != "percentual")
    c3.number_input("Banca inicial (R$) — 0 = não informar", min_value=0.0, step=50.0, key="sim_banca")
    c4.number_input("Semente aleatória (0 = sem semente)", min_value=0, step=1, key="sim_semente",
                    help="Com a mesma semente, a simulação dá exatamente o mesmo resultado.")
    c1, c2, c3, _ = st.columns(4)
    c1.number_input("Taxa mensal da alternativa de investimento (%)", step=0.1, key="sim_taxa")
    c2.selectbox("Periodicidade das apostas", PERIODICIDADES, key="sim_period")
    c3.write("")
    if c3.button("Sortear de novo"):
        s.sim_rodada += 1

    valor, odd, prob = s.sim_valor, s.sim_odd, s.sim_prob / 100
    apostas, modo, banca = s.sim_apostas, s.sim_modo, s.sim_banca or None
    pct = s.sim_pct / 100
    semente = s.sim_semente or None

    # 1. Aposta única -----------------------------------------------------------
    st.subheader("1. Aposta única")
    if modo == "percentual":
        if not banca:
            st.error("Para apostar um percentual da banca, informe a banca inicial.")
            return
        valor = pct * banca  # stake da primeira aposta
    try:
        sim.validar(apostas=apostas, banca=banca)
        a = sim.aposta_unica(valor, odd, prob)
    except sim.ErroValidacao as e:
        st.error(str(e))
        return
    c = st.columns(5)
    c[0].metric("Probabilidade implícita (1/odd)", pc(a["prob_implicita"], 2))
    c[1].metric("Lucro se acertar", brl(a["lucro_se_acertar"]))
    c[2].metric("Perda se errar", brl(a["perda_se_errar"]))
    c[3].metric("Valor esperado por aposta", brl(a["valor_esperado"]))
    c[4].metric("Critério de Kelly", pc(a["kelly"], 1), help="Fração da banca que o critério indicaria. Fica em zero quando o valor esperado é negativo.")
    (st.info if a["valor_esperado"] > 0 else st.warning)(a["mensagem"])
    st.caption(f"Ponto de equilíbrio: com odd {odd:.2f}, você precisaria acertar {pc(a['prob_equilibrio'], 2)} das apostas só para empatar. "
               f"Total apostado se fizer {apostas} apostas: {brl_md(valor * apostas)} · resultado esperado: {brl_md(a['valor_esperado'] * apostas)}.")
    with st.expander("Como ler isso"):
        st.markdown(
            "- **Probabilidade implícita** = 1 ÷ odd. Já inclui a margem da casa, então não é a chance real do evento.\n"
            "- **Valor esperado** = valor × (probabilidade × odd − 1): o resultado médio de uma aposta se você a repetisse muitas vezes.\n"
            "- **Kelly** é uma fração teórica da banca; só é maior que zero se o valor esperado for positivo, "
            "o que depende inteiramente da sua estimativa de probabilidade.")

    # 2. Monte Carlo ------------------------------------------------------------
    st.subheader("2. Trajetórias possíveis (Monte Carlo)")
    try:
        r = rodar_mc(valor, odd, prob, apostas, modo, banca, pct, semente, s.sim_rodada)
    except sim.ErroValidacao as e:
        st.error(str(e))
        return
    ref = "Saldo final" if banca else "Resultado acumulado"
    c = st.columns(4)
    c[0].metric(f"{ref} — média", brl(r["media"]))
    c[1].metric("Mediana", brl(r["mediana"]))
    c[2].metric("P10 (cenário ruim)", brl(r["p10"]))
    c[3].metric("P90 (cenário bom)", brl(r["p90"]))
    c = st.columns(4)
    c[0].metric("Termina abaixo do ponto de partida", pc(r["prob_abaixo_inicial"]))
    c[1].metric("Ruína / saldo insuficiente", pc(r["prob_ruina"]) if r["prob_ruina"] is not None else "informe a banca")
    c[2].metric("Drawdown máximo (média)", brl(r["drawdown_medio"]), help="Maior queda a partir de um pico, em média nas simulações.")
    c[3].metric("Pior drawdown observado", brl(r["drawdown_maximo"]))
    st.plotly_chart(grafico_trajetorias(r), width="stretch")
    st.plotly_chart(grafico_histograma(r), width="stretch")
    st.warning("Percentis **não são garantia**: P10 e P90 só dizem onde caíram 10% e 90% das simulações, "
               "dadas as hipóteses acima. Uma sequência passada não muda a probabilidade da próxima aposta.")

    # 3. Comparação de padrões ----------------------------------------------------
    st.subheader("3. Comparando padrões de aposta")
    banca_comp = banca or valor * 20
    if not banca:
        st.caption(f"Sem banca informada, a comparação usa uma banca ilustrativa de {brl_md(banca_comp)} (20 × o valor da aposta).")
    try:
        linhas = rodar_comparacao(valor, odd, prob, apostas, banca_comp, semente, s.sim_rodada)
    except sim.ErroValidacao as e:
        st.error(str(e))
    else:
        tabela = [{k: v if k == "Padrão" else brl(v) if "R$" in k else pc(v) for k, v in l.items()} for l in linhas]
        st.dataframe(tabela, hide_index=True, width="stretch")
        st.caption("O percentual da banca é escolhido para a primeira aposta valer o mesmo que a stake fixa. "
                   "O martingale dobra a aposta após cada perda: o resultado médio continua negativo, e o risco de saldo insuficiente cresce.")

    # 4. Custo de oportunidade ----------------------------------------------------
    st.subheader("4. Custo de oportunidade")
    try:
        co = sim.custo_oportunidade(valor, s.sim_period, apostas, s.sim_taxa)
    except sim.ErroValidacao as e:
        st.error(str(e))
    else:
        c = st.columns(3)
        c[0].metric("Total apostado", brl(co["total_apostado"]))
        c[1].metric("Acumulado se fosse guardado", brl(co["total_acumulado"]))
        c[2].metric("Rendimento da alternativa", brl(co["rendimento"]))
        st.plotly_chart(grafico_oportunidade(co), width="stretch")
        st.caption(f"Considera {apostas} aportes {s.sim_period}s de {brl_md(valor)} a {str(s.sim_taxa).replace('.', ',')}% ao mês. "
                   "Não é recomendação de produto financeiro. Aposta não é investimento: o retorno esperado da aposta é negativo por causa da margem da casa.")

    # 5. Hipóteses ------------------------------------------------------------------
    with st.expander("Hipóteses e limites do modelo", expanded=True):
        st.markdown(
            "- As apostas são **independentes** e a odd e a probabilidade são **constantes**; isso pode falhar na prática.\n"
            "- Não há **bônus, promoções, impostos, limites da plataforma** nem custos de transação.\n"
            "- Sua probabilidade é um **cenário**, não uma previsão validada. Odds embutem margem e não revelam a probabilidade verdadeira.\n"
            "- **Sequência passada não muda p**: perder cinco vezes seguidas não torna a sexta mais provável.\n"
            "- **Martingale**: a banca é finita, as plataformas têm limite de aposta e dobrar não muda o valor esperado negativo.\n"
            "- Sem banca informada, o saldo mostrado é o resultado acumulado (começa em zero) e não há cálculo de ruína.")


# ----------------------------------------------------------------------- app

st.title("Assistente educativo sobre apostas esportivas")
st.info("🎓 **Ferramenta educativa.** Para maiores de 18 anos. Não damos palpites, não indicamos casas de apostas e não "
        "fazemos aconselhamento financeiro ou psicológico. Se apostar estiver pesando, procure um CAPS/SUS ou acesse "
        "gov.br/autoexclusaoapostas.")

aba_chat_, aba_sim_ = st.tabs(["Chat", "Simulador"], key="abas", on_change="rerun")
with aba_chat_:
    aba_chat()
with aba_sim_:
    aba_simulador()
