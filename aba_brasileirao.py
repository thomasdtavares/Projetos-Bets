"""Interface de Apostas Brasileirão: dinheiro fictício e odds de uma coleta datada."""
from datetime import date

import streamlit as st

import brasileirao as bra


def moeda(valor):
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def dinheiro_md(valor):
    return moeda(valor).replace("$", r"\$")


def numero(valor):
    return f"{valor:.2f}".replace(".", ",")


def data_br(texto):
    return date.fromisoformat(texto[:10]).strftime("%d/%m/%Y")


def nome_resultado(codigo, jogo):
    return {"1": f"Vitória do {jogo['mandante']}", "X": "Empate",
            "2": f"Vitória do {jogo['visitante']}"}[codigo]


def preservar_estado():
    # Os widgets sobrevivem à navegação mesmo quando o Streamlit não renderiza a aba.
    padroes = {"bra_mandante": "Flamengo", "bra_visitante": "Fluminense",
               "bra_escolha": "1", "bra_valor": 20.0}
    for chave, padrao in padroes.items():
        st.session_state[chave] = st.session_state.get(chave, padrao)
    st.session_state.setdefault("bra_historico", [])
    st.session_state.setdefault("bra_contador", 0)


def mostrar_resultado():
    historico = st.session_state.bra_historico
    if not historico:
        return
    ultimo = historico[0]
    st.markdown("### Última simulação")
    st.caption(f"Simulação {ultimo['numero']} · {ultimo['mandante']} × {ultimo['visitante']} · "
               f"Escolha: {nome_resultado(ultimo['escolha'], ultimo)} · Odd {numero(ultimo['odd'])}")
    texto = f"Resultado sorteado: **{nome_resultado(ultimo['resultado'], ultimo)}**. "
    if ultimo["acertou"]:
        st.success(texto + f"Sua seleção acertou. Lucro fictício de **{dinheiro_md(ultimo['liquido'])}**.")
    else:
        st.error(texto + f"Sua seleção perdeu. Prejuízo fictício de **{dinheiro_md(-ultimo['liquido'])}**.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Valor simulado", moeda(ultimo["valor"]))
    c2.metric("Retorno total", moeda(ultimo["retorno"]))
    c3.metric("Lucro / prejuízo", moeda(ultimo["liquido"]))
    st.caption("O retorno total inclui o valor colocado. Lucro ou prejuízo = retorno total − valor simulado.")
    with st.expander(f"Histórico desta sessão · {len(historico)} simulações"):
        st.caption("As últimas 20 simulações ficam nesta sessão. Cada clique realiza um novo sorteio independente.")
        st.dataframe([{"Nº": h["numero"], "Confronto": f"{h['mandante']} × {h['visitante']}",
                       "Escolha": nome_resultado(h["escolha"], h),
                       "Resultado": nome_resultado(h["resultado"], h),
                       "Odd": numero(h["odd"]), "Valor": moeda(h["valor"]),
                       "Retorno": moeda(h["retorno"]), "Lucro / prejuízo": moeda(h["liquido"])}
                      for h in historico], hide_index=True, width="stretch")


def renderizar():
    st.markdown('<div class="secao">Apostas Brasileirão</div>'
                '<div class="sub">Escolha um confronto, monte seu bilhete e simule o resultado com dinheiro fictício.</div>',
                unsafe_allow_html=True)
    try:
        jogos = bra.carregar_jogos()
    except (OSError, ValueError, KeyError):
        st.error("Não foi possível carregar a base do Brasileirão. A simulação ficará disponível quando a base for corrigida.")
        return
    por_par = {(j["mandante"], j["visitante"]): j for j in jogos}
    times = sorted({j["mandante"] for j in jogos})
    com_odds = sum(j["odd_1"] is not None for j in jogos)
    consulta = max(j["consulta"] for j in jogos)
    st.caption(f"{len(jogos)} confrontos · {com_odds} com odds · {len(jogos) - com_odds} sem cotação · "
               f"Base coletada em {data_br(consulta)}. Odds históricas e pré-jogo; sem atualização ao vivo.")

    with st.container(border=True):
        st.markdown("#### 1. Escolha o confronto")
        c1, c2 = st.columns(2)
        mandante = c1.selectbox("Mandante · joga em casa", times, key="bra_mandante")
        adversarios = [time for time in times if time != mandante]
        if st.session_state.bra_visitante not in adversarios:
            st.session_state.bra_visitante = adversarios[0]
        visitante = c2.selectbox("Visitante · joga fora", adversarios, key="bra_visitante")
        jogo = por_par[(mandante, visitante)]
        st.markdown(f"**{mandante} × {visitante}**")
        disponivel = jogo["odd_1"] is not None
        if disponivel:
            rotulo = "Odds históricas de fechamento" if jogo["tipo"].startswith("Histórica") else "Odds pré-jogo registradas na coleta"
            st.caption(f"{rotulo} · data na fonte: {data_br(jogo['data_fonte'])}")
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Vitória · {mandante}", numero(jogo["odd_1"]))
            c2.metric("Empate", numero(jogo["odd_X"]))
            c3.metric(f"Derrota · {visitante} vence", numero(jogo["odd_2"]))
        else:
            st.info("Não encontramos odds para este mando de campo na coleta. Escolha outro confronto para simular.")

        st.markdown("#### 2. Monte o bilhete fictício")
        st.caption(f"Vitória e derrota se referem ao mandante, {mandante}. O empate vale para os dois times.")
        escolha = st.radio("Seu resultado", bra.RESULTADOS, key="bra_escolha", horizontal=True,
                           format_func=lambda c: {"1": "Vitória (1)", "X": "Empate (X)", "2": "Derrota (2)"}[c],
                           disabled=not disponivel)
        valor = st.number_input("Valor fictício (R$)", min_value=0.01, max_value=float(bra.MAX_VALOR),
                                step=1.0, format="%.2f", key="bra_valor", disabled=not disponivel)
        erro = None
        if disponivel:
            try:
                bilhete = bra.calcular_bilhete(jogo, escolha, valor)
                st.markdown(f"Odd selecionada: **{numero(bilhete['odd'])}**. Se acertar, voltam "
                            f"**{dinheiro_md(bilhete['retorno_possivel'])}**, com lucro de "
                            f"**{dinheiro_md(bilhete['lucro_possivel'])}**. Se errar, perde "
                            f"**{dinheiro_md(bilhete['valor'])}**.")
            except bra.ErroBrasileirao as exc:
                erro = str(exc)
                st.error(erro.replace("$", r"\$"))
        if st.button("Simular jogo", type="primary", width="stretch", key="bra_simular",
                     disabled=not disponivel or erro is not None):
            resultado = bra.simular_jogo(jogo, escolha, valor)
            st.session_state.bra_contador += 1
            resultado["numero"] = st.session_state.bra_contador
            st.session_state.bra_historico = [resultado, *st.session_state.bra_historico][:20]

    mostrar_resultado()
    with st.expander("Como o jogo é simulado e de onde vêm as odds"):
        st.markdown("O sorteio escolhe **um** resultado: vitória do mandante, empate ou vitória do visitante. "
                    "As chances são calculadas dividindo **1 ÷ odd** pela soma dos três inversos. "
                    "Isso retira proporcionalmente a margem embutida nas odds e é uma hipótese da simulação; "
                    "não estima o placar nem prevê o resultado real. O valor escolhido não muda essas chances.")
        if disponivel:
            chances = bra.probabilidades(jogo)
            st.markdown("Chances usadas neste sorteio: " + " · ".join(
                f"{rotulo}: **{numero(p * 100)}%**" for rotulo, p in zip(("Vitória", "Empate", "Derrota"), chances)))
            st.caption(f"Registro: {jogo['id']} · casa identificada na fonte: {jogo['casa']} · "
                       f"{jogo['tipo']} · referência da fonte: {data_br(jogo['data_fonte'])}.")
        st.markdown("A base reúne **309 confrontos com odds históricas**, **20 com odds pré-jogo publicadas** "
                    "e **51 sem cotação**. São retratos de datas diferentes: mesmo um jogo que já aconteceu "
                    "ganha um novo resultado fictício aqui. A ordem mandante/visitante importa.")
        st.caption("Coleta consolidada em 23/10/2026, às 16h24 de Brasília. A hora identifica a consolidação, "
                   "não a atualização dos preços. Retornos sem bônus, impostos ou comissões. "
                   "O histórico existe apenas enquanto esta sessão estiver ativa.")
