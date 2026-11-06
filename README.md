# Assistente educativo sobre apostas esportivas (bets)

Projeto da disciplina Projetos III — **Grupo 3** (Bernardo Nappo, Luc Le Corre, Gustavo Lamarca, Tomás Battaus e Thomás Mariano).

É uma ferramenta **educativa** para maiores de 18 anos que já apostam com alguma regularidade. Ela explica como as apostas funcionam (odds, probabilidade implícita, margem da casa, vieses, custo de oportunidade) e tem um **simulador** que mostra o que os números dizem sobre um cenário hipotético. Não dá palpites, não indica casas de apostas e não ensina a "recuperar perdas". Em sinais de risco, encaminha para CAPS/SUS e gov.br/autoexclusaoapostas.

## Como funciona
- **Aba Apostas Brasileirão**: escolha mandante e visitante entre os 20 times de 2026, vitória/empate/derrota do mandante e um valor fictício. Cada sessão começa com R$ 500 fictícios, sem reposições. É possível simular um jogo ou montar uma rodada de até 10 apostas independentes, reservando o total antes de receber retornos. O painel usa escudos dos clubes, mostra saldo, acertos, lucro/prejuízo, evolução do saldo por envio e histórico completo. Em uma seção expansível, compara o roteiro com 1.000 simulações e marca o saldo do usuário no histograma. Ao zerar o saldo, encerra a sessão com resumo e permite reiniciar com R$ 500; também é possível encerrar voluntariamente. Os 380 confrontos estão listados; 329 têm odds e 51 ficam indisponíveis para simular. A base é uma coleta de 23/10/2026, com 309 triplas históricas e 20 pré-jogo, identificadas na tela; não é uma cotação ao vivo. O sorteio normaliza os três inversos das odds, sem usar o resultado real dos jogos. Funciona sem chave de API.
- **Aba Chat**: um modelo de linguagem responde com base na base de conhecimento (`conhecimento/base.md`, as 10 fichas do Conteúdo III) e nas regras de `prompt_sistema.md`. Quando o caso pede simulação, a resposta termina com uma linha `[SIMULAR ...]`; o app a esconde, calcula um resumo em Python e oferece o botão **Abrir no simulador**.
- **Aba Simulador** (feita para quem não tem formação em estatística, funciona sem o chat): quatro partes. **Quanto custa apostar**: 3 perguntas do dia a dia (quanto, tipo de aposta, quantas por semana, por quanto tempo) e um botão; mostra o resultado médio, o que mudou em relação ao cenário anterior, "100 pessoas fazendo a mesma coisa" e como a chance de estar no lucro cai com o tempo (conta exata, binomial). **Estratégias**: valor fixo, dobrar depois de perder, dobrar depois de ganhar, apostar alto para recuperar, parar no lucro e limite de perda, com os mesmos sorteios (Monte Carlo). **Aposte rodada a rodada**: mini-jogo com R$ 200 de mentirinha e o caixa da casa com 1.000 apostadores. **Bilhete múltiplo**: a chance e a parte da casa conforme o número de jogos. **Ler as odds de um jogo**: com as 3 odds, mostra a chance que cada uma paga e a margem da casa. A margem (5% por padrão) pode ser ajustada, a taxa de "guardar" tem fonte (poupança ou Tesouro Selic/CDB) e há uma seção sobre reapostar o que volta. A chance de acerto nunca é perguntada: sai da odd sem a margem da casa (5%).

## Estrutura
```
app.py                  interface e navegação das quatro abas
aba_brasileirao.py       seleção, bilhete, resultado e histórico do Brasileirão
brasileirao.py           leitura validada da base e sorteio 1X2 (sem Streamlit)
dados/brasileirao_2026.csv  380 confrontos, odds disponíveis e origem
dados/FONTES_BRASILEIRAO.md  procedência, cobertura e limites da coleta
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

- `GEMINI_API_KEY`: Google Gemini, tem camada gratuita (chave em https://aistudio.google.com/apikey). Modelo padrão: `gemini-3.5-flash-lite` (rápido), com `gemini-3.6-flash` e `gemini-3.7-flash` como reserva se houver erro de sobrecarga.
- `ANTHROPIC_API_KEY`: Claude. Modelo padrão: `claude-haiku-5-5`.
- `MODELO` (opcional): troca o modelo do provedor em uso.

Se as duas existirem, o Gemini é usado. Sem nenhuma chave, o chat mostra um aviso e a aba Simulador continua funcionando.

## Publicar na internet (para outras pessoas usarem pelo link)
O jeito mais simples e gratuito é o Streamlit Community Cloud (share.streamlit.io): entre com a conta do GitHub, escolha este repositório, o arquivo `app.py` e, em *Advanced settings > Secrets*, cole `GEMINI_API_KEY = "sua-chave"`. O app ganha um link público que funciona em qualquer navegador, sem instalar nada.

## Testes com usuários
Cada resposta do chat tem 👍/👎. As perguntas e avaliações ficam num registro anônimo (`registros/interacoes.csv`). Para baixá-lo pelo app publicado, crie nos Secrets do Streamlit uma senha `EQUIPE_SENHA = "..."` e use a aba **Sobre > Área da equipe**. O registro é apagado quando o app reinicia ou recebe um commit novo: baixe ao fim de cada sessão de testes.

## Testes
```bash
pytest
```
(`tests/test_simulador.py` confere as contas; `tests/test_chat.py` confere novas tentativas, respostas prontas e registro, sem chamar o modelo; `tests/test_brasileirao.py` confere a base, sorteio e pagamentos; `tests/test_aba_brasileirao.py` exercita o fluxo da nova aba com Streamlit AppTest.)
O roteiro de teste manual do chat está em `tests/roteiro_teste_chat.md`.

## Limites
Cenários hipotéticos; apostas independentes; sem bônus, impostos ou limites de plataforma. Na aba Simulador, usam-se odds ilustrativas ou informadas pelo usuário. Na aba Apostas Brasileirão, usa-se uma base local de odds coletadas, sem consulta ao vivo: chance do resultado i = (1 ÷ odd i) ÷ soma dos três inversos. Isso é uma hipótese de simulação, não uma previsão. Valores ausentes não são preenchidos com estimativas. O valor fictício admite centavos e precisa caber no saldo disponível, assim como o total de cada rodada; o pagamento é arredondado para centavos. O histórico é temporário e não há depósitos, pagamentos reais ou integração com operadoras.

## Comparação das 1.000 simulações

Cada réplica começa com R$ 500 e repete as rodadas já realizadas, com os mesmos valores, escolhas e odds. As escolhas são mantidas fixas, mesmo que originalmente tenham reagido a ganhos ou perdas. A réplica para se não puder financiar a rodada inteira e preserva o saldo restante; não usa retornos futuros nem volta a apostar depois. Os quatro grupos do resumo (lucro, prejuízo com saldo, zero e empate financeiro) são exclusivos. A contagem de réplicas que não puderam concluir é informada separadamente e pode se sobrepor a esses grupos. A semente fixa mantém a comparação estável para um mesmo roteiro; o sorteio dos jogos do usuário permanece aleatório.

O caixa e a liquidação usam centavos inteiros, sem truncar o histórico após 20 apostas. Reiniciar limpa fila, resultados e comparação. As sessões antigas do modo sem saldo não são importadas para o novo caixa.
