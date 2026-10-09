# Assistente educativo sobre apostas esportivas (bets)

Projeto da disciplina Projetos III — **Grupo 3** (Bernardo Nappo, Luc Le Corre, Gustavo Lamarca, Tomás Battaus e Thomás Mariano).

É uma ferramenta **educativa** para maiores de 18 anos que já apostam com alguma regularidade. Ela explica como as apostas funcionam (odds, probabilidade implícita, margem da casa, vieses, custo de oportunidade) e tem um **simulador** que mostra o que os números dizem sobre um cenário hipotético. Não dá palpites, não indica casas de apostas e não ensina a "recuperar perdas". Em sinais de risco, encaminha para CAPS/SUS e gov.br/autoexclusaoapostas.

## Como funciona
- **Aba Chat**: um modelo de linguagem responde com base na base de conhecimento (`conhecimento/base.md`, as 10 fichas do Conteúdo III) e nas regras de `prompt_sistema.md`. Quando o caso pede simulação, a resposta termina com uma linha `[SIMULAR ...]`; o app a esconde, calcula um resumo em Python e oferece o botão **Abrir no simulador**.
- **Aba Simulador**: funciona sozinha, sem o chat. Aposta única (probabilidade implícita, valor esperado, Kelly), Monte Carlo com 10.000 simulações (stake fixa, percentual da banca e martingale, com semente opcional), comparação de padrões e custo de oportunidade, com gráficos em Plotly.

## Estrutura
```
app.py                  interface (abas Chat e Simulador)
simulador.py            cálculos puros (sem Streamlit)
llm.py                  chamada ao modelo (Gemini ou Claude)
conhecimento/base.md    10 fichas + texto de escopo (Conteúdo III)
prompt_sistema.md       instruções do assistente
tests/                  testes do simulador e roteiro de teste do chat
```

## Como rodar
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Chave de API (só para o chat)
Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e preencha **uma** chave (ou use variáveis de ambiente):

- `GEMINI_API_KEY`: Google Gemini, tem camada gratuita (chave em https://aistudio.google.com/apikey). Modelo padrão: `gemini-3.8-flash`.
- `ANTHROPIC_API_KEY`: Claude. Modelo padrão: `claude-haiku-5-5`.
- `MODELO` (opcional): troca o modelo do provedor em uso.

Se as duas existirem, o Gemini é usado. Sem nenhuma chave, o chat mostra um aviso e a aba Simulador continua funcionando.

## Publicar na internet (para outras pessoas usarem pelo link)
O jeito mais simples e gratuito é o Streamlit Community Cloud (share.streamlit.io): entre com a conta do GitHub, escolha este repositório, o arquivo `app.py` e, em *Advanced settings > Secrets*, cole `GEMINI_API_KEY = "sua-chave"`. O app ganha um link público que funciona em qualquer navegador, sem instalar nada.

## Testes
```bash
pytest
```
O roteiro de teste manual do chat está em `tests/roteiro_teste_chat.md`.

## Limites
Cenários hipotéticos; apostas independentes; sem bônus, impostos ou limites de plataforma. As odds e probabilidades são informadas pelo usuário, o sistema não acessa odds reais.
