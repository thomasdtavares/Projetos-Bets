"""Assistente educativo sobre apostas esportivas — abas Chat e Simulador."""
from pathlib import Path

import pandas  # noqa: F401  (importado cedo para evitar corrida de import entre execuções do script)
import plotly.graph_objects as go
import streamlit as st

import llm
import simulador as sim

RAIZ = Path(__file__).parent
EXEMPLOS = [
    "Como funciona uma aposta esportiva?",
    "Se eu acertar mais da metade das minhas apostas, eu lucro?",
    "Vale a pena dobrar a aposta para recuperar o que perdi?",
    "Se eu apostar R$ 20 por rodada do Brasileirão numa odd 2,20, quanto isso pode custar?",
]
MODOS_UI = {"fixo": "Mesmo valor sempre", "percentual": "Uma % do que eu tenho", "martingale": "Dobrar depois de perder"}
FONTES_UI = {
    "margem": "Tirar da odd (margem de referência)",
    "tres": "Calcular a margem com as 3 odds do jogo",
    "propria": "Testar uma chance minha",
}
PERIODICIDADES = list(sim.PERIODOS_POR_MES)

# Cores (paleta de referência validada: azul/vermelho como par de polaridade, cinza neutro)
AZUL, AZUL_CLARO = "#2a78d6", "rgba(42,120,214,0.16)"
VERMELHO, VERMELHO_CLARO = "#e34948", "rgba(227,73,72,0.16)"
LARANJA = "#eb6834"
CINZA, CINZA_TEXTO, TINTA = "#b9b7b0", "#6b6a66", "#1f1e1c"
GRADE = "#ecebe7"

st.set_page_config(page_title="Bets: os números", page_icon="🎓", layout="wide",
                   initial_sidebar_state="collapsed")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, .stApp { font-family: 'Inter', system-ui, sans-serif; }
.block-container { max-width: 1100px; padding-top: 2rem; }
h1, h2, h3 { letter-spacing: -0.01em; }

.hero { background: linear-gradient(135deg, #0f2f57 0%, #2a78d6 100%); color: #fff; border-radius: 18px;
        padding: 26px 30px; margin-bottom: 14px; }
.hero h1 { color: #fff; font-size: 1.9rem; font-weight: 700; margin: 0 0 6px 0; padding: 0; }
.hero p { color: #dce9fa; margin: 0; font-size: 1.02rem; }
.selo { display: inline-block; background: rgba(255,255,255,0.16); color: #fff; border-radius: 999px;
        padding: 3px 12px; font-size: 0.8rem; margin-bottom: 10px; font-weight: 500; }

.aviso { background: #f3f2ee; border-radius: 12px; padding: 10px 16px; font-size: 0.88rem; color: #52514e;
         margin-bottom: 8px; }
.aviso b { color: #1f1e1c; }

.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid #ecebe7; }
.stTabs [data-baseweb="tab"] { height: 44px; padding: 0 18px; font-weight: 600; font-size: 1rem; }

[data-testid="stMetric"] { background: #fff; border: 1px solid #ecebe7; border-radius: 14px; padding: 14px 16px; }
[data-testid="stMetricLabel"] p { color: #6b6a66; font-size: 0.85rem; }
[data-testid="stMetricValue"] { font-size: 1.45rem; font-weight: 650; }

[data-testid="stChatMessage"] { border-radius: 16px; padding: 14px 18px; }

.destaque { background: #fff; border: 1px solid #ecebe7; border-left: 6px solid #e34948; border-radius: 14px;
            padding: 18px 22px; margin: 6px 0 14px 0; }
.destaque.positivo { border-left-color: #2a78d6; }
.destaque .grande { font-size: 1.55rem; font-weight: 700; color: #1f1e1c; line-height: 1.25; }
.destaque .peq { color: #52514e; margin-top: 6px; font-size: 0.95rem; }

.chance { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 10px 0; }
.chip { background: #f3f2ee; border-radius: 999px; padding: 5px 12px; font-size: 0.86rem; color: #1f1e1c; }
.chip b { font-weight: 650; }

.passo { font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; color: #2a78d6; text-transform: uppercase;
         margin: 18px 0 0 0; }
</style>
"""


# ------------------------------------------------------------------ utilidades

def brl(x):
    sinal = "−" if round(x, 2) < 0 else ""
    return sinal + "R$ " + f"{abs(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl_md(x):
    """R$ para usar em markdown/caption (o Streamlit trata $...$ como fórmula)."""
    return brl(x).replace("$", "\\$")


def brl_html(x):
    return brl(x).replace("$", "&#36;")


def pc(x, casas=1):
    return f"{x * 100:.{casas}f}%".replace(".", ",")


def num(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",")


@st.cache_data
def prompt_completo():
    prompt = (RAIZ / "prompt_sistema.md").read_text(encoding="utf-8")
    base = (RAIZ / "conhecimento" / "base.md").read_text(encoding="utf-8")
    return f"{prompt}\n\n# BASE DE CONHECIMENTO\n\n{base}"


@st.cache_data(show_spinner="Simulando 10.000 sequências de apostas…")
def rodar_mc(valor, odd, prob, apostas, modo, banca, pct, semente, rodada):
    return sim.monte_carlo(valor, odd, prob, apostas, modo=modo, banca=banca or None,
                           pct_banca=pct, semente=semente)


@st.cache_data
def rodar_comparacao(valor, odd, prob, apostas, banca, semente, rodada):
    return sim.comparar_padroes(valor, odd, prob, apostas, banca, semente=semente)


# ----------------------------------------------------- estado do simulador

o1, o2, o3 = sim.ODDS_EXEMPLO_1X2
PADROES = dict(sim_valor=50.0, sim_odd=1.80, sim_apostas=52, sim_period="semanal", sim_fonte="margem",
               sim_margem=sim.MARGEM_PADRAO * 100, sim_o1=o1, sim_o2=o2, sim_o3=o3, sim_prob=50.0,
               sim_modo="fixo", sim_pct=5.0, sim_banca=0.0, sim_semente=0, sim_taxa=0.8, sim_rodada=0)
for k, v in PADROES.items():
    st.session_state[k] = st.session_state.get(k, v)  # reatribui: mantém o valor mesmo com a aba fechada
st.session_state.setdefault("mensagens", [])
st.session_state.setdefault("abas", "Conversa")


def abrir_no_simulador(p):
    """Callback do botão do chat: copia os parâmetros da linha [SIMULAR] para a aba Simulador."""
    s = st.session_state
    if "valor" in p:
        s.sim_valor = float(p["valor"])
    elif "pct" in p and "banca" in p:
        s.sim_valor = float(p["pct"] * p["banca"])
    if "odd" in p:
        s.sim_odd = float(p["odd"])
    if "apostas" in p:
        s.sim_apostas = int(p["apostas"])
    if "taxa" in p:
        s.sim_taxa = float(p["taxa"])
    if "banca" in p:
        s.sim_banca = float(p["banca"])
    if "pct" in p:
        s.sim_pct = float(p["pct"] * 100)
    if "prob" in p:
        s.sim_fonte, s.sim_prob = "propria", float(p["prob"] * 100)
    else:
        s.sim_fonte = "margem"
        s.sim_margem = float(p.get("margem", sim.MARGEM_PADRAO) * 100)
    s.sim_modo = p.get("modo", "fixo")
    s.abas = "Simulador"


def pergunta_exemplo(texto):
    st.session_state.pendente = texto


def limpar_conversa():
    st.session_state.mensagens = []


# ------------------------------------------------------------------ gráficos

def estilo(fig, titulo, x, y, altura=380):
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=16, color=TINTA), x=0, xanchor="left"),
        height=altura, margin=dict(t=88, b=8, l=8, r=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=CINZA_TEXTO, size=13),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(color=TINTA)),
        hoverlabel=dict(bgcolor="#fff", bordercolor=GRADE, font=dict(color=TINTA)),
        separators=",.",
    )
    fig.update_xaxes(title=x, gridcolor=GRADE, zeroline=False, showline=True, linecolor=GRADE)
    fig.update_yaxes(title=y, gridcolor=GRADE, zeroline=False, tickprefix="R$ ", separatethousands=True)
    return fig


def grafico_para_onde_vai(volta):
    """Barra única: de cada R$ 100, quanto volta e quanto fica com a casa."""
    fica = 100 - volta
    fig = go.Figure()
    fig.add_bar(y=[""], x=[volta], orientation="h", marker_color=AZUL, name="Volta para você (em média)",
                text=[f"volta {brl(volta)}"], textposition="inside", insidetextanchor="start",
                hovertemplate="Volta em média: R$ %{x:.2f}<extra></extra>")
    if fica > 0:
        fig.add_bar(y=[""], x=[fica], orientation="h", marker_color=VERMELHO, name="Fica com a casa",
                    text=[f"casa {brl(fica)}"], textposition="outside",
                    hovertemplate="Fica com a casa: R$ %{x:.2f}<extra></extra>")
    fig.update_layout(barmode="stack", height=120, margin=dict(t=8, b=8, l=8, r=90), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, system-ui, sans-serif", color="#fff", size=14),
                      bargap=0.15, separators=",.")
    fig.update_traces(selector=dict(name="Fica com a casa"), textfont_color=VERMELHO)
    fig.update_xaxes(visible=False, range=[0, max(100, volta) * 1.12])
    fig.update_yaxes(visible=False)
    return fig


def grafico_trajetorias(r):
    x = list(range(r["apostas"] + 1))
    ini = r["inicial"]
    fig = go.Figure()
    # algumas sequências individuais, coloridas pelo resultado final
    vistos = set()
    for linha in r["amostra"][:30]:
        acima = linha[-1] >= ini
        cor = "rgba(42,120,214,0.30)" if acima else "rgba(227,73,72,0.28)"
        nome = "Uma sequência que terminou no lucro" if acima else "Uma sequência que terminou no prejuízo"
        fig.add_scatter(x=x, y=linha, mode="lines", line=dict(width=1.2, color=cor), name=nome,
                        showlegend=nome not in vistos, legendgroup=nome, hoverinfo="skip")
        vistos.add(nome)
    fig.add_scatter(x=x, y=r["media_passo"], mode="lines", line=dict(width=3.5, color=TINTA),
                    name="Média de todas as 10.000 simulações",
                    hovertemplate="Depois de %{x} apostas<br>Média: R$ %{y:,.2f}<extra></extra>")
    fig.add_hline(y=ini, line_dash="dot", line_color=CINZA_TEXTO, line_width=1.5,
                  annotation_text="ponto de partida", annotation_position="bottom left",
                  annotation_font_color=CINZA_TEXTO)
    return estilo(fig, "Como o saldo pode evoluir, aposta a aposta", "Número da aposta",
                  "Saldo" if r["banca"] else "Ganho ou perda acumulada", altura=440)


def grafico_histograma(r):
    import numpy as np
    finais = np.round(r["saldo_final"] - r["inicial"], 2)
    valores, contagem = np.unique(finais, return_counts=True)
    largura = None
    if len(valores) > 80:  # resultados contínuos (percentual/martingale): agrupa em faixas
        contagem, bordas = np.histogram(finais, bins=40)
        valores, largura = (bordas[:-1] + bordas[1:]) / 2, (bordas[1] - bordas[0]) * 0.9
    elif len(valores) > 1:
        largura = np.min(np.diff(valores)) * 0.8
    cores = [VERMELHO if v < 0 else AZUL for v in valores]
    fig = go.Figure(go.Bar(x=valores, y=contagem / len(finais) * 100, width=largura, marker_color=cores,
                           marker_line_width=0, showlegend=False,
                           hovertemplate="Resultado ≈ R$ %{x:,.2f}<br>%{y:.1f}% das simulações<extra></extra>"))
    fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(color=VERMELHO, size=10, symbol="square"),
                    name=f"Terminou no prejuízo ({pc(r['prob_abaixo_inicial'])})")
    fig.add_scatter(x=[None], y=[None], mode="markers", marker=dict(color=AZUL, size=10, symbol="square"),
                    name=f"Terminou empatado ou no lucro ({pc(1 - r['prob_abaixo_inicial'])})")
    fig.add_vline(x=0, line_dash="dot", line_color=CINZA_TEXTO)
    fig = estilo(fig, "Como terminaram as 10.000 simulações", "Ganho ou perda no fim do período", "")
    fig.update_xaxes(tickprefix="R$ ", separatethousands=True)
    fig.update_yaxes(title="% das simulações", tickprefix="", ticksuffix="%")
    return fig


def grafico_oportunidade(c):
    x = c["periodos"]
    fig = go.Figure()
    fig.add_scatter(x=x, y=c["apostado"], mode="lines", name="Dinheiro que você separou",
                    line=dict(color=CINZA, width=2, dash="dot"),
                    hovertemplate="Separado: R$ %{y:,.2f}<extra></extra>")
    fig.add_scatter(x=x, y=c["acumulado"], mode="lines", name="Se fosse guardado (rendendo)",
                    line=dict(color=AZUL, width=3), hovertemplate="Guardado: R$ %{y:,.2f}<extra></extra>")
    if "apostando" in c:
        fig.add_scatter(x=x, y=c["apostando"], mode="lines", name="Se fosse apostado (o que volta, em média)",
                        line=dict(color=VERMELHO, width=3), fill="tonexty", fillcolor="rgba(227,73,72,0.08)",
                        hovertemplate="Apostando: R$ %{y:,.2f}<extra></extra>")
        fig.add_annotation(x=x[-1], y=(c["acumulado"][-1] + c["apostando"][-1]) / 2, xanchor="left",
                           text=f"diferença<br><b>{brl(c['diferenca'])}</b>", showarrow=False,
                           font=dict(color=TINTA, size=13), xshift=6)
    fig = estilo(fig, "Guardar ou apostar o mesmo dinheiro", "", "", altura=400)
    fig.update_layout(hovermode="x unified", margin=dict(r=100))
    return fig


def grafico_comparacao(linhas):
    nomes = [l["Padrão"] for l in linhas]
    ruina = [l["Ruína / saldo insuficiente"] * 100 for l in linhas]
    fig = go.Figure(go.Bar(x=ruina, y=nomes, orientation="h", marker_color=[AZUL, LARANJA, VERMELHO],
                           text=[pc(v / 100) for v in ruina], textposition="outside",
                           hovertemplate="%{y}: %{x:.1f}%<extra></extra>"))
    fig = estilo(fig, "Chance de o dinheiro acabar antes do fim", "", "", altura=230)
    fig.update_xaxes(ticksuffix="%", range=[0, max(ruina + [10]) * 1.25], title="")
    fig.update_yaxes(tickprefix="", autorange="reversed", gridcolor="rgba(0,0,0,0)")
    return fig


# ------------------------------------------------------------------- Chat

def resumo_chat(p, chave):
    """Resumo calculado em Python (nunca pelo modelo) + botão para abrir o simulador."""
    valor = p.get("valor") or (p["pct"] * p["banca"] if "pct" in p and "banca" in p else None)
    minimo = valor is not None and all(k in p for k in ("odd", "apostas"))
    with st.container(border=True):
        if minimo:
            try:
                r = sim.resumo_cenario(valor, p["odd"], p.get("prob"), p["apostas"], p.get("taxa"),
                                       margem=p.get("margem", sim.MARGEM_PADRAO))
            except sim.ErroValidacao as e:
                st.warning(str(e))
                r = None
            if r:
                origem = "a sua estimativa" if "prob" in p else "a chance que a odd indica, sem a margem da casa"
                st.markdown(f"**📊 Conta feita pelo simulador** · usando {origem}")
                c = st.columns(4)
                c[0].metric("Chance de acertar cada aposta", pc(r["prob"]))
                c[1].metric("De cada R$ 100, voltam", brl(r["retorno_por_100"]))
                c[2].metric("Total apostado", brl(r["total_apostado"]))
                c[3].metric("Resultado esperado no período", brl(r["perda_esperada"]))
                if p.get("modo", "fixo") != "fixo":
                    st.caption("Resumo com apostas de valor fixo; o simulador mostra a forma escolhida.")
        else:
            st.caption("Ainda faltam dados para a conta (valor, odd e número de apostas). "
                       "Você pode completá-los direto no simulador.")
        st.button("Abrir no simulador →", key=chave, on_click=abrir_no_simulador, args=(p,), type="primary")


def aba_chat():
    pergunta = st.chat_input("Pergunte sobre odds, chances, riscos, quanto custa apostar…")
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

    if not st.session_state.mensagens:
        with st.chat_message("assistant", avatar="🎓"):
            st.markdown("Oi! Eu explico **como as apostas funcionam por dentro**: o que a odd quer dizer, por que a "
                        "casa sempre leva uma parte e quanto apostar pode custar ao longo do tempo. "
                        "Não dou palpites. Comece por uma destas perguntas ou escreva a sua:")
            c = st.columns(2)
            for i, ex in enumerate(EXEMPLOS):
                c[i % 2].button(ex.replace("$", "\\$"), key=f"ex{i}", on_click=pergunta_exemplo, args=(ex,),
                                width="stretch")

    for i, m in enumerate(st.session_state.mensagens):
        avatar = "🎓" if m["role"] == "assistant" else "🙂"
        with st.chat_message(m["role"], avatar=avatar):
            st.markdown(m.get("texto", m["content"]).replace("$", "\\$"))
            if m.get("simular"):
                resumo_chat(m["simular"], f"abrir_{i}")

    if st.session_state.mensagens:
        st.button("Limpar conversa", on_click=limpar_conversa, type="tertiary", icon=":material/refresh:")


# --------------------------------------------------------------- Simulador

def chance_de_acerto(s, odd):
    """Retorna (prob, margem, texto da origem) conforme a fonte escolhida. Pode lançar ErroValidacao."""
    if s.sim_fonte == "propria":
        p = s.sim_prob / 100
        sim.validar(prob=p)
        return p, None, "sua estimativa"
    if s.sim_fonte == "tres":
        margem = sim.margem_das_odds([s.sim_o1, s.sim_o2, s.sim_o3])
    else:
        margem = s.sim_margem / 100
    return sim.prob_justa(odd, margem), margem, "odd sem a margem"


def aba_simulador():
    s = st.session_state
    st.markdown("Monte um **cenário imaginário** e veja o que os números dizem. Não é previsão de jogo nem "
                "indicação de aposta.")

    # --- 1. Cenário ---------------------------------------------------------------------
    st.markdown('<p class="passo">Passo 1</p>', unsafe_allow_html=True)
    st.subheader("Seu cenário", anchor=False)
    c1, c2, c3, c4 = st.columns(4)
    c1.number_input("Valor de cada aposta (R$)", min_value=0.0, step=5.0, key="sim_valor")
    c2.number_input("Odd", min_value=1.0, step=0.05, format="%.2f", key="sim_odd",
                    help="O número ao lado da opção na casa de apostas. Odd 1,80: R$ 10 viram R$ 18 se você acertar.")
    c3.selectbox("Com que frequência", PERIODICIDADES, key="sim_period")
    c4.number_input("Quantas apostas no total", min_value=1, step=1, key="sim_apostas",
                    help="Exemplos: 1 por semana durante um ano = 52; uma por rodada do Brasileirão = 38.")

    with st.container(border=True):
        st.markdown("**Qual a chance de acertar cada aposta?** Ninguém sabe ao certo, e não pedimos o seu palpite. "
                    "Usamos o que a própria odd indica, tirando a parte que a casa cobra (a margem).")
        st.radio("Como calcular", list(FONTES_UI), format_func=FONTES_UI.get, key="sim_fonte", horizontal=True,
                 label_visibility="collapsed")
        if s.sim_fonte == "margem":
            st.slider("Margem da casa (%)", 0.0, 15.0, step=0.5, key="sim_margem", format="%.1f%%",
                      help="Quanto a soma das chances de um jogo passa de 100%. O padrão de 5% é próximo do "
                           "exemplo da nossa base (odds 2,10 / 3,40 / 3,60 somam 104,8%).")
        elif s.sim_fonte == "tres":
            t1, t2, t3 = st.columns(3)
            t1.number_input("Odd do mandante", min_value=1.0, step=0.05, format="%.2f", key="sim_o1")
            t2.number_input("Odd do empate", min_value=1.0, step=0.05, format="%.2f", key="sim_o2")
            t3.number_input("Odd do visitante", min_value=1.0, step=0.05, format="%.2f", key="sim_o3")
            st.caption("Digite as três odds do mesmo jogo. A soma das chances (1 ÷ odd) menos 100% é a margem.")
        else:
            st.slider("Chance que você quer testar (%)", 0.0, 100.0, step=1.0, key="sim_prob", format="%.0f%%")
            st.caption("Só para comparar: quem acha que acerta mais que a odd indica precisa estar certo de forma "
                       "consistente, e com folga para vencer a margem.")

    with st.expander("Opções avançadas"):
        a1, a2, a3 = st.columns(3)
        a1.selectbox("Como define o valor de cada aposta", list(MODOS_UI), format_func=MODOS_UI.get, key="sim_modo")
        a2.number_input("Se for %: quanto do que você tem (%)", min_value=0.0, step=1.0, key="sim_pct",
                        disabled=s.sim_modo != "percentual")
        a3.number_input("Dinheiro reservado para apostar (R$)", min_value=0.0, step=50.0, key="sim_banca",
                        help="Opcional (0 = não informar). Com ele, o simulador calcula a chance de o dinheiro acabar.")
        b1, b2, b3 = st.columns(3)
        b1.number_input("Rendimento mensal se guardasse (%)", step=0.1, key="sim_taxa", format="%.2f")
        b2.number_input("Semente (0 = aleatória)", min_value=0, step=1, key="sim_semente",
                        help="Com a mesma semente, a simulação repete exatamente o mesmo resultado.")
        b3.write("")
        if b3.button("Simular de novo", icon=":material/casino:"):
            s.sim_rodada += 1

    valor, odd, apostas = s.sim_valor, s.sim_odd, s.sim_apostas
    modo, banca, pct = s.sim_modo, s.sim_banca or None, s.sim_pct / 100
    semente = s.sim_semente or None
    if modo == "percentual":
        if not banca:
            st.error("Para apostar uma % do que você tem, informe o dinheiro reservado nas opções avançadas.")
            return
        valor = pct * banca  # valor da primeira aposta
    try:
        sim.validar(valor=valor, odd=odd, apostas=apostas, banca=banca)
        prob, margem, origem = chance_de_acerto(s, odd)
        a = sim.aposta_unica(valor, odd, prob)
        r = rodar_mc(valor, odd, prob, apostas, modo, banca, pct, semente, s.sim_rodada)
    except sim.ErroValidacao as e:
        st.error(str(e))
        return

    chips = [f"Chance usada: <b>{pc(prob)}</b> ({origem})",
             f"A odd {num(odd)} paga como se fosse <b>{pc(a['prob_implicita'])}</b>"]
    if margem is not None:
        chips.append(f"Margem da casa: <b>{pc(margem)}</b>")
    st.markdown('<div class="chance">' + "".join(f'<span class="chip">{c}</span>' for c in chips) + "</div>",
                unsafe_allow_html=True)

    # --- 2. Conta média -------------------------------------------------------------------
    st.markdown('<p class="passo">Passo 2</p>', unsafe_allow_html=True)
    st.subheader("A conta, em média", anchor=False)
    volta = a["retorno_por_100"]
    positivo = a["valor_esperado"] > 0
    total_medio = a["valor_esperado"] * apostas
    frase = (f"De cada {brl_html(100)} apostados, voltam em média {brl_html(volta)}."
             if not positivo else f"De cada {brl_html(100)} apostados, voltariam em média {brl_html(volta)}.")
    detalhe = (f"Em {apostas} apostas de {brl_html(valor)}, isso dá um resultado médio de "
               f"<b>{brl_html(total_medio)}</b>. Não é o que vai acontecer com você: é o centro de todas as "
               "possibilidades, como mostra o passo 3.")
    if positivo:
        detalhe += " Atenção: só sai positivo porque a chance testada é maior que a que a odd indica."
    st.markdown(f'<div class="destaque{" positivo" if positivo else ""}"><div class="grande">{frase}</div>'
                f'<div class="peq">{detalhe}</div></div>', unsafe_allow_html=True)
    st.plotly_chart(grafico_para_onde_vai(volta), width="stretch", config={"displayModeBar": False})
    c = st.columns(3)
    c[0].metric("Total apostado", brl(valor * apostas) if modo == "fixo" else brl(r["total_apostado_medio"]),
                help="Na forma 'dobrar' ou '%', é a média das simulações.")
    c[1].metric("Resultado médio no total", brl(total_medio if modo == "fixo" else r["resultado_medio"]))
    c[2].metric("Ponto de equilíbrio", pc(a["prob_equilibrio"]),
                help="Você precisaria acertar mais do que isso, sempre, só para empatar.")

    # --- 3. Possibilidades ----------------------------------------------------------------
    st.markdown('<p class="passo">Passo 3</p>', unsafe_allow_html=True)
    st.subheader("E na prática? 10.000 versões possíveis", anchor=False)
    st.markdown(f"Repetimos as suas {apostas} apostas 10.000 vezes. Em cada uma, o acaso decide acertos e erros "
                "com a chance acima.")
    c = st.columns(4 if r["prob_ruina"] is not None else 3)
    c[0].metric("Terminam no prejuízo", pc(r["prob_abaixo_inicial"]))
    c[1].metric("Resultado ruim (1 em 10)", brl(r["p10"] - r["inicial"]),
                help="Em 9 de cada 10 simulações o resultado foi melhor que este.")
    c[2].metric("Resultado bom (1 em 10)", brl(r["p90"] - r["inicial"]),
                help="Em 9 de cada 10 simulações o resultado foi pior que este.")
    if r["prob_ruina"] is not None:
        c[3].metric("Dinheiro acaba antes do fim", pc(r["prob_ruina"]))
    st.plotly_chart(grafico_trajetorias(r), width="stretch")
    st.plotly_chart(grafico_histograma(r), width="stretch")
    st.caption("Estes números não são garantia: mostram o que aconteceu nas simulações, com as hipóteses acima. "
               "Perder várias vezes seguidas não aumenta a chance de ganhar na próxima.")

    # --- 4. Comparações -------------------------------------------------------------------
    st.markdown('<p class="passo">Passo 4</p>', unsafe_allow_html=True)
    st.subheader("Comparações", anchor=False)
    t1, t2 = st.tabs(["Guardar em vez de apostar", "Dobrar depois de perder"])
    with t1:
        try:
            co = sim.custo_oportunidade(valor, s.sim_period, apostas, s.sim_taxa, fator_retorno=prob * odd)
        except sim.ErroValidacao as e:
            st.error(str(e))
        else:
            c = st.columns(3)
            c[0].metric("Guardando, você teria", brl(co["total_acumulado"]))
            c[1].metric("Apostando, voltariam em média", brl(co["total_apostando"]))
            c[2].metric("Diferença", brl(co["diferenca"]))
            st.plotly_chart(grafico_oportunidade(co), width="stretch")
            st.caption(f"{apostas} valores de {brl_md(valor)} ({s.sim_period}) rendendo "
                       f"{num(s.sim_taxa)}% ao mês (mude nas opções avançadas). Não é recomendação de investimento.")
    with t2:
        banca_comp = banca or valor * 20
        if not banca:
            st.caption(f"Sem dinheiro reservado informado, usamos {brl_md(banca_comp)} (20 vezes o valor da aposta).")
        try:
            linhas = rodar_comparacao(valor, odd, prob, apostas, banca_comp, semente, s.sim_rodada)
        except sim.ErroValidacao as e:
            st.error(str(e))
        else:
            nomes = {"Stake fixa": MODOS_UI["fixo"], "Percentual da banca": MODOS_UI["percentual"],
                     "Martingale (dobra após perda)": MODOS_UI["martingale"]}
            for l in linhas:
                l["Padrão"] = nomes.get(l["Padrão"], l["Padrão"])
            st.plotly_chart(grafico_comparacao(linhas), width="stretch", config={"displayModeBar": False})
            tabela = [{"Forma de apostar": l["Padrão"],
                       "Resultado médio": brl(l["Resultado médio (R$)"]),
                       "Terminam no prejuízo": pc(l["Abaixo da banca inicial"]),
                       "Dinheiro acaba": pc(l["Ruína / saldo insuficiente"])} for l in linhas]
            st.dataframe(tabela, hide_index=True, width="stretch")
            st.caption("Dobrar depois de perder não muda a margem da casa: o resultado médio continua negativo e o "
                       "risco de o dinheiro acabar aumenta muito.")

    with st.expander("Detalhes e hipóteses do simulador"):
        c = st.columns(3)
        c[0].metric("Lucro se acertar", brl(a["lucro_se_acertar"]))
        c[1].metric("Perda se errar", brl(a["perda_se_errar"]))
        c[2].metric("Maior queda média", brl(r["drawdown_medio"]),
                    help="A maior queda a partir do ponto mais alto do saldo, em média nas simulações.")
        st.markdown(
            "- **Chance de acerto:** (1 ÷ odd) ÷ (1 + margem). É a chance que a odd indicaria se a casa não cobrasse "
            "nada. Não é a probabilidade verdadeira do jogo, que ninguém conhece.\n"
            "- Com qualquer odd, se a margem é *m*, de cada R\\$ 100 voltam em média R\\$ 100 ÷ (1 + *m*).\n"
            "- Cada aposta é **independente** das outras; odd e chance não mudam ao longo do período.\n"
            "- Não entram **bônus, promoções, impostos** nem limites das plataformas.\n"
            "- Sem dinheiro reservado informado, o gráfico mostra o ganho ou a perda acumulada, começando do zero.")


# ----------------------------------------------------------------------- app

st.markdown(CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Sobre")
    st.markdown("Ferramenta educativa do **Projetos III — Grupo 3**. Explica odds, margem da casa, vieses e custo "
                "de oportunidade com base em fontes oficiais e acadêmicas.")
    st.markdown("### Precisa de apoio?")
    st.markdown("- **CAPS / SUS**: atendimento gratuito na rede de saúde mental\n"
                "- **gov.br/autoexclusaoapostas**: autoteste e bloqueio do CPF em todas as bets autorizadas")
    prov = llm.provedor()
    st.caption(f"Modelo do chat: {'Gemini' if prov == 'gemini' else 'Claude' if prov == 'anthropic' else 'não configurado'}")

st.markdown(
    '<div class="hero"><span class="selo">🎓 Ferramenta educativa · 18+</span>'
    "<h1>Apostas esportivas: o que os números dizem</h1>"
    "<p>Converse sobre odds, chances e riscos, ou simule quanto apostar pode custar ao longo do tempo.</p></div>",
    unsafe_allow_html=True)
st.markdown('<div class="aviso"><b>Não damos palpites</b>, não indicamos casas de apostas e não fazemos '
            "aconselhamento financeiro ou psicológico. Se apostar estiver pesando, procure um CAPS/SUS ou acesse "
            "<b>gov.br/autoexclusaoapostas</b>.</div>", unsafe_allow_html=True)

aba_chat_, aba_sim_ = st.tabs(["Conversa", "Simulador"], key="abas", on_change="rerun")
with aba_chat_:
    aba_chat()
with aba_sim_:
    aba_simulador()
