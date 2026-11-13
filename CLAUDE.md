# Projeto: assistente educativo sobre apostas esportivas (Projetos III, Grupo 3)

Trabalho de faculdade. App em Python + Streamlit com quatro abas (Conversa, Simulador, Brasileirão (simulação) e Sobre). Público: maiores de 18 anos que já apostam. É uma ferramenta **educativa**: nunca dá palpite, indica casa de apostas, método para ganhar mais ou para recuperar perdas, e nunca faz juízo moral.

Repositório: https://github.com/thomasdtavares/Projetos-Bets (app publicado no Streamlit Community Cloud a partir da branch `main`; o link do app está no painel share.streamlit.io da conta do GitHub do dono).

## Arquivos
- `app.py`: interface (abas Conversa, Simulador e Sobre; botão "Ver no simulador" no chat).
- `simulador.py`: cálculos puros (aposta única, Monte Carlo 10.000, fixo/percentual/martingale, custo de oportunidade, `extrair_simular`). Os números do app vêm daqui, nunca do modelo.
- `llm.py`: `responder(mensagens, prompt_sistema) -> Resposta(texto, completa)`. Gemini (se houver `GEMINI_API_KEY`) ou Claude (`ANTHROPIC_API_KEY`). `com_tentativas` faz novas tentativas com espera, troca de modelo e limite de 50 s; resposta cortada volta com `completa=False`.
- `respostas_prontas.py`: respostas fixas (tiradas das fichas) para as 4 perguntas sugeridas; não chamam o modelo.
- `registro.py`: registro anônimo (pergunta, tipo de resposta, 👍/👎) em `registros/interacoes.csv` (fora do git; some quando o app reinicia). Download na aba Sobre > Área da equipe, se o secret `EQUIPE_SENHA` existir.
- `prompt_sistema.md`: regras do assistente + formato da linha `[SIMULAR valor=.. odd=.. prob=.. apostas=.. taxa=.. banca=.. pct=.. modo=..]`.
- `conhecimento/base.md`: fichas P1 a P10 e texto de escopo do Conteúdo III; desde 13/11/2026, também os verbetes P11 a P26 (resposta curta + "Quer entender melhor?") e as respostas-limite F1 a F5 do Conteúdo IV (extraídos sem reescrever, com as correções listadas no cabeçalho do arquivo). É carregada inteira no prompt (sem RAG). `tests/test_base.py` confere estrutura, coerência com o prompt e os números dos verbetes.
- `tests/test_simulador.py` (44 testes) e `tests/test_chat.py` (11 testes, sem chamar modelo), `tests/roteiro_teste_chat.md`, `tests/saida_teste_chat.md` (respostas reais do Gemini aos 13 casos do roteiro).
- `Implementacao_I_preenchido.docx`: relatório da entrega, com capturas em `docs/evidencias/`.

## Como rodar
```
pip install -r requirements.txt
streamlit run app.py
```
Chave do chat: copiar `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e preencher `GEMINI_API_KEY` (grátis em aistudio.google.com/apikey). Esse arquivo está no `.gitignore`: **nunca commitar chaves**. Na nuvem, a chave fica em *Advanced settings > Secrets* do Streamlit.

## Decisões importantes
- O Botpress foi trocado por código (Python + LLM) para integrar o simulador e manter prompt/base versionados.
- Modelo Gemini: o `gemini-3.8-flash` ficou lento (20 a 100 s) e dava erro 503 no plano grátis. O padrão agora é `gemini-3.5-flash-lite` (2 a 4 s), com `gemini-3.6-flash` e `gemini-3.7-flash` de reserva e limite de 20 s por tentativa. Dá para forçar um modelo com `MODELO` nos secrets. Claude padrão: `claude-haiku-5-5`.
- Streamlit: `$` em markdown vira fórmula, por isso o texto com `R$` é escapado (`brl_md`). A troca de aba pelo botão do chat usa `st.tabs(..., key="abas", on_change="rerun")`; por isso as chaves `q_*`, `mult_*` e `jogo_tipo` são reatribuídas no início do `app.py`. O `import pandas` no topo evita uma corrida de import. O `app.py` faz `importlib.reload(sim)`: sem isso, depois de um commit o Streamlit Cloud rodava o `app.py` novo com o `simulador.py` antigo na memória (AttributeError em 16/10/2026).
- **Simulador para leigos (15/10/2026, a pedido do dono):** sem "opções avançadas" (semente, Kelly, % da banca e taxa saíram da tela). Quatro sub-abas: *Quanto custa apostar* (valor, tipo de aposta Favorito 1,50 / Equilibrado 2,20 / Zebra 5,00 / Outra odd, apostas por semana, tempo; os resultados só mudam ao apertar "Ver o que acontece", e um quadro mostra o que mudou; 100 pessoas; chance de lucro mês a mês com tendência; guardar x apostar), *Estratégias* (`comparar_estrategias`), *Aposte rodada a rodada* (`rodada_do_jogo`) e *Bilhete múltiplo* (`bilhete_multiplo`). A odd é informada uma vez só. "100 pessoas" e "tempo" usam a conta exata (`distribuicao`, binomial); estratégias e o gráfico aposta a aposta usam Monte Carlo. `cenario_do_chat` converte o número de apostas da linha [SIMULAR] em apostas por semana + tempo.
- Git: a máquina de casa (desktop) não tinha git; o commit inicial foi feito com a biblioteca `dulwich`. O envio ao GitHub é feito pelo GitHub Desktop (Push origin).
- **Chance de acerto (15/10/2026):** o simulador não pergunta mais "quanto você acha que tem de chance". A chance sai da odd sem a margem da casa: `prob_justa(odd, margem) = (1/odd)/(1+margem)`, margem padrão 5% (`MARGEM_PADRAO`, próxima do exemplo 2,10/3,40/3,60 = 4,8% da ficha P3) ou calculada com `margem_das_odds([o1,o2,o3])`. "Testar uma chance minha" saiu da tela em 15/10 por confundir o público; a margem voltou a ser ajustável em 16/10 (ver abaixo), fora do fluxo principal. Na linha `[SIMULAR]`, `prob=` virou opcional e existe `margem=` (em %).
- **Ajustes do feedback (16/10/2026):** cartões de estratégia com "Total apostado (média)" e notas automáticas quando uma estratégia "parece" melhor (menos gente perde mas mais gente perde tudo; ou perde menos só porque aposta menos no total). Margem ajustável (2% a 15%, em "Margem da casa" no cenário, entra em `cen["margem"]`) e nova sub-aba "Ler as odds de um jogo" (`ler_odds`), com botão para usar a margem no simulador. Seção "E se você reaposta o que volta?" (`reapostar`, conta da média: apostado = colocado ÷ (1 − f·r)). Taxa de "guardar" com fonte (`TAXAS_GUARDAR`: poupança 0,67% a.m., Banco Central out/2026; Tesouro Selic/CDB 1,08% a.m. = Selic 13,75% a.a., Copom 16/09/2026; consultadas em 16/10/2026, atualizar se mudar). Mini-jogo sem cara de bet: botões "Sortear 1/10 apostas", texto "simulação educativa", "nenhuma aposta ainda" e resumo depois de 20 apostas.
- **Chat robusto e preciso (23/10/2026, feedback do app publicado):** a pergunta é salva antes de chamar o modelo; erro vira aviso amigável com botão "Tentar de novo"; resposta cortada aparece com aviso e o mesmo botão; `MAX_TOKENS` subiu de 1500 para 4096 (uma resposta foi cortada no meio). O prompt agora exige linha "Fonte:" no fim, proíbe chamar total apostado de "gasto", diz que a perda vem da margem (a LGN só explica a convergência), proíbe prometer números que o resumo não mostra e o lembrete genérico no fim de toda resposta; inclui "empréstimo" e "não consigo parar" como sinais de risco. Avaliação 👍/👎 em cada resposta. Aba "Sobre" com autores, o que faz/não faz, limitações, datas, privacidade e fontes (lidas de `base.md`).
- **Interface para o público (23/10/2026, feedback da aula):** pensada para celular: cabeçalho compacto ("Bets: o que os números dizem"), aviso de uma linha, botões de sugestão com texto curto (`ROTULOS`, a pergunta completa vai para o chat), abas do simulador com nomes curtos ("Quanto custa", "Estratégias", "Jogo", "Múltipla", "Ler odds"), "Resultado médio" virou "Perda média" (valor positivo), "reapostar" e "aposta a aposta" recolhidos, "Como calculamos (hipóteses)" virou "Como fizemos as contas".
- Visual (15/10/2026): tema em `.streamlit/config.toml`, CSS no topo do `app.py` (não aplicar fonte em `[class*="st-"]`: quebra os ícones), gráficos Plotly com a paleta azul (lucro/guardar) x vermelho (prejuízo/apostar).

- **Testes e Validação II (06/11/2026, a partir dos testes com usuários de 30/10):** (1) pedido de palpite, previsão de resultado ou indicação de casa não chega ao modelo: `respostas_prontas.eh_pedido_de_palpite` detecta e o app mostra a resposta fixa `PALPITE` (registro `palpite_recusado`); o prompt também reforça a recusa quando a pessoa insiste; (2) odd → chance em todo resultado (`simulador.odd_para_chance`, `frase_odd` no app; resumo do chat, cartão do resultado e resposta pronta "Como funciona uma aposta?"); (3) "Perda média" com explicação (`AJUDA_PERDA`); (4) simulador mais enxuto: "Apostar × guardar" logo depois do resultado, "com o passar do tempo" recolhido; (5) frase sobre ilusão de controle no resultado; (6) prompt com caminhos concretos de limite (autolimitação de valor e tempo, autoexclusão gov.br, plataforma autorizada); (7) atalho "Abrir o simulador" na tela inicial do chat.

## Estado e pendências (09/10/2026)
Feito: interface, base de conhecimento, chat testado com Gemini real, simulador completo, testes, publicação.
Pendente (responsáveis e prazos são só uma proposta, ver relatório): o grupo conferir cada resposta do chat com as fichas; entrevistas com usuários; consulta a professor de finanças; reconfirmar o dado da SPA de 2026; colar o link do app no relatório (campo `[COLAR LINK DO APP]`).

## Cuidados
- `docs/*.docx` (documentos da disciplina) não estão no git de propósito; só existem no computador de casa do dono. O conteúdo das fichas já está em `conhecimento/base.md`.
- O relatório foi gerado por um script que não está no repositório; para mudar algo, edite o `.docx` direto no Word.
- Se mudar o prompt ou o modelo, rode de novo os casos de `tests/roteiro_teste_chat.md`.

## Apostas Brasileirão (06/11/2026)

- Preservar a aba e sua integração no `app.py` ao atualizar outras áreas. Interface em `aba_brasileirao.py`; base, caixa e Monte Carlo em `brasileirao.py`; fontes em `dados/`.
- Decisões do usuário: saldo inicial fixo de R$ 500; jogo individual e rodada de até 10 apostas separadas; painel com escudos; curva do saldo; histograma de 1.000 réplicas em seção expansível; fim da sessão ao zerar, sem reposições. Reiniciar começa uma nova sessão.
- Reservar o total de uma rodada antes dos retornos e rejeitar confrontos duplicados na rodada. Usar centavos inteiros. Nunca truncar o histórico usado pelos gráficos/contas.
- A comparação usa o roteiro fixo e para cada réplica se faltar saldo para a próxima rodada inteira. Distinguir falta de saldo suficiente de saldo zero. Não alterar as probabilidades para forçar ganhos ou perdas.
- 380 pares: 329 com odds coletadas em 23/10/2026 e 51 sem cotação. Não inventar odds ou placares; identificar a data da base. Escudos locais obtidos da CBF, com `dados/escudos/fontes.json`.
- `pytest` valida caixa, rodadas, falta de saldo, reset, persistência entre abas e comparação. Mudanças no site precisam ser commitadas e enviadas ao `main` para aparecer no Streamlit Cloud.

## Entrega final (13/11/2026)

- Aba renomeada para "🏟️ Brasileirão (simulação)" (`ABA_BRASILEIRAO`), para não parecer uma casa de apostas no vídeo e na banca. Os testes da aba usam o novo nome.
- Linha "Na média" no bilhete do Brasileirão (`brasileirao.retorno_medio`): com p_i = (1/odd_i)/S, o retorno esperado de qualquer resultado é valor/S. Na base, S vai de 104,7% a 113,7% (média 106,9%). Explicação também no expander "Como funciona".
- Taxas de "guardar" reconfirmadas em 13/11/2026: Selic 13,75% a.a. mantida pelo Copom em 04/11/2026 (reunião 282); valores do simulador não mudaram, só a fonte e as datas.
- Aba Sobre: cita o Brasileirão e seus limites; datas atualizadas (app em 13/11/2026).
- Produto congelado após este commit para a gravação do vídeo e a banca (27/11): não publicar mudanças sem combinar com o grupo.
- **Base do Conteúdo IV (13/11/2026):** a base passou a ter as fichas P1 a P26 e as respostas-limite F1 a F5, fechando a lacuna apontada no feedback do Conteúdo III e no Workbook (ilusão de controle, excesso de confiança, Kelly, bônus, disponibilidade, viés do presente, TCL, binomial). O prompt cita P1 a P26, usa F1 a F5 como modelo para pedidos de palpite, estratégia, comparação de casas e vulnerabilidade, e só usa a parte "Quer entender melhor?" quando a pessoa pede detalhes. A aba Sobre deduplica as fontes por primeiro sobrenome + ano (`chave_da_fonte`). Roteiro do chat ampliado (seção B3 de `tests/roteiro_teste_chat.md`).
