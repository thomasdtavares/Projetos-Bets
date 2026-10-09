# Projeto: assistente educativo sobre apostas esportivas (Projetos III, Grupo 3)

Trabalho de faculdade. App em Python + Streamlit com duas abas (Chat e Simulador). Público: maiores de 18 anos que já apostam. É uma ferramenta **educativa**: nunca dá palpite, indica casa de apostas, método para ganhar mais ou para recuperar perdas, e nunca faz juízo moral.

Repositório: https://github.com/thomasdtavares/Projetos-Bets (app publicado no Streamlit Community Cloud a partir da branch `main`; o link do app está no painel share.streamlit.io da conta do GitHub do dono).

## Arquivos
- `app.py`: interface (abas Chat e Simulador, botão "Abrir no simulador").
- `simulador.py`: cálculos puros (aposta única, Monte Carlo 10.000, fixo/percentual/martingale, custo de oportunidade, `extrair_simular`). Os números do app vêm daqui, nunca do modelo.
- `llm.py`: `responder(mensagens, prompt_sistema)`. Gemini (se houver `GEMINI_API_KEY`) ou Claude (`ANTHROPIC_API_KEY`).
- `prompt_sistema.md`: regras do assistente + formato da linha `[SIMULAR valor=.. odd=.. prob=.. apostas=.. taxa=.. banca=.. pct=.. modo=..]`.
- `conhecimento/base.md`: as 10 fichas e o texto de escopo do Conteúdo III (extraídos sem reescrever). É carregada inteira no prompt (sem RAG).
- `tests/test_simulador.py` (23 testes, `pytest`), `tests/roteiro_teste_chat.md`, `tests/saida_teste_chat.md` (respostas reais do Gemini aos 13 casos do roteiro).
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
- Streamlit: `$` em markdown vira fórmula, por isso o texto com `R$` é escapado (`brl_md`). A troca de aba pelo botão do chat usa `st.tabs(..., key="abas", on_change="rerun")`; por isso as chaves `sim_*` são reatribuídas no início do `app.py`. O `import pandas` no topo evita uma corrida de import.
- A interface do simulador foi simplificada a pedido do dono: 4 campos na frente, o resto em "Opções avançadas" e em seções que se abrem.
- Git: a máquina de casa (desktop) não tinha git; o commit inicial foi feito com a biblioteca `dulwich`. O envio ao GitHub é feito pelo GitHub Desktop (Push origin).

## Estado e pendências (09/10/2026)
Feito: interface, base de conhecimento, chat testado com Gemini real, simulador completo, testes, publicação.
Pendente (responsáveis e prazos são só uma proposta, ver relatório): o grupo conferir cada resposta do chat com as fichas; entrevistas com usuários; consulta a professor de finanças; reconfirmar o dado da SPA de 2026; colar o link do app no relatório (campo `[COLAR LINK DO APP]`).

## Cuidados
- `docs/*.docx` (documentos da disciplina) não estão no git de propósito; só existem no computador de casa do dono. O conteúdo das fichas já está em `conhecimento/base.md`.
- O relatório foi gerado por um script que não está no repositório; para mudar algo, edite o `.docx` direto no Word.
- Se mudar o prompt ou o modelo, rode de novo os casos de `tests/roteiro_teste_chat.md`.
