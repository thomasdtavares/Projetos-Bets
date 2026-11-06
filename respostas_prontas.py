"""Respostas prontas para as 4 perguntas sugeridas na tela inicial do chat.

Motivo (feedback de 16/10/2026): os botões de sugestão são o que todo usuário (e a banca) clica primeiro.
Com resposta pronta, eles funcionam sempre, mesmo se o serviço do modelo estiver lento ou fora do ar.
Os textos vêm das fichas da base de conhecimento (conhecimento/base.md), com a vírgula decimal padronizada
e a linha "Fonte:" no fim. A 4ª resposta termina com a linha [SIMULAR ...], como as respostas do modelo.
"""

P1 = """Você escolhe um resultado dentro de um jogo (por exemplo, "o Palmeiras vence") e coloca um valor nesse palpite. Ao lado de cada opção aparece um número: é a **odd**. Se o resultado que você escolheu acontecer, você recebe o valor apostado multiplicado pela odd. Se não acontecer, você perde o valor apostado.

Um exemplo: você aposta R$ 20 numa opção com odd 1,80. Acertando, recebe R$ 36 (R$ 20 × 1,80): desses, R$ 20 são o seu próprio dinheiro voltando e R$ 16 são lucro. Errando, recebe R$ 0.

A odd também diz **qual chance a casa está dando** àquele resultado: basta dividir 1 pela odd. Odd 1,80 → 1 ÷ 1,80 ≈ 56%. Odd 2,00 → 50%. Como a margem da casa vem embutida, a chance estimada é um pouco menor: com a margem de referência de 5%, cerca de 53% na odd 1,80 e 48% na odd 2,00. Por isso odd alta não é oportunidade: ela paga mais porque acerta menos.

Além do resultado do jogo, existem dezenas de outros mercados: total de gols, escanteios, cartões, quem marca primeiro. O funcionamento é sempre o mesmo; o que muda é apenas o evento que está sendo precificado.

Vale um aviso sobre as **apostas múltiplas**, que juntam vários palpites num bilhete só. As odds se multiplicam e o retorno anunciado fica bem maior, mas o bilhete só paga se todos os palpites acertarem. Três palpites de odd 1,80 dão uma odd combinada de 5,83, e uma chance conjunta de cerca de 17%, não de 56%. Na aba **Simulador > Bilhete múltiplo** você pode testar isso.

Fonte: Lei nº 14.790/2023 (apostas de quota fixa); relação entre odd e probabilidade e regra do produto para eventos independentes (bibliografia de Probabilidade e Estatística)."""

P5 = """Não necessariamente. Acertar mais da metade só garante lucro se a odd for alta o suficiente para compensar as perdas.

Um exemplo concreto. Você aposta R$ 10 por bilhete, sempre em odd 1,80, e acerta 55 de 100 apostas:

- Total apostado: 100 × R$ 10 = R$ 1.000
- Total recebido: 55 × R$ 18 = R$ 990
- Resultado: prejuízo de R$ 10

Você acertou a maioria e mesmo assim terminou no vermelho. Nesse caso, o ponto de equilíbrio seria acertar cerca de 55,6 em 100, que é exatamente a chance que a odd 1,80 indica (1 ÷ 1,80). Abaixo disso, prejuízo.

Por isso a taxa de acerto, sozinha, não diz nada. Ela só significa alguma coisa quando comparada à odd em que você apostou.

Isso ajuda a explicar uma sensação comum: a de já ter ganhado várias vezes e mesmo assim estar no prejuízo. Os acertos são marcantes: têm hora, valor, comemoração. As perdas são pequenas, frequentes e se diluem. O teste é simples e um pouco desconfortável: em vez de lembrar, olhe o extrato e some tudo que saiu e tudo que voltou desde o primeiro depósito.

Abaixo, o simulador mostra o que acontece com 100 apostas de R$ 10 na odd 1,80.

Fonte: valor esperado e ponto de equilíbrio (bibliografia de Probabilidade e Estatística); Thaler (1985), contabilidade mental.
[SIMULAR valor=10 odd=1.80 apostas=100]"""

P8 = """Essa estratégia tem nome, **Martingale**, e ela falha por três motivos, todos matemáticos.

**Primeiro: o dinheiro é finito.** Dobrando a cada perda, R$ 10 vira R$ 20, R$ 40, R$ 80, R$ 160, R$ 320, R$ 640. Na oitava tentativa você precisaria colocar R$ 1.280 numa única aposta, tendo já perdido R$ 1.270. Sequências de oito perdas acontecem.

**Segundo: as plataformas impõem limite máximo de aposta.** Mesmo com dinheiro disponível, a progressão trava em algum ponto.

**Terceiro, e mais importante: dobrar não muda a margem da casa.** Cada aposta nova continua tendo resultado médio negativo. Você aumenta o tamanho do risco sem mudar nada a seu favor.

O que torna essa ideia tão atraente não é a matemática: é a sensação de que a perda ainda não é definitiva enquanto você estiver tentando recuperá-la. Na literatura, isso se chama **perseguição de perdas**.

Um mecanismo parecido explica outras duas sensações comuns. A de que "quase acertar" o bilhete significa estar perto: em termos de resultado, quase acertar e errar são a mesma coisa, mas o cérebro reage ao quase-ganho de forma parecida com o ganho. E a de que apostar com o dinheiro já ganho "não conta": aquele dinheiro é seu, e perdê-lo deixa você mais pobre do que estava minutos antes.

Na aba **Simulador > Estratégias** você vê o que acontece com 100 pessoas que dobram a aposta depois de perder. Se a vontade de recuperar o que perdeu estiver pesando, procure apoio: o CAPS, pelo SUS, atende de graça, e em gov.br/autoexclusaoapostas há um autoteste e o bloqueio do CPF em todas as bets autorizadas.

Fonte: Kahneman e Tversky (1979), aversão à perda; Clark et al. (2009), quase-ganho; Thaler e Johnson (1990), efeito do dinheiro da casa."""

CENARIO = """Dá para ver isso com números. O objetivo aqui é educativo: mostrar o que a conta diz, não indicar em que apostar.

Como você falou em apostar por rodada, considerei **38 apostas**, uma por rodada do Brasileirão. Você pode mudar isso no simulador.

- **Quanto você coloca:** 38 × R$ 20 = **R$ 760**. Esse é o total apostado, não o total perdido: parte desse dinheiro volta quando você acerta.
- **Quanto volta, em média:** a odd 2,20 já vem com a margem da casa embutida. Com a margem de referência de 5%, de cada R$ 100 apostados voltam, em média, cerca de R$ 95. Os outros R$ 5 ficam com a casa, ganhando ou perdendo.
- **O que isso dá no campeonato:** em média, a casa fica com cerca de R$ 5 de cada R$ 100 que você apostou. Mas a média não é o que acontece com cada pessoa: algumas terminam no lucro e a maioria termina no prejuízo.

Quem gera esse resultado negativo é a **margem da casa**. A Lei dos Grandes Números só explica por que, quanto mais apostas você faz, mais o seu resultado tende a se aproximar dessa média.

A conta exata aparece logo abaixo, feita pelo simulador. No botão **Ver no simulador**, você vê o que aconteceria com 100 pessoas fazendo exatamente a mesma coisa.

Fonte: valor esperado e Lei dos Grandes Números (bibliografia de Probabilidade e Estatística); conceito de margem (overround) da base de conhecimento do projeto.
[SIMULAR valor=20 odd=2.20 apostas=38]"""

# --- Pedido de palpite (Testes e Validação II, 06/11/2026) ---------------------------------------------
# Nos testes com usuários de 30/10, um participante relatou que o assistente "deu um palpite". Como o registro do app
# se apaga ao reiniciar, não foi possível confirmar. A correção não depende do modelo: pedidos claros de palpite,
# de previsão de resultado ou de indicação de casa recebem esta resposta fixa, sem chamar o modelo.

PALPITE = """Palpite eu não dou: nem sobre jogo, nem sobre resultado, nem sobre casa de apostas. Não é julgamento. Esta é uma ferramenta educativa, e a decisão de apostar ou não é sua. Eu também não tenho acesso a odds em tempo real nem a nenhuma informação que "saiba" o resultado.

E vale entender por que nenhum palpite resolveria a conta. A odd que a casa oferece já leva em conta o que se sabe do jogo: escalação, fase, mando de campo. A sensação de que entender de futebol dá vantagem é uma das mais comuns de quem aposta (na literatura, **ilusão de controle**), mas ela não tira a **margem da casa**, que está embutida em todas as odds. Numa odd 2,00, a casa paga como se a chance fosse 50%; tirando a margem de referência de 5%, a chance estimada é de cerca de 48%. De cada R$ 100 apostados, voltam em média cerca de R$ 95.

O que eu posso fazer: explicar o que quer dizer a odd do jogo que você está olhando, ou mostrar na aba **Simulador** o que acontece com 100 pessoas que apostam assim por um tempo.

Fonte: parâmetros éticos do projeto; relação entre odd e probabilidade (bibliografia de Probabilidade e Estatística)."""

_PADROES_PALPITE = [
    r"\bpalpites?\b",
    r"\bdevo apostar\b",
    r"\bvale (a pena )?apostar (no|na|nos|nas|em)\b",
    r"\bquem (vai )?(ganha|ganhar|vence|vencer|leva|levar)\b",
    r"\b(qual|que) (time|placar|resultado) (vai|deve|ganha|vence|leva)",
    r"\b(vai|deve) (ganhar|vencer|perder|empatar) (o jogo|hoje|amanha|esse|este|de)\b",
    r"\bquantos gols (vai|vao|sai|saem)\b",
    r"\baposta (mais )?(certa|segura|garantida|boa pra hoje|boa para hoje)\b",
    r"\b(me )?(da|de|manda|passa|indica) (uma |umas |alguma |algumas )?dicas?\b",
    r"\bdicas? (de|pra|para) aposta",
    r"\b(qual|quais) (a |e a |sao as )?(melhor|melhores) (aposta|apostas|casa|casas|bet|bets|site|sites)\b",
    r"\bem quem (eu )?(aposto|apostar)\b",
]


def _normalizar(texto):
    import unicodedata
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def eh_pedido_de_palpite(texto):
    """True quando a mensagem pede palpite, previsão de resultado ou indicação de aposta/casa."""
    import re
    t = _normalizar(texto or "")
    return any(re.search(p, t) for p in _PADROES_PALPITE)


RESPOSTAS_PRONTAS = {
    "Como funciona uma aposta esportiva?": P1,
    "Se eu acertar mais da metade das minhas apostas, eu lucro?": P5,
    "Vale a pena dobrar a aposta para recuperar o que perdi?": P8,
    "Se eu apostar R$ 20 por rodada do Brasileirão numa odd 2,20, quanto isso pode custar?": CENARIO,
}
