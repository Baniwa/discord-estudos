# Como usar o servidor

Não é para ler inteiro. O que importa está no primeiro bloco.

## O ciclo do dia, em 6 passos

Tudo isso soma menos de 2 minutos de digitação. O resto é estudo.

**1. Antes de começar, uma linha em `#metas-do-dia`.**
Não é planejamento, é compromisso. "hoje: ato administrativo, 45min + 20 questões".
Se você não consegue escrever a meta em uma linha, ela está grande demais.

**2. Entra em `🔇 Estudo Silencioso`.**
Isso é o registro de ponto. O bot cronometra sozinho, não precisa avisar nada.
Mic e câmera desligados, ninguém fala. A presença da outra é o ponto, não a
conversa. Se a Lari estiver lá, você entra. Se não estiver, você entra do mesmo
jeito, porque ela vai ver que você está.

**3. Estuda o bloco.**
18h00 às 19h45 nos dias úteis: 20 min de português, 45 min de conteúdo novo,
40 min de questões corrigidas na hora.

**4. Todo erro vai para `#erros-do-dia`, na hora.**
Uma mensagem por erro. O bot marca 📗 quando registra. Esse é o canal que
alimenta o Anki, e é o único cuja ausência significa que o dia não aconteceu.
Não deixe acumular para o fim de semana, porque no fim de semana você não
lembra por que errou.

**5. `/questoes` no fim do bloco.**
`/questoes materia:administrativo feitas:20 acertos:13`. Quinze segundos.

**6. `/estudei` se fechou o mínimo de 1 hora.**
Alimenta o streak. Em dia ruim o mínimo é 30 min de conteúdo mais 10 questões.
Reduzir vale, pular não.

## O que não fazer

Isso importa mais que a lista de cima, porque é o que mata servidor de estudo.

**Não use os fóruns como caderno de resumo.** Fórum é para dúvida e para
conclusão, não para transcrever PDF. Resumo vira card no Anki, não post.

**Não escreva em `#diario` na mão.** O bot preenche quando você fecha sessão de
call.

**Não crie canal novo.** A estrutura é por matéria exatamente para não crescer.
Se surgiu assunto novo, ele é uma tag ou um post dentro de um fórum que já
existe.

**Não poste conteúdo em `#editais-e-prazos`.** Ali só entra fonte primária, e
quem posta é o bot.

## Os fóruns, na prática

Um post por **tema**, nunca por dia.

O título é o conceito, não a data: "Ato administrativo: convalidação" e não
"Estudo de 17/08". A tag é a matéria.

Quando o assunto voltar, você **volta no post e edita**, em vez de abrir outro.
O post cresce e vira a página daquele conceito. É a mesma lógica do cofre no
Obsidian: a página se reescreve em vez de virar pilha cronológica.

`#duvidas` tem tag `aberta` e `resolvida`. Marca `resolvida` quando fechar,
porque dúvida resolvida vira material de revisão e dúvida aberta vira fila.

## O que cada uma traz

Eu sou fullstack e uso AWS. A Lari é frontend. Isso cobre engenharia de software
por dois ângulos e resolve boa parte do `#duvidas` sem precisar de fora.

O que nenhuma das duas domina é **redes, infraestrutura e auditoria de sistemas**.
É onde o estudo em par rende mais, e é onde a prova do BACEN concentra questão.
Auditoria de sistemas é o único vermelho de TI das duas, e é justamente o que
define o destino da trilha.

## O ciclo da semana

**Domingo às 20h o bot fecha o relatório sozinho.**

Ele lista tempo em call por pessoa, questões por matéria **da pior para a
melhor**, dias com o mínimo, erros lançados e a projeção de questões até 22/11.

A leitura é uma só: **a matéria que aparece no topo da lista de piores é o
conteúdo da semana seguinte.** Não é para discutir, é para pautar.

`/relatorio` puxa a qualquer momento, em 7, 14 ou 30 dias.

## Onde cada coisa mora

O Discord não substitui o resto, e não é para virar depósito.

| Ferramenta | Papel |
|---|---|
| **Discord** | execução e cobrança. O que aconteceu hoje. |
| **Anki** | retenção. O que precisa voltar amanhã e daqui a 10 dias. |
| **Obsidian** | memória. Por que a decisão foi tomada, o que o edital diz. |
| **Calendar** | horário. Quando o bloco acontece. |

Erro nasce no Discord e vira card no Anki. Decisão sobre o plano nasce no
Obsidian. Se você está usando o Discord para guardar coisa que precisa durar
meses, ela está no lugar errado.

## A regra que resume tudo

Dia sem mensagem em `#erros-do-dia` é dia que não aconteceu.

Você pode ter entrado na call, ter lido o PDF, ter assistido a aula. Se não
saiu erro, não houve questão. E prova do CEBRASPE não se ganha lendo, se ganha
errando cedo.
