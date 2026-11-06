# Base do simulador Apostas Brasileirão

`brasileirao_2026.csv` é a cópia da tabela principal da coleta de 23/10/2026. UTF-8 com BOM, separador ponto e vírgula e decimais com ponto. Contém os 380 pares dirigidos dos 20 clubes da Série A 2026: 19 mandantes e 19 visitantes por clube, sem confrontos de um time consigo mesmo.

## Cobertura

| Tipo | Confrontos | Tratamento |
|---|---:|---|
| Histórica — fechamento | 309 | Identificados como históricos; podem ser simulados novamente |
| Pré-jogo — publicada | 20 | Odds registradas na coleta, sem promessa de preço atual |
| Não encontrado | 51 | Odds vazias; simulação desabilitada |

`odd_1` representa vitória do mandante; `odd_X`, empate; `odd_2`, vitória do visitante (derrota do mandante). Cada tripla vem inteira de uma mesma casa e registro. A tabela priorizou bet365, depois Stake e Virgin Bet SA; isso organiza a base, sem recomendar operadoras. A coleta detalhada original reunia 825 registros por casa; o app usa os 329 registros escolhidos para a tabela principal.

O sorteio usa p(i) = (1 / odd_i) / soma(1 / odd_j). É uma hipótese proporcional para retirar a margem, não uma estimativa validada das chances reais. O resultado real das partidas encerradas não é usado. Sorteios independentes, sem geração de placares. Em caso de acerto: retorno = valor × odd, arredondado para centavos; lucro = retorno − valor. Em caso de erro: retorno = zero e prejuízo = valor.

## Fontes

- [Football-Data — Brasil](https://football-data.co.uk/brazil.php), [CSV original](https://football-data.co.uk/new/BRA.csv) e [dicionário](https://football-data.co.uk/notes.txt): filtro Season = 2026, campos B365CH/B365CD/B365CA para as 309 triplas históricas. O sufixo C indica fechamento. A página informava atualização em 20/10/2026 quando consultada.
- [Stake — Série A](https://stake.com/pt/sports/soccer/brazil/brasileiro-serie-a) e [Virgin Bet SA — Série A](https://www.virginbet.co.za/sports/football/brazil-serie-a/SBTC3_38529/): odds pré-jogo recuperadas em consulta pública/indexada das páginas.
- A URL específica de cada registro permanece na coluna `fonte`, junto com `casa`, `tipo`, `data_fonte` e `consulta`.
- As odds da Pinnacle foram excluídas da consolidação devido ao [aviso do fornecedor sobre dados desatualizados desde 23/07/2025](https://football-data.co.uk/data.php).

## Limites

- `consulta = 2026-10-23T16:24:10-03:00` identifica a consolidação, não a atualização de cada preço. O site não consulta operadoras ao vivo.
- Odds históricas e pré-jogo foram registradas em datas diferentes: não são uma fotografia simultânea nem preços executáveis agora.
- `data_fonte` é uma referência do fornecedor, não um calendário auditado da CBF. Há divergências entre fontes; os preços foram associados por temporada, mandante e visitante.
- Fontes internacionais podem ter preços diferentes dos brasileiros. Não se presume disponibilidade em contas brasileiras.
- Os 51 pares sem dados não recebem odds estimadas nem preços do confronto com mando invertido.
- Dinheiro exclusivamente fictício, sem impostos, bônus ou comissões; sem depósitos ou pagamentos reais. O histórico da sessão guarda as últimas 20 simulações.
