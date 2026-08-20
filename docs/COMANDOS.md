# Comandos, eventos e tarefas

Referência completa do que o bot expõe. Para o dia a dia, o resumo está no
[COMO-USAR.md](../COMO-USAR.md); para o funcionamento por dentro,
[ARQUITETURA.md](ARQUITETURA.md).

Os comandos são sincronizados por guild no `on_ready`, então mudança de nome ou
de parâmetro aparece no Discord no restart seguinte, sem esperar propagação
global.

## Slash commands

### `/estudei`

Sem parâmetros. Marca o mínimo inegociável do dia e devolve streak atual e
recorde. Um por dia por pessoa: chamar de novo responde em ephemeral que já
está registrado, sem duplicar. Streak de 7 dias ou mais troca o ✅ por 🔥.

### `/erro materia pergunta resposta`

| Parâmetro | Tipo | Obrigatório |
|---|---|---|
| `materia` | texto | sim |
| `pergunta` | texto | sim, é a frente do card |
| `resposta` | texto | sim, é o verso: o que é certo, e por quê |

Enfileira o card e registra o erro na mesma chamada. Responde com o número do
card e quantos estão pendentes na fila. A entrega ao Anki é do `ler_anki`, a
cada 30 minutos.

Alternativa sem comando: mensagem em `#erros-do-dia` no formato
`[matéria] frente :: verso`. Depende da intent MESSAGE CONTENT.

`materia` tem autocomplete (ver abaixo).

### `/questoes materia feitas acertos`

| Parâmetro | Tipo | Obrigatório |
|---|---|---|
| `materia` | texto | sim, gravada em minúscula |
| `feitas` | inteiro | sim, maior que zero |
| `acertos` | inteiro | sim, entre 0 e `feitas` |

Recusa em ephemeral se os números não fecham. Abaixo de 60% vem com aviso: é a
meta de corte usada no relatório.

### `/aula disciplina aula minutos [professor] [fonte] [nota]`

| Parâmetro | Tipo | Padrão |
|---|---|---|
| `disciplina` | texto | — |
| `aula` | texto, número e título | — |
| `minutos` | inteiro de 1 a 600 | — |
| `professor` | texto | vazio |
| `fonte` | texto | `Estratégia` |
| `nota` | texto, o que ficou em uma linha | vazio |

Publica o embed em `#aulas`. Se o comando foi chamado de outro canal, a
confirmação volta em ephemeral e o registro fica só em `#aulas`.

Aula é consumo, questão é produção. O relatório mantém os dois separados de
propósito, e avisa quando a semana teve muita aula e pouca questão.

### `/simulado materia duracao`

| Parâmetro | Tipo | Padrão |
|---|---|---|
| `materia` | texto, com autocomplete | — |
| `duracao` | inteiro de 15 a 360 minutos | 210, a duração da prova do TCDF |

Abre a janela de simulado e publica em `#simulados` a hora de fim. O bot avisa
na metade (só em simulado de mais de 90 min), aos 30 e aos 10 minutos, e anuncia
o fim.

A hora de fim vai como timestamp do Discord (`<t:…:R>`), que o cliente renderiza
como contagem regressiva ao vivo. É por isso que o bot não fica editando a
mensagem de minuto em minuto: quem conta é o cliente de quem está lendo.

Uma pessoa só pode ter um simulado aberto por vez. Chamar de novo responde
quando o atual termina.

A sala de voz `🧪 Simulado` fica na categoria de estudo, então o tempo de prova
já é cronometrado pelo mesmo mecanismo das sessões, sem nada de novo. Se a sala
não existir no servidor, o comando funciona igual e aponta a categoria de
estudo — rode o `setup_servidor.py` para criá-la.

### `/resultado acertos total`

Lança a nota no último simulado seu que ainda não tem nota, e o fecha. Sem
simulado esperando nota, responde em ephemeral apontando o `/questoes`.

Nota de simulado **não** entra no ciclo de questões. São coisas diferentes:
questão treinada mede estudo, simulado mede prova, e somar as duas apaga a
única medida sob pressão que existe. O relatório mostra os dois em blocos
separados.

### Autocomplete de matéria

`/erro`, `/questoes`, `/simulado` (parâmetro `materia`) e `/aula` (parâmetro
`disciplina`) sugerem o que já foi registrado antes, da matéria mais usada
para a menos, no máximo 25 opções. Vem de `db.materias()`, que junta
questões, cards, simulados e aulas.

Não é lista fechada: matéria nova continua sendo aceita digitando. A sugestão
existe para que nome novo só nasça quando não há nenhum parecido. Tudo é gravado
em minúscula, mas isso sozinho não resolvia "adm" contra "administrativo", e a
matéria fragmentada estraga justamente o ranking da pior matéria, que é o que
pauta a semana.

### `/questoes` e `/aula` no mesmo dia

Não há vínculo entre os dois. São tabelas diferentes, e a leitura útil é a
razão entre elas no relatório, não o pareamento aula por aula.

### `/anki`

Sem parâmetros. Três blocos:

1. **Fila do bot** — cards ainda não entregues, agrupados por matéria.
2. **Coleção** — último snapshot lido do Anki, por deck, com a data da leitura.
   Se o Anki nunca esteve aberto com o AnkiConnect, diz isso em vez de mostrar
   zero.
3. **O que não gruda** — os 5 cards com mais lapsos.

Lê do banco, nunca do AnkiConnect ao vivo, então responde igual com o Anki
fechado.

### `/relatorio periodo`

`periodo` é escolha fixa: semana (7 dias), quinzena (14) ou mês (30). Mesmo
embed do relatório de domingo. Usa `defer`, porque a montagem passa dos 3
segundos de resposta imediata do Discord.

O relatório traz, nesta ordem: tempo em call por pessoa com streak, questões por
pessoa, questões por matéria da pior para a melhor, aulas, simulados, estado
do Anki, o que não gruda, consistência (dias com o mínimo e erros lançados) e a projeção de
questões até a prova.

A linha que importa é a matéria no topo da lista de piores. É ela que pauta a
semana seguinte.

### `/hoje`

Sem parâmetros. O log do dia corrente, montado na hora e **sem gravar**: usa
`db.agregar_dia()`, que é o `fechar_dia()` sem a escrita.

Existe porque o fechamento oficial só sai às 02h, quando não dá mais para
reagir. Às 21h ainda dá.

Dia vazio aqui sai em amarelo, não em vermelho. Às 10h da manhã não ter registro
não é fracasso, é cedo.

### `/bloco quando`

| Parâmetro | Escolhas | Padrão |
|---|---|---|
| `quando` | hoje, amanhã | hoje |

O que estudar segundo o plano de 14 semanas: rótulo da semana, conteúdo,
horário e estrutura do bloco. Mesmo embed que a tarefa das 17h45 publica.

O aviso automático chega 15 minutos antes do bloco e some no meio do canal.
Este comando puxa de novo a qualquer hora, e o `amanhã` serve para fechar a
noite já sabendo o que abre o dia seguinte.

### `/adesao`

Sem parâmetros. Dias com o mínimo por semana do plano, das 8 semanas mais
recentes, com a semana corrente marcada por ▶, mais o acumulado desde o começo.

É a pergunta que o `log_diario` foi criado para responder: cumpriu 9 dos 14 dias
da S1. Lê de `db.adesao()`, ou seja, dos dias **já fechados**. O dia de hoje
entra no fechamento das 02h, e o rodapé do embed diz isso.

### `/prazos`

Sem parâmetros. O mesmo embed do briefing das 07h, sob demanda: marcos
confirmados por fonte primária com contagem regressiva e farol, e abaixo os
concursos sem edital, listados sem contagem.

### `/agora`

Sem parâmetros. Quem está em call na categoria `🔊 SALA DE ESTUDO` neste
momento. Lê o estado de voz da guild, não o banco.

## O que acontece sem comando

| Gatilho | O que o bot faz |
|---|---|
| entrar em canal de `🔊 SALA DE ESTUDO` | abre a sessão e começa a cronometrar |
| sair do canal | fecha a sessão; anuncia em `#diario` se passou de 10 min |
| mensagem em `#erros-do-dia` | conta o erro; vira card se tiver `::`; reage 📗 ou 📝 |
| ✅ em mensagem de briefing | confirma o marco, grava quem confirmou e para de cobrar |
| membro novo entra | boas-vindas em `🤙🏽┇boas-vindas` com as três regras |

## Tarefas agendadas

Fuso de `config/marcos.json` (`America/Sao_Paulo`).

| Horário | Tarefa | Canal | Condição |
|---|---|---|---|
| 07h00 | `briefing_diario` | `#editais-e-prazos` | só se há prazo dentro do limite, ou se é segunda |
| 17h45 | `aviso_do_bloco` | `#metas-do-dia` | dia útil |
| 09h15 | `aviso_do_bloco` | `#metas-do-dia` | sábado e domingo |
| a cada 30 min | `ler_anki` | `#erros-do-dia` | só fala quando entregou card |
| a cada minuto | `vigiar_simulados` | `#simulados` | só quando há simulado aberto |
| 02h00 | `fechamento_diario` | `#diario` | fecha o dia anterior, sempre |
| domingo 20h | `relatorio_semanal` | `#marcos` | só domingo |

## Scripts de operação

Não são comandos do Discord. Rodam no terminal, com o bot parado ou não.

| Comando | O que faz |
|---|---|
| `python convite.py` | gera o link de convite com as permissões certas |
| `python diagnostico.py` | inventário do servidor, só leitura |
| `python setup_servidor.py --dry-run` | mostra o que faria, sem tocar em nada |
| `python setup_servidor.py` | cria e reconverte a estrutura, idempotente |
| `python semear_foruns.py` | reação padrão e post inicial dos fóruns |
| `python publicar.py` | publica regras e calendário |
| `python membros.py` | lista membros (`--remover` para aplicar) |
| `python limpar.py` | apaga o que não serve, em três faixas |
| `python anki_sync.py` | entrega a fila à mão e lê estatística |
| `python sentinela.py` | sobe o bot |

Rode o `--dry-run` antes de qualquer script que escreve.
