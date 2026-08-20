# Arquitetura

Como o bot funciona por dentro, e por que cada decisão está do jeito que está.
O código não tem comentário: o "porquê" mora aqui.

Leia junto com [BANCO.md](BANCO.md) (o que fica gravado) e
[COMANDOS.md](COMANDOS.md) (o que aparece no Discord).

## O princípio

O único número em que dá para confiar é o que o bot mede sozinho.

Relatório feito só de auto-declaração mede disciplina de preencher formulário,
não estudo. Por isso tempo em call, revisão do Anki e card que não gruda são
capturados sem digitação, e só sobra para digitar o que nenhum sensor pega:
questão feita, erro cometido e aula assistida.

Esse princípio explica quase toda escolha abaixo. Na dúvida entre perguntar e
medir, é medir.

## Os módulos

| Arquivo | Responsabilidade | Não faz |
|---|---|---|
| `sentinela.py` | o bot: eventos, tarefas agendadas, comandos, montagem dos embeds | não fala SQL, não fala com o Anki direto |
| `db.py` | esquema, migração e toda consulta ao SQLite | não conhece Discord |
| `anki_sync.py` | AnkiConnect: entrega de card, estatística da coleção, export `.apkg` | não conhece Discord |
| `config/estrutura.py` | categorias, canais, fóruns, tags e plano de reconversão | não roda nada |
| `config/agenda.py` | as 14 semanas do plano, e o bloco de cada dia | não roda nada |
| `config/marcos.json` | concursos, datas e a marca de fonte primária | — |
| `config/credenciais.py` | valida token e guild id antes de subir | — |

A regra é essa: `sentinela.py` orquestra, `db.py` persiste, `anki_sync.py`
integra. Nenhum SQL solto no bot, nenhum `discord.` fora do bot.

Estrutura de servidor e plano de estudo são **dado**, em `config/`. Trocar de
concurso é trocar `marcos.json` e `agenda.py`, sem tocar em código.

## O caminho de um dia

```
07h00   briefing_diario ......... #editais-e-prazos  (só se há prazo a cobrar, ou segunda)
17h45   aviso_do_bloco .......... #metas-do-dia      (dia útil)
09h15   aviso_do_bloco .......... #metas-do-dia      (sábado e domingo)
        entra na call ........... sessão abre sozinha
        /questoes /erro /aula ... registro manual, menos de 1 min no dia
        sai da call ............. sessão fecha, #diario anuncia se passou de 10 min
a/30min ler_anki ................ entrega a fila de cards e fotografa a coleção
/simulado ....................... #simulados, avisa na metade, aos 30 e aos 10
02h00   fechamento_diario ....... #diario, fechando o dia ANTERIOR
dom 20h relatorio_semanal ....... #marcos (ou #diario)
```

## Ciclo de vida

### `setup_hook`

Roda a migração do `estado.json` antigo e liga os seis loops. Só isso.

Sessão órfã **não** é fechada aqui. Quem ainda está na call continua estudando,
e fechar cegamente picava a sessão dela em pedaços a cada restart. O tratamento
certo precisa saber quem está em call agora, e essa informação só existe depois
do `on_ready`.

### `on_ready`

Três coisas, nesta ordem:

1. **Resolve a guild.** `guild_alvo()` aceita `DISCORD_GUILD_ID` vazio ou
   errado: com o bot em um servidor só não há ambiguidade, então cai no
   primeiro. A comparação com `cliente.user.id` existe porque o erro comum é
   colar a *application id* no lugar da guild id.
2. **Sincroniza os comandos.** O sync não pode ir no `setup_hook`: lá o cache
   de guilds ainda está vazio. Aqui a guild já está resolvida de verdade. Roda
   uma vez só por processo, guardado em `_comandos_sincronizados`.
3. **Reconcilia as sessões de voz.** Quem está em call agora entra em `em_call`
   e tem a sessão **preservada**; o resto é fechado por `db.fechar_orfas()`.
   Sem isso, cada restart transformava uma sessão de 50 minutos em cinco de 10.

Sessão órfã fecha pelo último instante plausível, com teto de 4 horas. Perder
hora estudada desmotiva mais que contar de menos, mas sessão aberta há mais de
4h é o bot que caiu, não alguém estudando.

## As seis tarefas

### `briefing_diario` (07h00)

Monta o farol de prazos e só publica se houver marco dentro do limite, ou se
for segunda-feira. Bot que fala todo dia sem ter o que dizer vira ruído, e aí
ninguém lê quando importa.

Quando há prazo a cobrar, menciona `⚔️ Maidens`, reage com ✅ na própria
mensagem e vincula a mensagem aos marcos em `mensagens_marco`. É esse vínculo
que faz a reação valer como confirmação depois.

O farol: vermelho a 7 dias se o marco é crítico, a 3 se não é; amarelo até 15;
verde acima disso; preto quando passou.

### `aviso_do_bloco` (17h45 e 09h15)

O loop dispara nos dois horários e a guarda `fim_de_semana != (agora.hour < 12)`
descarta o que não corresponde ao dia. Um aviso único às 17h45 chegava **depois**
do bloco de sábado ter passado, o que é pior que não avisar.

Publica 15 minutos antes do bloco, com o conteúdo do dia vindo de
`agenda.bloco_do_dia()`. Sem isso o começo do bloco vira decisão, e decisão no
fim do dia é onde o plano se perde.

### `ler_anki` (a cada 30 min)

Entrega a fila de cards e fotografa a coleção, nesta ordem.

Roda em `asyncio.to_thread`, então **precisa da própria conexão**: objeto SQLite
pertence à thread que o criou, e passar a conexão global levantou
`ProgrammingError` na primeira subida. É o que `_sincronizar_anki_isolado()`
faz: abre, usa, fecha. O WAL cuida da concorrência com a conexão do bot.

A entrega mora aqui, e não só no `anki_sync.py` rodado à mão, porque a promessa
é que `/erro` faz o card aparecer sozinho.

Silencioso de propósito: Anki fechado é o estado normal, não um erro que mereça
aviso. Falha só imprime no console, e a fila fica intacta para a próxima volta.

### `fechamento_diario` (02h00)

Fecha o dia **anterior**, não o corrente. O padrão de estudo aqui é até tarde,
com sessão atravessando a meia-noite. Fechando às 22h30, tudo que acontecia
depois ficava fora do log do próprio dia, justamente nas noites mais produtivas.

`db.fechar_dia()` é idempotente (`INSERT OR REPLACE` na chave `dia, usuario_id`),
então rodar de novo recalcula em vez de duplicar.

Dia sem nada registrado sai em vermelho, com o que estava previsto. É isso que
permite responder depois "cumpri 9 dos 14 dias da S1", que nenhum outro número
responde sozinho.

### `vigiar_simulados` (a cada minuto)

O único loop de minuto em minuto, e ele existe porque simulado tem hora para
acabar. Para cada simulado aberto no banco: se o tempo virou, encerra e anuncia;
se não, olha quais avisos venceram e ainda não foram dados.

O estado mora no banco, não em memória, então o cronômetro sobrevive a restart:
subir de novo no meio de um simulado de 3h30 não repete o aviso dos 30 minutos
nem esquece de anunciar o fim. Se o bot ficou fora do ar e várias marcas
venceram de uma vez, ele grava todas como dadas e anuncia só a mais urgente.

A contagem regressiva visível não é trabalho do bot: a mensagem leva um
timestamp do Discord (`<t:…:R>`), e quem conta é o cliente de quem está lendo.

### `relatorio_semanal` (domingo 20h)

O loop roda todo dia às 20h e sai fora se não for domingo. `tasks.loop(time=...)`
não filtra dia da semana, então o filtro é na mão.

Publica em `#marcos`, com `#diario` de reserva.

## Eventos

### `on_voice_state_update`

Abre sessão ao entrar em canal da categoria `🔊 SALA DE ESTUDO`, fecha ao sair.
A comparação `antes.channel != depois.channel` evita reagir a mute, deafen e
troca de estado que não é entrada nem saída.

Anúncio em `#diario` só a partir de 10 minutos. Abaixo disso é gente entrando e
saindo, e o canal viraria log de porta.

### `on_message`

Só escuta `#erros-do-dia`. Toda mensagem conta como erro. Se contiver `::`, o
texto vira card: `[matéria] frente :: verso`, com a matéria opcional.

Sem a intent **MESSAGE CONTENT**, `msg.content` vem vazio: dá para contar que
houve erro, mas não para montar o card. Por isso a reação diz o que aconteceu:

- 📗 virou card e entrou na fila do Anki
- 📝 foi contado, mas o card só sai pelo `/erro`

### `on_raw_reaction_add`

✅ em mensagem de briefing confirma os marcos vinculados àquela mensagem, grava
quem confirmou e quando, e o bot para de cobrar. É `raw` de propósito: a
mensagem pode ser de dias atrás e já ter saído do cache.

### `on_member_join`

Boas-vindas curtas, com as três coisas que a pessoa precisa fazer. Não é tour
pelos 15 canais.

## Armadilhas registradas

Cada uma dessas custou um bug em produção.

**`mensagem_id` é `None`, nunca `0`.** A coluna é `UNIQUE`, e o SQLite aceita
vários `NULL` mas só um `0`. Com `card_id or 0`, o segundo `/erro` do dia que
caísse em duplicata era engolido pelo `INSERT OR IGNORE` e sumia da contagem.

**`CREATE TABLE IF NOT EXISTS` não altera tabela que já existe.** Coluna nova em
tabela antiga precisa entrar na lista `MIGRACOES` do `db.py`, senão o banco em
produção fica com o esquema velho e o `INSERT` quebra em runtime. Foi exatamente
o que aconteceu com `log_diario` quando `aulas` entrou.

**Conexão SQLite não atravessa thread.** Qualquer coisa dentro de
`asyncio.to_thread` abre a própria conexão.

**Intents privilegiadas.** `members` é obrigatória (boas-vindas e cargo);
`message_content` é opcional, e sem ela `#erros-do-dia` conta mas não vira card.
As duas se ligam no portal do Discord, não no código.

**Hierarquia de cargo.** O cargo do bot tem que estar acima dos cargos que ele
gerencia, senão atribuir cargo e expulsar membro falham mesmo com Administrador.

**Aula e call medem coisas diferentes e podem se sobrepor.** Assistir aula
dentro da sala de voz conta nas duas. Por isso o relatório traz a nota de que os
dois números não somam: sem ela, "2h em call" e "2h de aula" viram 4h que nunca
existiram.

**Marco de fonte secundária não recebe contagem regressiva.** `marcos_ativos()`
ignora concurso com `"verificado": false`. Contar dias para data que ninguém
publicou é fabricar urgência, e urgência fabricada estraga a confiança no bot
inteiro.

## Onde mexer

| Quero mudar | Mexo em |
|---|---|
| horário de qualquer tarefa | constantes `HORA_*` no topo do `sentinela.py` |
| canal onde o bot publica | constantes `CANAL_*` no topo do `sentinela.py` |
| concursos, datas, marcos | `config/marcos.json` |
| conteúdo das 14 semanas | `config/agenda.py` |
| canais, fóruns e tags do servidor | `config/estrutura.py` |
| deck de destino por matéria | `MAPA_DECK` no `anki_sync.py` |
| nova coluna em tabela existente | `ESQUEMA` **e** `MIGRACOES`, no `db.py` |
