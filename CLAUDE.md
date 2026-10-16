# Projeto: assistente educativo sobre apostas esportivas (Projetos III, Grupo 3)

Trabalho de faculdade. App em Python + Streamlit com duas abas (Chat e Simulador). Público: maiores de 18 anos que já apostam. É uma ferramenta **educativa**: nunca dá palpite, indica casa de apostas, método para ganhar mais ou para recuperar perdas, e nunca faz juízo moral.

Repositório: https://github.com/thomasdtavares/Projetos-Bets (app publicado no Streamlit Community Cloud a partir da branch `main`; o link do app está no painel share.streamlit.io da conta do GitHub do dono).

## Arquivos
- `app.py`: interface (abas Conversa e Simulador, botão "Ver no simulador" no chat).
- `simulador.py`: cálculos puros (aposta única, Monte Carlo 10.000, fixo/percentual/martingale, custo de oportunidade, `extrair_simular`). Os números do app vêm daqui, nunca do modelo.
- `llm.py`: `responder(mensagens, prompt_sistema)`. Gemini (se houver `GEMINI_API_KEY`) ou Claude (`ANTHROPIC_API_KEY`).
- `prompt_sistema.md`: regras do assistente + formato da linha `[SIMULAR valor=.. odd=.. prob=.. apostas=.. taxa=.. banca=.. pct=.. modo=..]`.
- `conhecimento/base.md`: as 10 fichas e o texto de escopo do Conteúdo III (extraídos sem reescrever). É carregada inteira no prompt (sem RAG).
- `tests/test_simulador.py` (44 testes, `pytest`), `tests/roteiro_teste_chat.md`, `tests/saida_teste_chat.md` (respostas reais do Gemini aos 13 casos do roteiro).
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
- Streamlit: `$` em markdown vira fórmula, por isso o texto com `R$` é escapado (`brl_md`). A troca de aba pelo botão do chat usa `st.tabs(..., key="abas", on_change="rerun")`; por isso as chaves `q_*`, `mult_*` e `jogo_tipo` são reatribuídas no início do `app.py`. O `import pandas` no topo evita uma corrida de import.
- **Simulador para leigos (15/10/2026, a pedido do dono):** sem "opções avançadas" (semente, Kelly, % da banca e taxa saíram da tela). Quatro sub-abas: *Quanto custa apostar* (valor, tipo de aposta Favorito 1,50 / Equilibrado 2,20 / Zebra 5,00 / Outra odd, apostas por semana, tempo; os resultados só mudam ao apertar "Ver o que acontece", e um quadro mostra o que mudou; 100 pessoas; chance de lucro mês a mês com tendência; guardar x apostar), *Estratégias* (`comparar_estrategias`), *Aposte rodada a rodada* (`rodada_do_jogo`) e *Bilhete múltiplo* (`bilhete_multiplo`). A odd é informada uma vez só. "100 pessoas" e "tempo" usam a conta exata (`distribuicao`, binomial); estratégias e o gráfico aposta a aposta usam Monte Carlo. `cenario_do_chat` converte o número de apostas da linha [SIMULAR] em apostas por semana + tempo.
- Git: a máquina de casa (desktop) não tinha git; o commit inicial foi feito com a biblioteca `dulwich`. O envio ao GitHub é feito pelo GitHub Desktop (Push origin).
- **Chance de acerto (15/10/2026):** o simulador não pergunta mais "quanto você acha que tem de chance". A chance sai da odd sem a margem da casa: `prob_justa(odd, margem) = (1/odd)/(1+margem)`, margem padrão 5% (`MARGEM_PADRAO`, próxima do exemplo 2,10/3,40/3,60 = 4,8% da ficha P3) ou calculada com `margem_das_odds([o1,o2,o3])`. "Testar uma chance minha" saiu da tela em 15/10 por confundir o público; a margem voltou a ser ajustável em 16/10 (ver abaixo), fora do fluxo principal. Na linha `[SIMULAR]`, `prob=` virou opcional e existe `margem=` (em %).
- **Ajustes do feedback (16/10/2026):** cartões de estratégia com "Total apostado (média)" e notas automáticas quando uma estratégia "parece" melhor (menos gente perde mas mais gente perde tudo; ou perde menos só porque aposta menos no total). Margem ajustável (2% a 15%, em "Margem da casa" no cenário, entra em `cen["margem"]`) e nova sub-aba "Ler as odds de um jogo" (`ler_odds`), com botão para usar a margem no simulador. Seção "E se você reaposta o que volta?" (`reapostar`, conta da média: apostado = colocado ÷ (1 − f·r)). Taxa de "guardar" com fonte (`TAXAS_GUARDAR`: poupança 0,67% a.m., Banco Central out/2026; Tesouro Selic/CDB 1,08% a.m. = Selic 13,75% a.a., Copom 16/09/2026; consultadas em 16/10/2026, atualizar se mudar). Mini-jogo sem cara de bet: botões "Sortear 1/10 apostas", texto "simulação educativa", "nenhuma aposta ainda" e resumo depois de 20 apostas.
- Visual (15/10/2026): tema em `.streamlit/config.toml`, CSS no topo do `app.py` (não aplicar fonte em `[class*="st-"]`: quebra os ícones), gráficos Plotly com a paleta azul (lucro/guardar) x vermelho (prejuízo/apostar).

## Estado e pendências (09/10/2026)
Feito: interface, base de conhecimento, chat testado com Gemini real, simulador completo, testes, publicação.
Pendente (responsáveis e prazos são só uma proposta, ver relatório): o grupo conferir cada resposta do chat com as fichas; entrevistas com usuários; consulta a professor de finanças; reconfirmar o dado da SPA de 2026; colar o link do app no relatório (campo `[COLAR LINK DO APP]`).

## Cuidados
- `docs/*.docx` (documentos da disciplina) não estão no git de propósito; só existem no computador de casa do dono. O conteúdo das fichas já está em `conhecimento/base.md`.
- O relatório foi gerado por um script que não está no repositório; para mudar algo, edite o `.docx` direto no Word.
- Se mudar o prompt ou o modelo, rode de novo os casos de `tests/roteiro_teste_chat.md`.
