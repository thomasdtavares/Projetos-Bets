"""Assistente educativo sobre apostas esportivas — abas Conversa e Simulador."""
from pathlib import Path

import numpy as np
import pandas  # noqa: F401  (importado cedo para evitar corrida de import entre execuções do script)
import plotly.graph_objects as go
import streamlit as st

import importlib
import re
import uuid

import llm
import registro
import respostas_prontas
import simulador as sim

# No Streamlit Cloud, um novo commit roda o app.py de novo, mas o módulo simulador já importado continua
# na memória com a versão antiga (o que gerou AttributeError em 16/10/2026). Recarregar garante a versão atual.
sim = importlib.reload(sim)
respostas_prontas = importlib.reload(respostas_prontas)
registro = importlib.reload(registro)
llm = importlib.reload(llm)

RAIZ = Path(__file__).parent
EXEMPLOS = [
    "Como funciona uma aposta esportiva?",
    "Se eu acertar mais da metade das minhas apostas, eu lucro?",
    "Vale a pena dobrar a aposta para recuperar o que perdi?",
    "Se eu apostar R$ 20 por rodada do Brasileirão numa odd 2,20, quanto isso pode custar?",
]
OUTRA = "Outra odd"
TIPOS = list(sim.TIPOS_ODD) + [OUTRA]
DESCR_TIPO = {"Favorito": "o time mais forte vence", "Jogo equilibrado": "times parecidos",
              "Zebra": "o mais fraco vence", OUTRA: "digite a odd"}
HORIZONTES = list(sim.HORIZONTES)
ABA_CHAT, ABA_SIM, ABA_SOBRE = "💬 Conversa", "📊 Simulador", "ℹ️ Sobre"
JOGO_INICIO, JOGO_APOSTA = 200.0, 10.0

# Cores (paleta de referência validada: azul/vermelho como par de polaridade, cinza neutro)
AZUL, VERMELHO, LARANJA = "#2a78d6", "#e34948", "#eb6834"
CINZA, CINZA_TEXTO, TINTA, GRADE = "#b9b7b0", "#6b6a66", "#1f1e1c", "#ecebe7"

st.set_page_config(page_title="Bets: os números", page_icon="🎓", layout="wide",
                   initial_sidebar_state="collapsed")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp { font-family: 'Inter', system-ui, sans-serif; }
.block-container { max-width: 1080px; padding-top: 2rem; }
h1, h2, h3 { letter-spacing: -0.01em; }

.hero { background: linear-gradient(135deg, #0f2f57 0%, #1d5fb0 55%, #2a78d6 100%); color: #fff;
        border-radius: 20px; padding: 28px 32px; margin-bottom: 14px; }
.hero h1 { color: #fff; font-size: 2rem; font-weight: 800; margin: 0 0 6px 0; padding: 0; }
.hero p { color: #dce9fa; margin: 0; font-size: 1.03rem; }
.selo { display: inline-block; background: rgba(255,255,255,0.16); color: #fff; border-radius: 999px;
        padding: 3px 12px; font-size: 0.8rem; margin-bottom: 10px; font-weight: 600; }
.aviso { background: #f3f2ee; border-radius: 12px; padding: 10px 16px; font-size: 0.88rem; color: #52514e;
         margin-bottom: 8px; }
.aviso b { color: #1f1e1c; }

.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid #ecebe7; }
.stTabs [data-baseweb="tab"] { height: 44px; padding: 0 16px; font-weight: 600; font-size: 0.98rem; }

[data-testid="stMetric"] { background: #fff; border: 1px solid #ecebe7; border-radius: 14px; padding: 14px 16px; }
[data-testid="stMetricLabel"] p { color: #6b6a66; font-size: 0.85rem; }
[data-testid="stMetricValue"] { font-size: 1.45rem; font-weight: 700; }
[data-testid="stChatMessage"] { border-radius: 16px; padding: 14px 18px; }

.secao { font-size: 1.25rem; font-weight: 750; color: #1f1e1c; margin: 26px 0 2px 0; }
.sub { color: #6b6a66; margin: 0 0 10px 0; font-size: 0.95rem; }

.resultado { background: #fff; border: 1px solid #ecebe7; border-radius: 18px; padding: 22px 26px; margin: 8px 0 12px 0;
             box-shadow: 0 1px 2px rgba(0,0,0,0.03); }
.resultado .rotulo { font-size: 0.8rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #e34948; }
.resultado .rotulo.azul { color: #2a78d6; }
.resultado .grande { font-size: 1.7rem; font-weight: 800; color: #1f1e1c; line-height: 1.25; margin: 6px 0; }
.resultado .grande .neg { color: #d03b3b; }
.resultado .peq { color: #52514e; font-size: 0.98rem; }

.mudou { background: #eef4fc; border: 1px solid #cde2fb; border-radius: 14px; padding: 12px 18px; margin: 6px 0 4px 0;
         color: #1c3f6e; font-size: 0.95rem; }
.mudou b { color: #0d366b; }
.pendente { background: #fff7e6; border: 1px solid #fadb9c; border-radius: 12px; padding: 10px 16px; color: #6b4a00;
            font-size: 0.92rem; margin-top: 8px; }

.pessoas { display: grid; grid-template-columns: repeat(20, 1fr); gap: 6px 4px; max-width: 640px; margin: 10px 0 6px 0; }
.pessoas svg { width: 100%; height: auto; max-width: 26px; }
@media (max-width: 640px) { .pessoas { grid-template-columns: repeat(10, 1fr); } }
.legenda { display: flex; flex-wrap: wrap; gap: 16px; font-size: 0.92rem; color: #1f1e1c; margin: 4px 0 10px 0; }
.legenda span::before { content: ""; display: inline-block; width: 11px; height: 11px; border-radius: 3px;
                        margin-right: 6px; background: var(--c); vertical-align: -1px; }

.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 10px 0; }
@media (max-width: 860px) { .cards { grid-template-columns: 1fr; } }
.card { background: #fff; border: 1px solid #ecebe7; border-radius: 16px; padding: 16px 18px; border-top: 5px solid var(--c); }
.card h4 { margin: 0 0 4px 0; font-size: 1.02rem; font-weight: 700; color: #1f1e1c; padding: 0; }
.card .d { color: #6b6a66; font-size: 0.86rem; min-height: 2.6em; margin-bottom: 10px; }
.card .linha { display: flex; justify-content: space-between; font-size: 0.92rem; padding: 4px 0;
               border-top: 1px solid #f3f2ee; color: #1f1e1c; }
.card .linha b { font-weight: 700; }
.card .nota { font-size: 0.83rem; color: #6b4a00; background: #fff7e6; border-radius: 8px; padding: 6px 8px;
              margin-top: 8px; line-height: 1.35; }
.card .tag { display: inline-block; font-size: 0.72rem; font-weight: 700; border-radius: 999px; padding: 2px 8px;
             background: var(--c); color: #fff; margin-bottom: 6px; }

.placar { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 10px 0; }
@media (max-width: 640px) { .placar { grid-template-columns: 1fr; } }
.placar > div { background: #fff; border: 1px solid #ecebe7; border-radius: 16px; padding: 14px 16px; }
.placar .r { font-size: 0.82rem; color: #6b6a66; }
.placar .v { font-size: 1.6rem; font-weight: 800; color: #1f1e1c; }
.ultimo { font-size: 1.05rem; font-weight: 650; margin: 4px 0 2px 0; }
</style>
"""

PESSOA = ('<svg viewBox="0 0 24 24" fill="{c}"><circle cx="12" cy="6.5" r="4.2"/>'
          '<path d="M3.5 23c0-5 3.8-9 8.5-9s8.5 4 8.5 9z"/></svg>')


# ------------------------------------------------------------------ utilidades

def brl(x, casas=2):
    sinal = "−" if round(x, casas) < 0 else ""
    return sinal + "R$ " + f"{abs(x):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl_md(x, casas=2):
    """R$ para usar em markdown/caption (o Streamlit trata $...$ como fórmula)."""
    return brl(x, casas).replace("$", "\\$")


def brl_html(x, casas=2):
    return brl(x, casas).replace("$", "&#36;")


def pc(x, casas=1):
    return f"{x * 100:.{casas}f}%".replace(".", ",")


def num(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",")


def secao(titulo, sub=None):
    st.markdown(f'<div class="secao">{titulo}</div>' + (f'<p class="sub">{sub}</p>' if sub else ""),
                unsafe_allow_html=True)


@st.cache_data
def prompt_completo():
    prompt = (RAIZ / "prompt_sistema.md").read_text(encoding="utf-8")
    base = (RAIZ / "conhecimento" / "base.md").read_text(encoding="utf-8")
    return f"{prompt}\n\n# BASE DE CONHECIMENTO\n\n{base}"


@st.cache_data(show_spinner=False)
def rodar_mc(valor, odd, prob, apostas):
    return sim.monte_carlo(valor, odd, prob, apostas, semente=2026)


@st.cache_data(show_spinner=False)
def rodar_tempo(valor, odd, prob, por_semana):
    return sim.lucro_ao_longo_do_tempo(valor, odd, prob, por_semana)


@st.cache_data(show_spinner="Simulando as estratégias…")
def rodar_estrategias(valor, odd, prob, apostas, banca):
    return sim.comparar_estrategias(valor, odd, prob, apostas, banca, n_sim=5000, semente=2026)


# ------------------------------------------------------------------ estado

o1, o2, o3 = sim.ODDS_EXEMPLO_1X2
PADROES = dict(q_valor=20.0, q_tipo="Jogo equilibrado", q_odd_outra=1.80, q_por_semana=2, q_horizonte="1 ano",
               q_margem=sim.MARGEM_PADRAO * 100, q_taxa=list(sim.TAXAS_GUARDAR)[0], q_reaposta="Metade",
               q_banca=400.0, mult_tipo="Favorito", mult_jogos=3, jogo_tipo="Jogo equilibrado",
               calc_o1=o1, calc_o2=o2, calc_o3=o3)
REAPOSTA = {"Nada (saco tudo)": 0.0, "Metade": 0.5, "Tudo, até acabar": 1.0}
for k, v in PADROES.items():
    st.session_state[k] = st.session_state.get(k, v)  # reatribui: mantém o valor mesmo com a aba fechada
st.session_state.setdefault("mensagens", [])
st.session_state.setdefault("abas", ABA_CHAT)
st.session_state.setdefault("sessao", uuid.uuid4().hex[:8])  # código aleatório, só para agrupar o registro anônimo


def odd_do_tipo(tipo, outra):
    return outra if tipo == OUTRA else sim.TIPOS_ODD.get(tipo, 2.20)


def cenario_atual():
    s = st.session_state
    tipo = s.q_tipo or PADROES["q_tipo"]
    return {"valor": float(s.q_valor), "tipo": tipo, "odd": float(odd_do_tipo(tipo, s.q_odd_outra)),
            "por_semana": int(s.q_por_semana or PADROES["q_por_semana"]),
            "horizonte": s.q_horizonte or PADROES["q_horizonte"], "margem": round(float(s.q_margem) / 100, 4)}


def aplicar_cenario():
    s = st.session_state
    novo = cenario_atual()
    if s.get("cen") != novo:
        s.cen_ant = s.get("cen")
        s.cen = novo


st.session_state.setdefault("cen", cenario_atual())
st.session_state.setdefault("cen_ant", None)


def abrir_no_simulador(p):
    """Callback do botão do chat: leva o cenário da linha [SIMULAR] para o simulador e já mostra o resultado."""
    s = st.session_state
    if "valor" in p:
        s.q_valor = float(p["valor"])
    elif "pct" in p and "banca" in p:
        s.q_valor = float(p["pct"] * p["banca"])
    if "odd" in p:
        odd = float(p["odd"])
        tipo = next((t for t, o in sim.TIPOS_ODD.items() if abs(o - odd) < 1e-9), OUTRA)
        s.q_tipo, s.q_odd_outra = tipo, odd
    if "apostas" in p:
        s.q_por_semana, s.q_horizonte = sim.cenario_do_chat(int(p["apostas"]))
    if "banca" in p:
        s.q_banca = float(p["banca"])
    if "margem" in p:
        s.q_margem = min(max(float(p["margem"]) * 100, 0.0), 20.0)
    aplicar_cenario()
    s.abas = ABA_SIM


def pergunta_exemplo(texto):
    st.session_state.pendente = texto


def limpar_conversa():
    st.session_state.mensagens = []


def tentar_de_novo(i):
    """Apaga a resposta que falhou (ou veio cortada) e pede de novo a resposta da mesma pergunta."""
    del st.session_state.mensagens[i:]
    st.session_state.repetir = True


def avaliar(i):
    m = st.session_state.mensagens[i]
    nota = st.session_state.get(f"fb_{m['id']}")
    pergunta = next((x["content"] for x in reversed(st.session_state.mensagens[:i]) if x["role"] == "user"), "")
    registro.registrar(st.session_state.sessao, "avaliacao", pergunta, m.get("tipo", ""),
                       {1: "positiva", 0: "negativa"}.get(nota, "removida"))


# ------------------------------------------------------------------ gráficos

def estilo(fig, titulo, x="", y="", altura=380, moeda=True):
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
    fig.update_yaxes(title=y, gridcolor=GRADE, zeroline=False, separatethousands=True,
                     tickprefix="R$ " if moeda else "")
    return fig


SEM_BARRA = {"displayModeBar": False}


def grafico_para_onde_vai(volta):
    """Barra única: de cada R$ 100, quanto volta e quanto fica com a casa."""
    fica = 100 - volta
    fig = go.Figure()
    fig.add_bar(y=[""], x=[volta], orientation="h", marker_color=AZUL, name="Volta para você",
                text=[f"volta {brl(volta)}"], textposition="inside", insidetextanchor="start",
                hovertemplate="Volta em média: R$ %{x:.2f}<extra></extra>")
    if fica > 0:
        fig.add_bar(y=[""], x=[fica], orientation="h", marker_color=VERMELHO, name="Fica com a casa",
                    text=[f"casa {brl(fica)}"], textposition="outside", textfont_color=VERMELHO,
                    hovertemplate="Fica com a casa: R$ %{x:.2f}<extra></extra>")
    fig.update_layout(barmode="stack", height=96, margin=dict(t=4, b=4, l=4, r=4), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, system-ui, sans-serif", color="#fff", size=14),
                      bargap=0.1, separators=",.")
    fig.update_xaxes(visible=False, range=[0, max(100, volta) * 1.3])
    fig.update_yaxes(visible=False)
    return fig


def grafico_tempo(linhas, mes_escolhido):
    meses = [l["mes"] for l in linhas]
    bruto = [l["chance_lucro"] * 100 for l in linhas]
    tend = [l["tendencia"] * 100 for l in linhas]
    fig = go.Figure()
    fig.add_scatter(x=meses, y=bruto, mode="lines", line=dict(color="rgba(42,120,214,0.30)", width=1.5),
                    name="Mês a mês", hovertemplate="Depois de %{x} meses: %{y:.0f} em 100 no lucro<extra></extra>")
    fig.add_scatter(x=meses, y=tend, mode="lines", line=dict(color=AZUL, width=4), name="Tendência",
                    hovertemplate="Tendência: %{y:.0f} em 100<extra></extra>")
    i = min(range(len(meses)), key=lambda j: abs(meses[j] - mes_escolhido))
    fig.add_scatter(x=[meses[i]], y=[tend[i]], mode="markers+text", marker=dict(size=13, color=AZUL,
                    line=dict(color="#fff", width=3)), text=[f"seu cenário: {tend[i]:.0f} em 100"],
                    textposition="top right", textfont=dict(color=TINTA, size=13), showlegend=False,
                    hoverinfo="skip")
    fig.add_hline(y=50, line_dash="dot", line_color=CINZA, annotation_text="metade das pessoas",
                  annotation_position="top right", annotation_font_color=CINZA_TEXTO)
    fig = estilo(fig, "Pessoas no lucro (de cada 100), conforme o tempo passa", "Meses apostando", "",
                 altura=390, moeda=False)
    fig.update_yaxes(range=[0, max(60, max(bruto) + 5)], ticksuffix="")
    fig.update_xaxes(tickvals=[1, 6, 12, 24, 36, 48, 60])
    return fig


def grafico_oportunidade(c):
    x = c["periodos"]
    fig = go.Figure()
    fig.add_scatter(x=x, y=c["apostado"], mode="lines", name="O que você colocou",
                    line=dict(color=CINZA, width=2, dash="dot"), hovertemplate="Colocado: R$ %{y:,.2f}<extra></extra>")
    fig.add_scatter(x=x, y=c["acumulado"], mode="lines", name="Se tivesse guardado",
                    line=dict(color=AZUL, width=3), hovertemplate="Guardado: R$ %{y:,.2f}<extra></extra>")
    fig.add_scatter(x=x, y=c["apostando"], mode="lines", name="Se apostou (o que volta, em média)",
                    line=dict(color=VERMELHO, width=3), fill="tonexty", fillcolor="rgba(227,73,72,0.08)",
                    hovertemplate="Apostando: R$ %{y:,.2f}<extra></extra>")
    fig.add_annotation(x=x[-1], y=(c["acumulado"][-1] + c["apostando"][-1]) / 2, xanchor="left",
                       text=f"diferença<br><b>{brl(c['diferenca'])}</b>", showarrow=False,
                       font=dict(color=TINTA, size=13), xshift=6)
    fig = estilo(fig, "Guardar ou apostar o mesmo dinheiro", "Semanas", "", altura=380)
    fig.update_layout(hovermode="x unified", margin=dict(r=100))
    return fig


def grafico_trajetorias(r):
    x = list(range(r["apostas"] + 1))
    fig = go.Figure()
    vistos = set()
    for linha in r["amostra"][:30]:
        acima = linha[-1] >= 0
        nome = "Uma pessoa que terminou no lucro" if acima else "Uma pessoa que terminou no prejuízo"
        fig.add_scatter(x=x, y=linha, mode="lines", name=nome, legendgroup=nome, showlegend=nome not in vistos,
                        line=dict(width=1.2, color="rgba(42,120,214,0.30)" if acima else "rgba(227,73,72,0.28)"),
                        hoverinfo="skip")
        vistos.add(nome)
    fig.add_scatter(x=x, y=r["media_passo"], mode="lines", line=dict(width=3.5, color=TINTA),
                    name="Média de todas", hovertemplate="Depois de %{x} apostas<br>Média: R$ %{y:,.2f}<extra></extra>")
    fig.add_hline(y=0, line_dash="dot", line_color=CINZA_TEXTO, line_width=1.5)
    return estilo(fig, "30 pessoas, aposta a aposta", "Número da aposta", "Ganho ou perda acumulada", altura=420)


def grafico_reaposta(deposito, fator):
    nomes = list(REAPOSTA)
    sobras = [sim.reapostar(deposito, fator, f)["sobra"] for f in REAPOSTA.values()]
    fig = go.Figure(go.Bar(x=nomes, y=sobras, marker_color=[AZUL, LARANJA, VERMELHO],
                           text=[f"sobra {brl(v, 0)}" for v in sobras],
                           textposition=["inside" if v > deposito * 0.15 else "outside" for v in sobras],
                           insidetextanchor="middle", textfont=dict(size=14),
                           hovertemplate="%{x}: sobra R$ %{y:,.0f}<extra></extra>"))
    fig.add_hline(y=deposito, line_dash="dot", line_color=CINZA_TEXTO,
                  annotation_text=f"você colocou {brl(deposito, 0)}", annotation_position="top right",
                  annotation_font_color=CINZA_TEXTO)
    fig = estilo(fig, "Quanto sobra, em média, conforme o quanto você reaposta", altura=340)
    fig.update_yaxes(range=[0, deposito * 1.25])
    return fig


def grafico_estrategias(linhas):
    nomes = [l["nome"] for l in linhas]
    tudo = [l["perderam_tudo"] * 100 for l in linhas]
    cores = [AZUL if l["chave"] == "limite_perda" else CINZA if l["chave"] == "fixo"
             else (VERMELHO if l["perderam_tudo"] >= 0.5 else LARANJA) for l in linhas]
    fig = go.Figure(go.Bar(x=tudo, y=nomes, orientation="h", marker_color=cores,
                           text=[f"{v:.0f} em 100" for v in tudo], textposition="outside",
                           hovertemplate="%{y}: %{x:.0f} em 100 perderam tudo<extra></extra>"))
    fig = estilo(fig, "Quantas pessoas (de 100) perderam TODO o dinheiro reservado", altura=330, moeda=False)
    fig.update_xaxes(range=[0, 118], showticklabels=False, showgrid=False)
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    return fig


def grafico_jogo(hist, titulo, cor, ref=None):
    fig = go.Figure(go.Scatter(x=list(range(len(hist))), y=hist, mode="lines", line=dict(color=cor, width=3),
                               fill="tozeroy" if ref is None else None, fillcolor="rgba(227,73,72,0.08)",
                               hovertemplate="Aposta %{x}: R$ %{y:,.2f}<extra></extra>"))
    if ref is not None:
        fig.add_hline(y=ref, line_dash="dot", line_color=CINZA_TEXTO, annotation_text="você começou aqui",
                      annotation_position="bottom right", annotation_font_color=CINZA_TEXTO)
    fig = estilo(fig, titulo, "Apostas", "", altura=300)
    fig.update_yaxes(tickformat=",.0f")
    fig.update_layout(margin=dict(t=48, b=8, l=8, r=8), showlegend=False)
    return fig


def grafico_multipla(odd, escolhido, margem, maximo=8):
    ks = list(range(1, maximo + 1))
    chances = [sim.bilhete_multiplo(odd, k, margem)["chance"] * 100 for k in ks]
    cores = [AZUL if k == escolhido else "#b7d3f6" for k in ks]
    fig = go.Figure(go.Bar(x=[f"{k} jogo" + ("s" if k > 1 else "") for k in ks], y=chances, marker_color=cores,
                           text=[f"{c:.1f}%".replace(".", ",") if c >= 0.1 else "<0,1%" for c in chances],
                           textposition="outside", hovertemplate="%{x}: %{y:.2f}% de chance<extra></extra>"))
    fig = estilo(fig, "Chance de acertar o bilhete inteiro", altura=340, moeda=False)
    fig.update_yaxes(ticksuffix="%", range=[0, max(chances) * 1.2])
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
                d = sim.distribuicao(valor, p["odd"], r["prob"], p["apostas"])
            except sim.ErroValidacao as e:
                st.warning(str(e))
                r = None
            if r:
                st.markdown(f"**📊 Conta feita pelo simulador** · {p['apostas']} apostas de {brl_md(valor)}, odd {num(p['odd'])}")
                c = st.columns(4)
                c[0].metric("De cada R$ 100, voltam", brl(r["retorno_por_100"]))
                c[1].metric("Total apostado", brl(r["total_apostado"]))
                c[2].metric("Resultado médio", brl(r["perda_esperada"]))
                c[3].metric("De 100 pessoas, perdem", f"{sim.pessoas_em_100(d)['perderam']}")
        else:
            st.caption("Ainda faltam dados para a conta (valor, odd e número de apostas). "
                       "Você pode completá-los direto no simulador.")
        st.button("Ver no simulador →", key=chave, on_click=abrir_no_simulador, args=(p,), type="primary")


MSG_ERRO = ("Não consegui responder agora: o serviço do assistente está demorando ou fora do ar. "
            "Sua pergunta continua aqui. Tente de novo em alguns segundos.")
MSG_SEM_CHAVE = ("O chat está sem chave de API configurada (GEMINI_API_KEY ou ANTHROPIC_API_KEY nos Secrets do app). "
                 "As perguntas sugeridas e o simulador funcionam normalmente.")


def nova_resposta(texto, tipo, completa=True):
    limpo, params = sim.extrair_simular(texto)
    return {"role": "assistant", "content": texto, "texto": limpo, "simular": params, "tipo": tipo,
            "incompleta": not completa, "id": uuid.uuid4().hex[:10]}


def responder_ultima():
    """Pede ao modelo a resposta para a última pergunta do histórico (a pergunta já está salva)."""
    msgs = st.session_state.mensagens
    historico = [{"role": m["role"], "content": m["content"]} for m in msgs if not m.get("erro")]
    pergunta = historico[-1]["content"]
    try:
        with st.spinner("Pensando… (pode levar alguns segundos)"):
            r = llm.responder(historico, prompt_completo())
    except Exception as e:  # rede, cota, sobrecarga, tempo esgotado...
        msgs.append({"role": "assistant", "content": "", "erro": True, "detalhe": type(e).__name__,
                     "id": uuid.uuid4().hex[:10]})
        registro.registrar(st.session_state.sessao, "pergunta", pergunta, "erro")
        return
    tipo = "modelo" if r.completa else "modelo_incompleta"
    msgs.append(nova_resposta(r.texto, "modelo", r.completa))
    registro.registrar(st.session_state.sessao, "pergunta", pergunta, tipo)


def aba_chat():
    s = st.session_state
    pergunta = st.chat_input("Pergunte sobre odds, chances, riscos, quanto custa apostar…")
    pergunta = pergunta or s.pop("pendente", None)

    if pergunta:
        s.mensagens.append({"role": "user", "content": pergunta, "id": uuid.uuid4().hex[:10]})
        pronta = respostas_prontas.RESPOSTAS_PRONTAS.get(pergunta.strip())
        if pronta:
            s.mensagens.append(nova_resposta(pronta, "pronta"))
            registro.registrar(s.sessao, "pergunta", pergunta, "pronta")
        elif llm.provedor() is None:
            s.mensagens.append({"role": "assistant", "content": "", "erro": True, "detalhe": "SemChave",
                                "id": uuid.uuid4().hex[:10]})
        else:
            responder_ultima()
    elif s.pop("repetir", False) and s.mensagens and s.mensagens[-1]["role"] == "user":
        if llm.provedor() is None:
            s.mensagens.append({"role": "assistant", "content": "", "erro": True, "detalhe": "SemChave",
                                "id": uuid.uuid4().hex[:10]})
        else:
            responder_ultima()

    if not s.mensagens:
        with st.chat_message("assistant", avatar="🎓"):
            st.markdown("Oi! Eu explico **como as apostas funcionam por dentro**: o que a odd quer dizer, por que a "
                        "casa sempre leva uma parte e quanto apostar pode custar ao longo do tempo. "
                        "Não dou palpites. Comece por uma destas perguntas ou escreva a sua:")
            c = st.columns(2)
            for i, ex in enumerate(EXEMPLOS):
                c[i % 2].button(ex.replace("$", "\\$"), key=f"ex{i}", on_click=pergunta_exemplo, args=(ex,),
                                width="stretch")

    ultimo = len(s.mensagens) - 1
    for i, m in enumerate(s.mensagens):
        m.setdefault("id", uuid.uuid4().hex[:10])
        avatar = "🎓" if m["role"] == "assistant" else "🙂"
        with st.chat_message(m["role"], avatar=avatar):
            if m.get("erro"):
                st.warning(MSG_SEM_CHAVE if m.get("detalhe") == "SemChave" else MSG_ERRO, icon=":material/schedule:")
                if i == ultimo:
                    st.button("Tentar de novo", key=f"rep_{m['id']}", on_click=tentar_de_novo, args=(i,),
                              icon=":material/refresh:")
                continue
            st.markdown(m.get("texto", m["content"]).replace("$", "\\$"))
            if m.get("incompleta"):
                st.warning("A resposta foi interrompida antes do fim.", icon=":material/content_cut:")
                if i == ultimo:
                    st.button("Tentar de novo", key=f"rep_{m['id']}", on_click=tentar_de_novo, args=(i,),
                              icon=":material/refresh:")
            if m.get("simular"):
                resumo_chat(m["simular"], f"abrir_{m['id']}")
            if m["role"] == "assistant":
                rodape = st.columns([1, 5])
                with rodape[0]:
                    st.feedback("thumbs", key=f"fb_{m['id']}", on_change=avaliar, args=(i,))
                if m.get("tipo") == "pronta":
                    rodape[1].caption("Resposta da base de conhecimento do projeto.")

    if s.mensagens:
        st.button("Limpar conversa", on_click=limpar_conversa, type="tertiary", icon=":material/delete_sweep:")


# --------------------------------------------------------------- Simulador

def margem_de(c):
    return c.get("margem", sim.MARGEM_PADRAO)


def calcular(c, taxa=sim.TAXA_GUARDAR):
    """Todos os números do cenário aplicado (conta exata, sem sorteio)."""
    prob = sim.prob_justa(c["odd"], margem_de(c))
    semanas = sim.HORIZONTES[c["horizonte"]]
    n = c["por_semana"] * semanas
    d = sim.distribuicao(c["valor"], c["odd"], prob, n)
    a = sim.aposta_unica(c["valor"], c["odd"], prob)
    co = sim.custo_oportunidade(c["valor"] * c["por_semana"], "semanal", semanas, taxa,
                                fator_retorno=prob * c["odd"])
    return {"prob": prob, "n": n, "semanas": semanas, "d": d, "a": a, "co": co, "g": sim.pessoas_em_100(d)}


def descrever_mudanca(ant, novo):
    partes = []
    if ant["valor"] != novo["valor"]:
        partes.append(f"o valor de {brl_html(ant['valor'])} para {brl_html(novo['valor'])}")
    if ant["odd"] != novo["odd"]:
        partes.append(f"a aposta de {ant['tipo'].lower()} (odd {num(ant['odd'])}) para "
                      f"{novo['tipo'].lower()} (odd {num(novo['odd'])})")
    if ant["por_semana"] != novo["por_semana"]:
        partes.append(f"de {ant['por_semana']} para {novo['por_semana']} apostas por semana")
    if ant["horizonte"] != novo["horizonte"]:
        partes.append(f"o tempo de {ant['horizonte']} para {novo['horizonte']}")
    if margem_de(ant) != margem_de(novo):
        partes.append(f"a margem da casa de {pc(margem_de(ant))} para {pc(margem_de(novo))}")
    return ", ".join(partes)


def pessoas_html(g):
    icones = ([PESSOA.format(c=VERMELHO)] * g["perderam"] + [PESSOA.format(c=CINZA)] * g["empataram"]
              + [PESSOA.format(c=AZUL)] * g["ganharam"])
    legenda = [f'<span style="--c:{VERMELHO}"><b>{g["perderam"]}</b> perderam dinheiro</span>']
    if g["empataram"]:
        legenda.append(f'<span style="--c:{CINZA}"><b>{g["empataram"]}</b> empataram</span>')
    legenda.append(f'<span style="--c:{AZUL}"><b>{g["ganharam"]}</b> ganharam dinheiro</span>')
    return f'<div class="pessoas">{"".join(icones)}</div><div class="legenda">{"".join(legenda)}</div>'


def bloco_quanto_custa():
    s = st.session_state
    with st.container(border=True):
        st.markdown("##### Conte como você aposta")
        c1, c2 = st.columns(2)
        c1.number_input("Quanto você aposta por vez? (R$)", min_value=1.0, max_value=100_000.0, step=5.0,
                        key="q_valor")
        c2.segmented_control("Quantas apostas por semana?", sim.APOSTAS_POR_SEMANA, key="q_por_semana")
        st.segmented_control("Em que tipo de aposta?", TIPOS, key="q_tipo",
                             format_func=lambda t: t if t == OUTRA else f"{t} · odd {num(sim.TIPOS_ODD[t])}",
                             help="A odd é quanto a casa paga por R$ 1. Odd 2,20: R$ 10 viram R$ 22 se acertar.")
        if s.q_tipo == OUTRA:
            st.number_input("Qual a odd?", min_value=1.01, max_value=100.0, step=0.05, format="%.2f",
                            key="q_odd_outra")
        st.segmented_control("Por quanto tempo?", HORIZONTES, key="q_horizonte",
                             help="1 Brasileirão = 38 semanas, uma rodada por semana.")
        with st.expander(f"Margem da casa: {pc(s.q_margem / 100)} (opcional: ajustar)"):
            st.slider("Margem da casa (%)", 2.0, 15.0, step=0.1, key="q_margem", format="%.1f%%")
            st.caption("É a parte que a casa embute nas odds. Usamos 5% como referência (o exemplo da nossa base soma "
                       "104,8%). Em zebras e em mercados menos movimentados ela costuma ser maior. Para medir a margem "
                       "de um jogo de verdade, use a aba **Ler as odds de um jogo**.")
        pendente = cenario_atual() != s.cen
        st.button("Ver o que acontece", type="primary", on_click=aplicar_cenario, width="stretch",
                  icon=":material/play_arrow:")
        if pendente:
            st.markdown('<div class="pendente">✏️ Você mudou o cenário. Aperte <b>Ver o que acontece</b> para '
                        "atualizar o resultado.</div>", unsafe_allow_html=True)

    c = s.cen
    try:
        r = calcular(c)
    except sim.ErroValidacao as e:
        st.error(str(e))
        return
    d, a, g, co = r["d"], r["a"], r["g"], r["co"]

    # --- o que mudou -------------------------------------------------------------------
    if s.cen_ant:
        try:
            ant = calcular(s.cen_ant)
        except sim.ErroValidacao:
            ant = None
        if ant:
            st.markdown(
                f'<div class="mudou">🔄 Você mudou {descrever_mudanca(s.cen_ant, c)}.<br>'
                f'Resultado médio: antes <b>{brl_html(ant["d"]["resultado_medio"])}</b> → agora '
                f'<b>{brl_html(d["resultado_medio"])}</b> · Pessoas no prejuízo: antes <b>{ant["g"]["perderam"]}</b> '
                f'→ agora <b>{g["perderam"]}</b> em 100'
                + ("<br>O resultado médio não mudou: a casa cobra a mesma parte em qualquer tipo de aposta. "
                   "O que muda é como a sorte se espalha entre as pessoas."
                   if abs(ant["d"]["resultado_medio"] - d["resultado_medio"]) < 0.5 and ant["d"]["apostas"] == d["apostas"]
                   and ant["d"]["total_apostado"] == d["total_apostado"] else "")
                + "</div>", unsafe_allow_html=True)

    # --- resultado principal -----------------------------------------------------------
    volta = a["retorno_por_100"]
    st.markdown(
        f'<div class="resultado"><div class="rotulo">O resultado</div>'
        f'<div class="grande">Em {c["horizonte"]}, você coloca {brl_html(d["total_apostado"], 0)} nas apostas '
        f'e, em média, termina com <span class="neg">{brl_html(-d["resultado_medio"], 0)} a menos</span>.</div>'
        f'<div class="peq">São {r["n"]} apostas de {brl_html(c["valor"])}. De cada {brl_html(100, 0)} apostados, '
        f'voltam em média {brl_html(volta)}; o resto fica com a casa. Isso vale para qualquer tipo de aposta: '
        "a casa cobra a parte dela em todas.</div></div>", unsafe_allow_html=True)
    st.plotly_chart(grafico_para_onde_vai(volta), width="stretch", config=SEM_BARRA)

    ant_r = None
    if s.cen_ant:
        try:
            ant_r = calcular(s.cen_ant)
        except sim.ErroValidacao:
            pass
    def delta(x, moeda=True):
        if ant_r is None or abs(x) < 0.005:
            return None
        txt = brl(x, 0) if moeda else f"{x:+.0f}"
        return txt.replace("−", "-") + " vs. antes"

    m = st.columns(3)
    m[0].metric("Total apostado", brl(d["total_apostado"], 0),
                delta=delta(d["total_apostado"] - ant_r["d"]["total_apostado"]) if ant_r else None,
                delta_color="off")
    m[1].metric("Resultado médio", brl(d["resultado_medio"], 0),
                delta=delta(d["resultado_medio"] - ant_r["d"]["resultado_medio"]) if ant_r else None)
    m[2].metric("De 100 pessoas, perdem", f"{g['perderam']}",
                delta=delta(g["perderam"] - ant_r["g"]["perderam"], moeda=False) if ant_r else None,
                delta_color="inverse")

    # --- 100 pessoas --------------------------------------------------------------------
    secao("Se 100 pessoas fizessem exatamente isso",
          "Mesmo valor, mesma aposta, mesmo tempo. A única diferença entre elas é a sorte.")
    st.markdown(pessoas_html(g), unsafe_allow_html=True)
    frase = f"**{g['perderam']} de cada 100 terminam no prejuízo**"
    if d["chance_perda"] > 0:
        frase += f", perdendo em média {brl_md(-d['perda_media'], 0)}"
    if g["ganharam"]:
        frase += f". As {g['ganharam']} que ganham levam em média {brl_md(d['ganho_medio'], 0)}"
    st.markdown(frase + ". Quem ganha costuma contar para os outros; quem perde, quase nunca.")

    # --- tempo ----------------------------------------------------------------------------
    secao("Quanto mais tempo apostando, menos gente fica no lucro",
          "No começo, a sorte pesa mais e muita gente está ganhando. Com o tempo, a parte da casa vai somando.")
    linhas = rodar_tempo(c["valor"], c["odd"], r["prob"], c["por_semana"])
    st.plotly_chart(grafico_tempo(linhas, r["semanas"] * 12 / 52), width="stretch", config=SEM_BARRA)
    if linhas:
        st.caption(f"Depois de 1 mês: cerca de {linhas[0]['tendencia'] * 100:.0f} em 100 estão no lucro. "
                   f"Depois de {linhas[-1]['mes'] // 12} anos: cerca de {linhas[-1]['tendencia'] * 100:.0f} em 100, "
                   f"e o resultado médio chega a {brl_md(linhas[-1]['resultado_medio'], 0)}.")

    # --- guardar --------------------------------------------------------------------------
    secao("E se esse dinheiro fosse guardado?",
          "O mesmo valor, toda semana, numa aplicação simples. É só uma comparação, não uma recomendação de investimento.")
    st.segmented_control("Guardar onde?", list(sim.TAXAS_GUARDAR), key="q_taxa")
    taxa, fonte = sim.TAXAS_GUARDAR[s.q_taxa or PADROES["q_taxa"]]
    co = calcular(c, taxa)["co"]
    st.caption(f"Taxa usada: {fonte}. Valores consultados em 16/10/2026.")
    k = st.columns(3)
    k[0].metric("Guardando", brl(co["total_acumulado"], 0))
    k[1].metric("Apostando (o que volta, em média)", brl(co["total_apostando"], 0))
    k[2].metric("Diferença", brl(co["diferenca"], 0))
    st.plotly_chart(grafico_oportunidade(co), width="stretch", config=SEM_BARRA)

    # --- reapostar --------------------------------------------------------------------------
    secao("E se você reaposta o que volta?",
          "Até aqui, supomos que o dinheiro que volta das apostas é sacado. Na prática, muita gente deixa na conta da bet "
          "e aposta de novo. Aí o total apostado cresce, e a perda também.")
    st.segmented_control("Do dinheiro que volta, quanto você aposta de novo?", list(REAPOSTA), key="q_reaposta")
    fr = REAPOSTA[s.q_reaposta or PADROES["q_reaposta"]]
    fator = r["prob"] * c["odd"]
    rp = sim.reapostar(d["total_apostado"], fator, fr)
    k = st.columns(3)
    k[0].metric("Dinheiro que você colocou", brl(rp["depositado"], 0))
    k[1].metric("Total que acaba apostado", brl(rp["apostado"], 0), help=f"{num(rp['vezes'], 1)} vezes o que você colocou.")
    k[2].metric("Sobra, em média", brl(rp["sobra"], 0))
    st.plotly_chart(grafico_reaposta(d["total_apostado"], fator), width="stretch", config=SEM_BARRA)
    st.caption("Conta da média: cada R\\$ 1 apostado devolve, em média, R\\$ " + num(fator, 4) + ". Quem reaposta tudo "
               "acaba, em média, perdendo todo o dinheiro que colocou, mesmo ganhando várias vezes no caminho.")

    with st.expander("Ver a simulação aposta a aposta (para curiosos)"):
        mc = rodar_mc(c["valor"], c["odd"], r["prob"], r["n"])
        st.markdown("Aqui sorteamos 10.000 vezes as mesmas apostas. Cada linha é uma pessoa: algumas sobem um "
                    "tempo, mas a linha preta (a média de todas) desce sem parar.")
        st.plotly_chart(grafico_trajetorias(mc), width="stretch")


def bloco_estrategias():
    s = st.session_state
    c = s.cen
    st.markdown("Muita gente acredita que existe um jeito de apostar que vence a casa. Aqui, **100 pessoas** fazem "
                f"as mesmas **{c['por_semana'] * sim.HORIZONTES[c['horizonte']]} apostas** do seu cenário "
                f"(base de {brl_md(c['valor'])}, {c['tipo'].lower()}, odd {num(c['odd'])}), cada grupo com uma estratégia. "
                "Os resultados de cada jogo são os mesmos para todas: muda só o jeito de apostar.")
    st.number_input("Quanto dinheiro cada pessoa tem reservado para apostar? (R$)", min_value=10.0, step=50.0,
                    key="q_banca", help="Ninguém aposta mais do que tem. Quando o dinheiro acaba, a pessoa para.")
    banca = s.q_banca
    try:
        linhas = rodar_estrategias(c["valor"], c["odd"], sim.prob_justa(c["odd"], margem_de(c)),
                                   c["por_semana"] * sim.HORIZONTES[c["horizonte"]], banca)
    except sim.ErroValidacao as e:
        st.error(str(e))
        return
    cards = []
    fixo = next(l for l in linhas if l["chave"] == "fixo")
    for l in linhas:
        if l["chave"] == "limite_perda":
            cor, tag = AZUL, "protege"
        elif l["chave"] == "fixo":
            cor, tag = CINZA_TEXTO, "referência"
        elif l["perderam_tudo"] >= 0.5:
            cor, tag = VERMELHO, "muito arriscada"
        else:
            cor, tag = LARANJA, "arriscada"
        desc = l["descricao"]
        if l["chave"] in ("parar_no_lucro", "limite_perda"):
            desc += f" (aqui: {brl_html(banca / 2, 0)})"
        notas = []
        if l["chave"] != "fixo":
            if l["perderam"] < fixo["perderam"] - 0.02 and l["perderam_tudo"] > fixo["perderam_tudo"] + 0.02:
                notas.append(f"⚠️ Menos gente termina no prejuízo, mas <b>{l['perderam_tudo'] * 100:.0f} em 100 perdem "
                             f"tudo</b> (contra {fixo['perderam_tudo'] * 100:.0f} apostando sempre o mesmo valor).")
            if l["resultado_medio"] > fixo["resultado_medio"] + 1 and l["apostado_medio"] < fixo["apostado_medio"] * 0.9:
                if l["chave"] == "limite_perda":
                    notas.append(f"ℹ️ Perde menos porque para no limite: aposta {brl_html(l['apostado_medio'], 0)} no total, "
                                 f"contra {brl_html(fixo['apostado_medio'], 0)}. A casa continua levando a mesma parte de cada aposta.")
                else:
                    notas.append(f"⚠️ A perda média parece menor só porque essas pessoas <b>apostam menos no total</b> "
                                 f"({brl_html(l['apostado_medio'], 0)} contra {brl_html(fixo['apostado_medio'], 0)}). "
                                 "Por real apostado, a casa leva o mesmo.")
        cards.append(
            f'<div class="card" style="--c:{cor}"><span class="tag">{tag}</span><h4>{l["nome"]}</h4>'
            f'<div class="d">{desc}</div>'
            f'<div class="linha"><span>Perderam dinheiro</span><b>{l["perderam"] * 100:.0f} em 100</b></div>'
            f'<div class="linha"><span>Perderam tudo</span><b>{l["perderam_tudo"] * 100:.0f} em 100</b></div>'
            f'<div class="linha"><span>Total apostado (média)</span><b>{brl_html(l["apostado_medio"], 0)}</b></div>'
            f'<div class="linha"><span>Resultado médio</span><b>{brl_html(l["resultado_medio"], 0)}</b></div>'
            f'<div class="linha"><span>De cada {brl_html(100, 0)} apostados, voltam</span>'
            f'<b>{brl_html(l["retorno_por_100"], 0)}</b></div>'
            + "".join(f'<div class="nota">{n}</div>' for n in notas) + "</div>")
    st.markdown(f'<div class="cards">{"".join(cards)}</div>', unsafe_allow_html=True)
    st.plotly_chart(grafico_estrategias(linhas), width="stretch", config=SEM_BARRA)
    st.markdown(
        '<div class="resultado"><div class="rotulo azul">O que isso mostra</div>'
        '<div class="peq"><b>Nenhuma estratégia vence a parte da casa.</b> Em todas, de cada R&#36; 100 apostados voltam '
        "praticamente os mesmos valores. Quando uma estratégia parece \"perder menos\", é porque a pessoa parou antes "
        "e apostou menos no total, ou porque trocou muitas perdas pequenas por poucas perdas enormes. As estratégias só mudam o jeito de perder: dobrar depois de perder ou apostar alto "
        "para recuperar fazem muita gente perder tudo de uma vez. Um <b>limite de perda</b> não dá lucro, mas impede que "
        "a perda passe do valor que você decidiu antes, com calma. As bets autorizadas são obrigadas a oferecer "
        "ferramentas de limite, e dá para bloquear o CPF em gov.br/autoexclusaoapostas.</div></div>",
        unsafe_allow_html=True)


def reiniciar_jogo():
    s = st.session_state
    s.jogo_saldo, s.jogo_hist, s.jogo_casa, s.jogo_casa_hist = JOGO_INICIO, [JOGO_INICIO], 0.0, [0.0]
    s.jogo_acertos, s.jogo_n, s.jogo_ultimo = 0, 0, None
    s.jogo_rng = np.random.default_rng()


def apostar(vezes):
    s = st.session_state
    odd = sim.TIPOS_ODD[s.jogo_tipo or "Jogo equilibrado"]
    prob = sim.prob_justa(odd, margem_de(s.cen))
    for _ in range(vezes):
        if s.jogo_saldo < JOGO_APOSTA:
            break
        acertou, s.jogo_saldo, casa = sim.rodada_do_jogo(s.jogo_rng, odd, prob, JOGO_APOSTA, s.jogo_saldo)
        s.jogo_casa += casa
        s.jogo_n += 1
        s.jogo_acertos += acertou
        s.jogo_hist.append(s.jogo_saldo)
        s.jogo_casa_hist.append(s.jogo_casa)
        s.jogo_ultimo = (acertou, JOGO_APOSTA * (odd - 1) if acertou else -JOGO_APOSTA)


def bloco_jogo():
    s = st.session_state
    if "jogo_saldo" not in s:
        reiniciar_jogo()
    st.markdown(f"Uma **simulação educativa, sem dinheiro de verdade**: você começa com {brl_md(JOGO_INICIO, 0)} fictícios "
                f"e cada clique sorteia uma aposta de {brl_md(JOGO_APOSTA, 0)}. Ao mesmo tempo, outras **1.000 pessoas** "
                "fazem a mesma aposta, e a gente mostra o que acontece com o caixa da casa.")
    st.segmented_control("Tipo de aposta", list(sim.TIPOS_ODD), key="jogo_tipo", disabled=s.jogo_n > 0,
                         format_func=lambda t: f"{t} · odd {num(sim.TIPOS_ODD[t])}",
                         help="Para trocar o tipo, recomece o jogo.")
    b = st.columns([1.2, 1.2, 1, 2])
    acabou = s.jogo_saldo < JOGO_APOSTA
    b[0].button("Sortear 1 aposta", on_click=apostar, args=(1,), disabled=acabou, width="stretch",
                icon=":material/science:")
    b[1].button("Sortear 10 apostas", on_click=apostar, args=(10,), disabled=acabou, width="stretch",
                icon=":material/fast_forward:")
    b[2].button("Recomeçar", on_click=reiniciar_jogo, width="stretch", type="tertiary", icon=":material/refresh:")

    if s.jogo_ultimo:
        acertou, valor = s.jogo_ultimo
        st.markdown(f'<div class="ultimo" style="color:{AZUL if acertou else VERMELHO}">'
                    f'{"✅ Acertou!" if acertou else "❌ Errou."} {"+" if valor > 0 else ""}{brl_html(valor)}</div>',
                    unsafe_allow_html=True)
    dif = s.jogo_saldo - JOGO_INICIO
    st.markdown(
        '<div class="placar">'
        f'<div><div class="r">Seu dinheiro</div><div class="v">{brl_html(s.jogo_saldo)}</div>'
        f'<div class="r" style="color:{AZUL if dif >= 0 else VERMELHO}">{"+" if dif > 0 else ""}{brl_html(dif)} desde o início</div></div>'
        f'<div><div class="r">Você acertou</div><div class="v">{s.jogo_acertos} de {s.jogo_n}</div>'
        f'<div class="r">{pc(s.jogo_acertos / s.jogo_n, 0) if s.jogo_n else "–"} das apostas</div></div>'
        f'<div><div class="r">Caixa da casa (1.000 pessoas)</div><div class="v">{brl_html(s.jogo_casa, 0)}</div>'
        f'<div class="r">{"nenhuma aposta ainda" if s.jogo_n == 0 else "a casa está ganhando" if s.jogo_casa > 0 else "a casa está perdendo, por enquanto"}</div></div>'
        "</div>", unsafe_allow_html=True)
    if s.jogo_n:
        g1, g2 = st.columns(2)
        g1.plotly_chart(grafico_jogo(s.jogo_hist, "Seu dinheiro: sobe e desce", AZUL, ref=JOGO_INICIO),
                        width="stretch", config=SEM_BARRA)
        g2.plotly_chart(grafico_jogo(s.jogo_casa_hist, "Caixa da casa: sobe quase sempre", VERMELHO),
                        width="stretch", config=SEM_BARRA)
    if acabou:
        st.error(f"Seu dinheiro do jogo acabou depois de {s.jogo_n} apostas, e você acertou {s.jogo_acertos} delas. "
                 "A casa não precisou adivinhar nenhum resultado: só cobrou a parte dela em cada aposta.")
    if s.jogo_n >= 20:
        apostado = s.jogo_n * JOGO_APOSTA
        voltou = apostado + dif
        casa_100 = 100 * s.jogo_casa / (s.jogo_n * 1000 * JOGO_APOSTA)
        st.markdown(
            '<div class="resultado"><div class="rotulo azul">Resumo das suas ' + str(s.jogo_n) + ' apostas</div>'
            f'<div class="peq">Você apostou <b>{brl_html(apostado, 0)}</b> no total e voltaram <b>{brl_html(voltou, 0)}</b>: '
            f'está com <b>{brl_html(abs(dif), 0)} {"a mais" if dif > 0 else "a menos"}</b> do que começou. '
            f'Com as 1.000 pessoas juntas, a casa ficou com <b>{brl_html(s.jogo_casa, 0)}</b>, cerca de '
            f'<b>{brl_html(casa_100)}</b> de cada {brl_html(100, 0)} apostados. '
            + ("Você pode estar com sorte agora, mas a casa não depende de sorte: a parte dela vem de todo mundo."
               if dif > 0 else "A casa não precisou acertar nenhum resultado: ela ganha com a soma de todas as apostas.")
            + "</div></div>", unsafe_allow_html=True)


def bloco_multipla():
    s = st.session_state
    st.markdown("Na aposta múltipla, você junta vários palpites num bilhete só. As odds se multiplicam e o prêmio "
                "fica enorme, mas **o bilhete só paga se todos acertarem**.")
    c1, c2 = st.columns([2, 1])
    c1.segmented_control("Tipo de cada palpite", list(sim.TIPOS_ODD), key="mult_tipo",
                         format_func=lambda t: f"{t} · odd {num(sim.TIPOS_ODD[t])}")
    c2.slider("Quantos jogos no bilhete", 1, 8, key="mult_jogos")
    odd = sim.TIPOS_ODD[s.mult_tipo or "Favorito"]
    k = s.mult_jogos
    m_c = margem_de(s.cen)
    b = sim.bilhete_multiplo(odd, k, m_c)
    um_em = 1 / b["chance"] if b["chance"] > 0 else float("inf")
    st.markdown(
        f'<div class="resultado"><div class="rotulo">Bilhete com {k} jogo{"s" if k > 1 else ""}</div>'
        f'<div class="grande">R&#36; 10 viram {brl_html(10 * b["odd_total"])} se acertar tudo. '
        f'Mas a chance de acertar tudo é de <span class="neg">{pc(b["chance"], 1 if b["chance"] >= 0.001 else 2)}</span>: '
        f'cerca de 1 bilhete em cada {f"{um_em:,.0f}".replace(",", ".")}.</div>'
        + f'<div class="peq">Além disso, a parte da casa também se multiplica: num bilhete de {k} jogo{"s" if k > 1 else ""}, de cada '
        f'R&#36; 100 apostados voltam em média {brl_html(b["retorno_por_100"])} (numa aposta simples, {brl_html(100 / (1 + m_c))}).</div></div>',
        unsafe_allow_html=True)
    m = st.columns(3)
    m[0].metric("Odd do bilhete", num(b["odd_total"]))
    m[1].metric("Chance de acertar tudo", pc(b["chance"], 2))
    m[2].metric("De cada R$ 100, voltam", brl(b["retorno_por_100"]))
    st.plotly_chart(grafico_multipla(odd, k, m_c), width="stretch", config=SEM_BARRA)


def usar_margem(m):
    st.session_state.q_margem = round(min(max(m * 100, 2.0), 15.0), 1)
    aplicar_cenario()
    st.session_state.margem_aplicada = True


def grafico_odds(info, nomes):
    cores = [AZUL, CINZA, LARANJA]
    fig = go.Figure()
    for nome, v, cor in zip(nomes, info["implicitas"], cores):
        fig.add_bar(y=[""], x=[v * 100], orientation="h", name=nome, marker_color=cor,
                    marker_line=dict(color="#fcfcfb", width=2), text=[f"{nome}: {pc(v)}"], textposition="inside",
                    insidetextanchor="middle", textfont=dict(color="#fff"),
                    hovertemplate=f"{nome}: %{{x:.1f}}%<extra></extra>")
    fig.add_vline(x=100, line_color=TINTA, line_width=2, annotation_text="100%", annotation_position="top")
    fig = estilo(fig, f"As chances que as odds pagam somam {pc(info['soma'])}", altura=210, moeda=False)
    fig.update_layout(barmode="stack", showlegend=False, margin=dict(t=60, b=8, l=8, r=8))
    fig.update_xaxes(ticksuffix="%", range=[0, max(110, info["soma"] * 100 + 5)], title="")
    fig.update_yaxes(visible=False)
    return fig


def bloco_odds():
    s = st.session_state
    st.markdown("Toda odd esconde uma chance: **1 ÷ odd**. Digite as odds dos três resultados de um jogo e veja quanto a "
                "casa embute de margem. Se as chances somam mais de 100%, a diferença é a parte da casa.")
    c = st.columns(3)
    c[0].number_input("Odd da vitória do mandante", min_value=1.01, step=0.05, format="%.2f", key="calc_o1")
    c[1].number_input("Odd do empate", min_value=1.01, step=0.05, format="%.2f", key="calc_o2")
    c[2].number_input("Odd da vitória do visitante", min_value=1.01, step=0.05, format="%.2f", key="calc_o3")
    nomes = ["Mandante", "Empate", "Visitante"]
    odds = [s.calc_o1, s.calc_o2, s.calc_o3]
    try:
        info = sim.ler_odds(odds)
    except sim.ErroValidacao as e:
        st.error(str(e))
        return
    st.markdown(
        f'<div class="resultado"><div class="rotulo">Margem deste jogo</div>'
        f'<div class="grande">A casa embute <span class="neg">{pc(info["margem"])}</span> de margem neste jogo.</div>'
        f'<div class="peq">Num mercado sem margem, as três chances somariam exatamente 100%. Aqui somam {pc(info["soma"])}. '
        f'Na prática, de cada {brl_html(100, 0)} apostados neste jogo, voltam em média cerca de '
        f'{brl_html(100 / (1 + info["margem"]))}.</div></div>', unsafe_allow_html=True)
    st.plotly_chart(grafico_odds(info, nomes), width="stretch", config=SEM_BARRA)
    tabela = [{"Resultado": n, "Odd": num(o), "Chance que a odd paga (1 ÷ odd)": pc(i),
               "Chance sem a margem": pc(j)} for n, o, i, j in zip(nomes, odds, info["implicitas"], info["justas"])]
    st.dataframe(tabela, hide_index=True, width="stretch")
    st.caption("A \"chance sem a margem\" divide cada chance pela soma. É uma estimativa, não a chance verdadeira do jogo, "
               "que ninguém conhece. Odds só devem ser digitadas para entender o preço, nunca como palpite.")
    st.button(f"Usar a margem de {pc(info['margem'])} no simulador", on_click=usar_margem, args=(info["margem"],),
              icon=":material/input:")
    if s.pop("margem_aplicada", False):
        st.success("Pronto. A aba **Quanto custa apostar** já está usando essa margem.")


def aba_simulador():
    st.markdown("Veja, com números simples, **o que acontece com o seu dinheiro** quando você aposta. "
                "Não é previsão de jogo nem indicação de aposta.")
    t1, t2, t3, t4, t5 = st.tabs(["💸 Quanto custa apostar", "🎯 Estratégias", "🎮 Aposte rodada a rodada",
                                  "🎟️ Bilhete múltiplo", "🧮 Ler as odds de um jogo"])
    with t1:
        bloco_quanto_custa()
    with t2:
        bloco_estrategias()
    with t3:
        bloco_jogo()
    with t4:
        bloco_multipla()
    with t5:
        bloco_odds()

    with st.expander("Como calculamos (hipóteses)"):
        poup, selic = sim.TAXAS_GUARDAR.values()
        st.markdown(
            "- **Chance de acertar:** tirada da própria odd, sem a parte da casa: (1 ÷ odd) ÷ (1 + margem). A margem "
            "padrão é 5%, próxima do exemplo da nossa base (odds 2,10 / 3,40 / 3,60 somam 104,8%), e pode ser ajustada. "
            "Não é a chance verdadeira do jogo, que ninguém conhece.\n"
            "- Com margem *m*, de cada R\\$ 100 apostados voltam em média R\\$ 100 ÷ (1 + *m*). Na prática, a margem "
            "costuma ser maior em zebras e em mercados menos movimentados (o chamado *favorite-longshot bias*); o "
            "simulador usa a mesma margem para todas as odds, o que é uma simplificação.\n"
            "- **100 pessoas** e **tempo**: conta exata pela distribuição binomial (número de acertos em *n* apostas). "
            "**Estratégias**, **aposta a aposta** e **jogo**: sorteios (simulação de Monte Carlo).\n"
            "- Cada aposta é **independente** das outras; não entram bônus, promoções, impostos nem limites das plataformas.\n"
            "- Fora da seção \"reapostar\", supomos que o dinheiro que volta **não é reapostado**. Na seção, a conta é a "
            "da média: total apostado = colocado ÷ (1 − fração reapostada × retorno por real).\n"
            f"- **Guardar** (valores consultados em 16/10/2026): poupança, {poup[1]}; Tesouro Selic ou CDB, {selic[1]}. "
            "Não é recomendação de investimento.\n"
            "- Tipos de aposta (odds 1,50 / 2,20 / 5,00) são ilustrativos, sem relação com jogos reais.")


# ----------------------------------------------------------------------- Sobre

@st.cache_data
def fontes_da_base():
    """Fontes citadas nas fichas (conhecimento/base.md), sem repetir e sem 'elaboração própria'."""
    base = (RAIZ / "conhecimento" / "base.md").read_text(encoding="utf-8")
    vistas, chaves = [], set()
    for bloco in re.findall(r"\*\*Fontes:\*\*(.*?)(?=\n## |\Z)", base, re.S):
        for linha in re.findall(r"^- (.+)$", bloco, re.M):
            linha = linha.strip()
            chave = linha.split(" — ")[0]
            if "elaboração própria" not in linha and chave not in chaves:
                chaves.add(chave)
                vistas.append(linha)
    return vistas


def aba_sobre():
    s = st.session_state
    st.markdown("### Sobre esta ferramenta")
    st.markdown(
        "Assistente educativo sobre apostas esportivas criado na disciplina **Projetos III (FGV EESP)** pelo **Grupo 3**: "
        "Bernardo Nappo, Luc Le Corre, Gustavo Lamarca, Tomás Battaus e Thomás Mariano. É para maiores de 18 anos que "
        "já apostam e querem entender o que os números dizem.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**O que a ferramenta faz**")
        st.markdown("- explica como funcionam odds, margem da casa e apostas múltiplas;\n"
                    "- mostra, com contas, quanto apostar pode custar ao longo do tempo;\n"
                    "- explica vieses comuns, como a falácia do jogador e a perseguição de perdas;\n"
                    "- indica onde buscar apoio e informação oficial.")
    with c2:
        st.markdown("**O que a ferramenta não faz**")
        st.markdown("- não dá palpites nem indica jogos, casas de apostas ou estratégias;\n"
                    "- não ensina a ganhar mais nem a recuperar perdas;\n"
                    "- não dá aconselhamento financeiro, jurídico ou psicológico, nem faz diagnóstico;\n"
                    "- não acessa odds em tempo real nem dados da sua conta.")
    st.markdown("**Limitações**")
    st.markdown(
        "- As respostas da conversa são escritas por um modelo de linguagem a partir da nossa base de conhecimento e "
        "podem conter erros. Os números do simulador são calculados pelo código, não pelo modelo.\n"
        "- O simulador usa cenários hipotéticos e hipóteses simplificadas (veja *Como calculamos* na aba Simulador).\n"
        "- Datas: base de conhecimento de 11/09/2026; taxas de \"guardar\" consultadas em 16/10/2026; "
        "última atualização do app em 23/10/2026.")
    st.markdown("**Privacidade**")
    st.markdown("Para melhorar a ferramenta, registramos de forma **anônima** as perguntas feitas e as avaliações 👍/👎. "
                "Não registramos nome, e-mail, endereço IP nem nada que identifique você. Não escreva dados pessoais "
                "nas perguntas.")
    with st.expander("Fontes utilizadas"):
        st.markdown("\n".join(f"- {f}" for f in fontes_da_base()))
        poup, selic = sim.TAXAS_GUARDAR.values()
        st.markdown(f"- Taxas de \"guardar\": poupança, {poup[1]}; Tesouro Selic ou CDB, {selic[1]}.\n"
                    "- Exemplos e cálculos de elaboração própria do grupo, conferidos em testes automatizados.")
    st.info("**Precisa de apoio?** O CAPS, pelo SUS, atende de graça questões ligadas a jogo. Em "
            "**gov.br/autoexclusaoapostas** há um autoteste e o bloqueio do CPF em todas as bets autorizadas.",
            icon=":material/support:")
    senha = llm._ler("EQUIPE_SENHA")
    if senha:
        with st.expander("Área da equipe"):
            if st.text_input("Senha da equipe", type="password", key="equipe_senha") == senha:
                st.download_button(f"Baixar registro anônimo ({registro.total_linhas()} linhas)",
                                   registro.conteudo(), file_name="interacoes.csv", mime="text/csv",
                                   icon=":material/download:")
                st.caption("O registro some quando o app reinicia ou recebe um commit novo: baixe ao fim de cada "
                           "sessão de testes.")


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
    "<p>Converse sobre odds, chances e riscos, ou simule o que acontece com o seu dinheiro ao longo do tempo.</p></div>",
    unsafe_allow_html=True)
st.markdown('<div class="aviso"><b>Não damos palpites</b>, não indicamos casas de apostas e não fazemos '
            "aconselhamento financeiro ou psicológico. Se apostar estiver pesando, procure um CAPS/SUS ou acesse "
            "<b>gov.br/autoexclusaoapostas</b>.</div>", unsafe_allow_html=True)

aba_chat_, aba_sim_, aba_sobre_ = st.tabs([ABA_CHAT, ABA_SIM, ABA_SOBRE], key="abas", on_change="rerun")
with aba_chat_:
    aba_chat()
with aba_sim_:
    aba_simulador()
with aba_sobre_:
    aba_sobre()
