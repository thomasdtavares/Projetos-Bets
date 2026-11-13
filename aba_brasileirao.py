"""Painel esportivo educativo: caixa fictício, rodadas e comparação de cenários."""
import base64
import json
from datetime import date
from html import escape
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

import brasileirao as bra

RAIZ = Path(__file__).parent
AZUL, VERMELHO, CINZA = "#2a78d6", "#cf4651", "#687789"
CSS = """<style>
.bra-top {background:linear-gradient(120deg,#112c4b,#214d76);color:white;padding:22px 26px;border-radius:18px;margin:18px 0 16px;}
.bra-top h2 {color:white!important;font-size:1.55rem;margin:6px 0;padding:0;}
.bra-top p {color:#d4e3f2;margin:0;font-size:.94rem;}
.bra-tag {font-size:.73rem;letter-spacing:.1em;text-transform:uppercase;font-weight:700;color:#b7d5f3;}
.bra-match {display:grid;grid-template-columns:1fr 48px 1fr;align-items:center;padding:20px 8px;gap:12px;}
.bra-team {display:flex;align-items:center;justify-content:center;gap:12px;font-size:1.1rem;font-weight:700;color:#20334a;}
.bra-team img,.bra-badge {width:60px;height:60px;object-fit:contain;border-radius:10px;background:white;padding:5px;}
.bra-versus {text-align:center;color:#7c8996;font-size:.8rem;letter-spacing:.08em;}
.bra-odds {display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:0 0 14px;}
.bra-odd {border:1px solid #dce5ef;border-radius:12px;padding:12px 10px;text-align:center;background:#f7faff;}
.bra-odd b {display:block;font-size:1.5rem;color:#173f6b;margin:4px 0;}
.bra-odd small {display:block;color:#687789;font-size:.76rem;}
.bra-label {font-size:.84rem;color:#36485d;}
.bra-result {border:1px solid #dde5ed;border-left:4px solid var(--cor);border-radius:12px;padding:15px 18px;margin:10px 0;background:white;}
.bra-result .meta {font-size:.8rem;color:#687789;margin-bottom:5px;}
.bra-result .res {font-weight:700;color:#23374f;margin:5px 0;}
.bra-result .finance {font-size:.88rem;line-height:1.65;color:#42546a;}
.bra-result .net {color:var(--cor);font-weight:700;}
@media(max-width:640px){.bra-top{padding:18px}.bra-match{gap:4px}.bra-team{flex-direction:column;text-align:center;font-size:.95rem;gap:7px}.bra-odds{gap:6px}.bra-odd{padding:10px 4px}.bra-odd b{font-size:1.3rem}}
</style>"""


def moeda(valor):
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def dinheiro_md(valor):
    return moeda(valor).replace("$", r"\$")


def dinheiro_html(valor):
    return escape(moeda(valor)).replace("$", "&#36;")


def numero(valor):
    return f"{valor:.2f}".replace(".", ",")


def data_br(texto):
    return date.fromisoformat(texto[:10]).strftime("%d/%m/%Y")


def nome_resultado(codigo, jogo):
    return {"1": f"Vitória do {jogo['mandante']}", "X": "Empate",
            "2": f"Vitória do {jogo['visitante']}"}[codigo]


@st.cache_data(show_spinner=False)
def escudos_html():
    pasta = RAIZ / "dados" / "escudos"
    registros = json.loads((pasta / "fontes.json").read_text(encoding="utf-8"))
    return {nome: '<img alt="Escudo do ' + escape(nome, quote=True) + '" src="data:image/jpeg;base64,' +
            base64.b64encode((pasta / info["arquivo"]).read_bytes()).decode() + '">' for nome, info in registros.items()}


def preservar_estado():
    padroes = {"bra_mandante": "Flamengo", "bra_visitante": "Fluminense", "bra_escolha": "1",
               "bra_valor": 20.0, "bra_modo": "Jogo individual"}
    for chave, padrao in padroes.items():
        st.session_state[chave] = st.session_state.get(chave, padrao)
    st.session_state.setdefault("bra_sessao", bra.nova_sessao())
    st.session_state.setdefault("bra_fila", [])
    st.session_state.setdefault("bra_comparacao", None)


def reiniciar():
    st.session_state.bra_sessao = bra.nova_sessao()
    st.session_state.bra_fila = []
    st.session_state.bra_comparacao = None
    st.session_state.bra_valor = 20.0


def executar(apostas):
    st.session_state.bra_sessao = bra.executar_rodada(st.session_state.bra_sessao, apostas)
    st.session_state.bra_fila = []
    st.session_state.bra_comparacao = None


def estilo(fig, eixo_y):
    fig.update_layout(height=320, margin=dict(l=12,r=20,t=45,b=20), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter, sans-serif",color="#33475b"),
                      yaxis_title=eixo_y, showlegend=False, separators=",.", hovermode="closest")
    fig.update_yaxes(gridcolor="#e6ecf2",zeroline=False)
    fig.update_xaxes(showgrid=False,zeroline=False)
    return fig


def grafico_saldo(sessao):
    saldos = [bra.SALDO_INICIAL / 100] + [r["depois"] / 100 for r in sessao["rodadas"]]
    fig = go.Figure(go.Scatter(x=list(range(len(saldos))),y=saldos,mode="lines+markers",
                             line=dict(color=AZUL,width=3),marker=dict(size=8),
                             hovertemplate="Após envio %{x}<br>Saldo: R$ %{y:,.2f}<extra></extra>"))
    fig.add_hline(y=500,line_dash="dot",line_color=CINZA,annotation_text="Início: R$ 500",
                  annotation_position="top left")
    fig.update_xaxes(title="Envio individual ou rodada",dtick=1 if len(saldos)<20 else None)
    fig.update_yaxes(rangemode="tozero",tickprefix="R$ ")
    return estilo(fig, "Saldo fictício")


def grafico_comparacao(comparacao, saldo):
    fig = go.Figure(go.Histogram(x=[s/100 for s in comparacao["saldos"]],nbinsx=25,
                               marker_color="#9dbce2",name="Simulações",
                               hovertemplate="Saldo: %{x}<br>Simulações: %{y}<extra></extra>"))
    fig.add_vline(x=500,line_dash="dot",line_color=CINZA,annotation_text="Início: R$ 500",annotation_position="top left")
    fig.add_vline(x=saldo/100,line_color="#cf4651",line_width=3,annotation_text="Seu saldo",annotation_position="top right")
    fig.update_xaxes(title="Saldo final fictício",tickprefix="R$ ")
    return estilo(fig,"Quantidade de simulações")


def painel_saldo(sessao):
    resumo = bra.resumo_sessao(sessao)
    a,b,c = st.columns(3)
    a.metric("Saldo disponível",moeda(resumo["saldo"]/100))
    b.metric("Lucro / prejuízo",moeda(resumo["liquido"]/100))
    c.metric("Acertos / apostas",f"{resumo['acertos']} / {resumo['jogos']}")
    st.caption("Saldo inicial: R\\$ 500 · Sem reposições · Dinheiro fictício. Acertos e lucro são medidas diferentes.")


def mostrar_resultados(sessao):
    if not sessao["rodadas"]:
        return
    ultima = sessao["rodadas"][-1]
    st.markdown(f"### Resultado do envio {ultima['numero']}")
    st.caption(f"{'Jogo individual' if len(ultima['resultados']) == 1 else 'Rodada'} · "
               f"Total colocado: {dinheiro_md(ultima['apostado']/100)} · Retorno: {dinheiro_md(ultima['retorno']/100)}")
    for r in ultima["resultados"]:
        cor = AZUL if r["acertou"] else VERMELHO
        st.markdown(f'<div class="bra-result" style="--cor:{cor}"><div class="meta">'
                    f'{escape(r["mandante"])} × {escape(r["visitante"])} · Odd {numero(r["odd"])}'
                    f'</div><div class="res">{escape(nome_resultado(r["resultado"],r))} · resultado sorteado</div>'
                    f'<div class="finance">Sua escolha: {escape(nome_resultado(r["escolha"],r))}<br>'
                    f'Valor: {dinheiro_html(r["valor"])} · Retorno total: {dinheiro_html(r["retorno"])}<br>'
                    f'<span class="net">{"Lucro" if r["acertou"] else "Prejuízo"}: {dinheiro_html(abs(r["liquido"]))}</span></div></div>',unsafe_allow_html=True)
    st.caption("Retorno total inclui o valor colocado. Lucro ou prejuízo = retorno − valor da aposta.")


def mostrar_analises(sessao):
    if not sessao["rodadas"]:
        return
    st.markdown("### Seu saldo ao longo da sessão")
    st.plotly_chart(grafico_saldo(sessao),width="stretch",config={"displayModeBar":False},key="bra_grafico_saldo")
    with st.expander("E se você repetisse essas apostas? · 1.000 simulações"):
        st.write("Compare seu saldo com outras 1.000 versões do mesmo roteiro: mesmos confrontos, escolhas, valores e odds.")
        if st.button("Comparar com 1.000 simulações",key="bra_comparar"):
            st.session_state.bra_comparacao = bra.comparar_sessoes(sessao)
        comp = st.session_state.bra_comparacao
        if comp:
            cols = st.columns(4)
            for col,(rotulo,chave) in zip(cols,[("No lucro","lucro"),("No prejuízo, com saldo","prejuizo"),("Saldo zerado","zeradas"),("Mesmo saldo inicial","empate")]):
                col.metric(rotulo,str(comp[chave]))
            st.plotly_chart(grafico_comparacao(comp,sessao["saldo"]),width="stretch",config={"displayModeBar":False},key="bra_grafico_comparacao")
            st.markdown(f"Seu saldo foi igual ou superior ao de **{numero(comp['percentil_seu'])}%** das simulações. "
                        f"O saldo mediano foi **{dinheiro_md(comp['mediana']/100)}**.")
            if comp["impedidas"]:
                st.info(f"{comp['impedidas']} simulações não conseguiram financiar alguma rodada e pararam ali, preservando o saldo restante. Esse número pode incluir sessões com saldo zero.")
        st.caption("Cada versão começa com R$ 500 e precisa ter saldo para a rodada inteira antes de receber retornos. "
                   "As apostas escolhidas aqui ficam fixas, mesmo que você tenha decidido depois de ganhar ou perder. "
                   "Comparação hipotética sob as chances das odds; não é previsão de jogos. O conjunto permanece estável até você alterar o roteiro.")
    with st.expander("Histórico completo desta sessão"):
        resumo = bra.resumo_sessao(sessao)
        st.caption(f"Total colocado: {dinheiro_md(resumo['apostado']/100)} · Total recebido: {dinheiro_md(resumo['retorno']/100)}. "
                   "O total colocado pode superar os R$ 500 iniciais porque retornos podem ser usados novamente.")
        linhas = [{"Envio":rodada["numero"],"Confronto":f"{r['mandante']} × {r['visitante']}",
                   "Escolha":nome_resultado(r["escolha"],r),"Resultado":nome_resultado(r["resultado"],r),
                   "Valor":moeda(r["valor"]),"Retorno":moeda(r["retorno"]),"Lucro / prejuízo":moeda(r["liquido"])}
                  for rodada in sessao["rodadas"] for r in rodada["resultados"]]
        st.dataframe(linhas,hide_index=True,width="stretch")


def construtor(jogos):
    s = st.session_state
    sessao = s.bra_sessao
    times = sorted({j["mandante"] for j in jogos})
    st.radio("Como quer simular?",["Jogo individual","Montar rodada"],horizontal=True,key="bra_modo")
    rodada = s.bra_modo == "Montar rodada"
    with st.container(border=True):
        st.markdown("#### Escolha seu confronto")
        c1,c2 = st.columns(2)
        mandante = c1.selectbox("Mandante · joga em casa",times,key="bra_mandante")
        adversarios = [t for t in times if t != mandante]
        if s.bra_visitante not in adversarios:
            s.bra_visitante = adversarios[0]
        visitante = c2.selectbox("Visitante · joga fora",adversarios,key="bra_visitante")
        jogo = next(j for j in jogos if j["mandante"] == mandante and j["visitante"] == visitante)
        try:
            escudos = escudos_html()
        except (OSError,ValueError,KeyError):
            escudos = {}
        st.markdown('<div class="bra-match">' + ''.join(
            ('<div class="bra-versus">×</div>' if i else '') + f'<div class="bra-team">{escudos.get(time, "")}<span>{escape(time)}</span></div>'
            for i,time in enumerate((mandante,visitante))) + '</div>',unsafe_allow_html=True)
        disponivel = jogo["odd_1"] is not None
        if disponivel:
            st.caption(f"{jogo['tipo']} · data na fonte: {data_br(jogo['data_fonte'])}")
            chances = bra.probabilidades(jogo)
            st.markdown('<div class="bra-odds">' + ''.join(
                f'<div class="bra-odd"><span class="bra-label">{rotulo}</span><b>{numero(odd)}</b><small>{numero(p*100)}% no sorteio</small></div>'
                for rotulo,odd,p in zip(("Vitória (1)","Empate (X)","Derrota (2)"),bra.odds_do_jogo(jogo),chances)) + '</div>',unsafe_allow_html=True)
        else:
            st.info("Este confronto está sem cotação na coleta. Escolha outro para simular.")
        st.caption(f"Vitória e derrota são do mandante, {mandante}. As chances são hipóteses calculadas pelas odds.")
        escolha = st.radio("Seu resultado",bra.RESULTADOS,horizontal=True,key="bra_escolha",disabled=not disponivel,
                           format_func=lambda c:{"1":"Vitória (1)","X":"Empate (X)","2":"Derrota (2)"}[c])
        valor = st.number_input("Valor fictício (R$)",min_value=0.01,max_value=float(bra.MAX_VALOR),step=1.0,format="%.2f",key="bra_valor",disabled=not disponivel)
        aposta = {"jogo":jogo,"escolha":escolha,"valor":valor}
        erro = None
        if disponivel:
            try:
                b = bra.calcular_bilhete(jogo,escolha,valor)
                st.markdown(f"Se acertar: **{dinheiro_md(b['retorno_possivel'])}** de retorno, com **{dinheiro_md(b['lucro_possivel'])}** de lucro. "
                            f"Se errar: **{dinheiro_md(valor)}** de prejuízo.")
                media = bra.retorno_medio(jogo)
                st.info(f"**Na média:** de cada {dinheiro_md(100)} colocados neste jogo, voltam "
                        f"**{dinheiro_md(media['retorno_medio'])}**, seja qual for o resultado escolhido. "
                        f"Os {dinheiro_md(media['perda_media'])} restantes ficam com a casa: é a margem embutida nas odds "
                        f"(as três chances somam {numero(media['soma_chances']*100)}%, e não 100%).",
                        icon=":material/percent:")
                bra.preparar_rodada([*s.bra_fila,aposta] if rodada else [aposta],sessao["saldo"])
            except bra.ErroBrasileirao as exc:
                erro = str(exc)
                st.info(erro.replace("$",r"\$"))
        if rodada:
            if st.button("Adicionar à rodada",key="bra_adicionar",width="stretch",disabled=not disponivel or erro is not None):
                s.bra_fila = [*s.bra_fila,aposta]
                st.rerun()
        elif st.button("Simular jogo",key="bra_simular",type="primary",width="stretch",disabled=not disponivel or erro is not None):
            executar([aposta])
            st.rerun()
    if rodada:
        st.markdown(f"#### Sua rodada · {len(s.bra_fila)} de 10 jogos")
        st.caption("Apostas separadas, com valor e resultado próprios. É uma rodada montada por você, sem vínculo com o calendário oficial.")
        for i,a in enumerate(s.bra_fila):
            jogo = a["jogo"]
            with st.container(border=True):
                c1,c2 = st.columns([4,1])
                c1.markdown(f"**{jogo['mandante']} × {jogo['visitante']}**")
                c1.caption(f"{nome_resultado(a['escolha'],jogo)} · {dinheiro_md(a['valor'])}")
                if c2.button("Remover",key=f"bra_remover_{i}"):
                    s.bra_fila = [a for j,a in enumerate(s.bra_fila) if j != i]
                    st.rerun()
        total = sum(bra.centavos(a["valor"]) for a in s.bra_fila)
        st.markdown(f"Total da rodada: **{dinheiro_md(total/100)}** · Saldo disponível: **{dinheiro_md(sessao['saldo']/100)}**")
        if st.button("Simular rodada",key="bra_simular_rodada",type="primary",width="stretch",disabled=not s.bra_fila or total>sessao["saldo"]):
            executar(s.bra_fila)
            st.rerun()
    elif s.bra_fila:
        st.caption("Você tem uma rodada em preparação. Ela será descartada se simular um jogo individual.")


def renderizar():
    st.markdown(CSS,unsafe_allow_html=True)
    st.markdown('<div class="bra-top"><span class="bra-tag">Brasileirão 2026 · simulação educativa</span>'
                '<h2>Seu jogo. Seus números.</h2><p>Comece com R&#36; 500 fictícios e acompanhe o efeito de cada escolha no saldo.</p></div>',unsafe_allow_html=True)
    try:
        jogos = bra.carregar_jogos()
    except (OSError,ValueError,KeyError):
        st.error("Não foi possível carregar a base do Brasileirão.")
        return
    sessao = st.session_state.bra_sessao
    painel_saldo(sessao)
    st.caption("380 confrontos · 329 com odds · Coleta de 23/10/2026 · Sem atualização ao vivo.")
    if sessao["encerrada"]:
        st.markdown("### Resumo da sessão encerrada")
        if sessao["saldo"] == 0:
            st.info("Seu saldo fictício chegou a zero. Esta sessão terminou; veja o resumo e as comparações abaixo.")
        resumo = bra.resumo_sessao(sessao)
        st.markdown(f"Você fez **{resumo['jogos']} apostas**, acertou **{resumo['acertos']}** e terminou com "
                    f"**{dinheiro_md(resumo['saldo']/100)}**. Lucro ou prejuízo: **{dinheiro_md(resumo['liquido']/100)}**.")
        st.button("Começar nova sessão com R$ 500",key="bra_reiniciar",on_click=reiniciar,type="primary")
        st.caption("Uma nova sessão limpa o histórico e os gráficos anteriores.")
    else:
        construtor(jogos)
    sessao = st.session_state.bra_sessao
    mostrar_resultados(sessao)
    mostrar_analises(sessao)
    if sessao["rodadas"] and not sessao["encerrada"]:
        if st.button("Encerrar sessão e ver resumo",key="bra_encerrar"):
            st.session_state.bra_sessao = {**sessao,"encerrada":True}
            st.session_state.bra_fila = []
            st.rerun()
    with st.expander("Como funciona · odds, sorteios e fontes"):
        st.write("Vitória, empate e derrota são sorteados com chances proporcionais a 1 ÷ odd, normalizadas para somarem 100%. "
                 "Isso é uma hipótese para a simulação, não uma previsão. Não geramos placares nem usamos o resultado real dos jogos históricos.")
        st.write("Por que, na média, sempre se perde: somando 1 ÷ odd dos três resultados, os jogos desta base dão entre "
                 "104,7% e 113,7% (média de 106,9%). O que passa de 100% é a margem da casa. Com as chances do sorteio, "
                 "cada R\\$ 100 colocados devolvem em média R\\$ 100 ÷ essa soma, qualquer que seja o resultado escolhido. "
                 "Acertar alguns jogos é comum; ficar no lucro depois de muitas apostas é cada vez menos provável.")
        st.write("Cada rodada precisa caber no saldo antes de receber retornos. Ao zerar, a sessão termina. "
                 "Não há reposições de dinheiro. Os R$ 500 voltam somente ao começar uma nova sessão.")
        st.caption("Base: 309 confrontos históricos, 20 com odds pré-jogo registradas e 51 sem cotação. "
                   "Coleta consolidada em 23/10/2026, 16h24 de Brasília, sem consulta ao vivo. "
                   "As datas são referências das fontes. Sem bônus, impostos ou comissões. Histórico temporário, mantido enquanto esta sessão estiver ativa.")
        st.markdown("Escudos: [página oficial dos clubes na CBF](https://www.cbf.com.br/futebol-brasileiro/times/campeonato-brasileiro/serie-a/2026).")
