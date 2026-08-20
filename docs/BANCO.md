# Banco

SQLite em `estudos.db`, na raiz do repo, fora do git. `DB_PATH` sobrescreve o
caminho, que é como o Docker aponta para um volume.

`db.conectar()` liga o **WAL** (sobrevive a queda no meio da escrita), aplica o
`ESQUEMA` inteiro com `CREATE TABLE IF NOT EXISTS` e roda as `MIGRACOES`. Chamar
é barato e seguro: todo script abre a própria conexão assim.

Cada thread abre a sua. Conexão SQLite pertence à thread que a criou.

## Tabelas

### `sessoes_voz`

Uma linha por entrada em canal de estudo. `fim` e `segundos` ficam `NULL`
enquanto a sessão está aberta, e é assim que o bot sabe o que reconciliar
quando sobe.

Este é o único dado do banco que ninguém digitou.

### `questoes`

Ciclo de questões, por pessoa, dia e matéria. A matéria entra em minúscula e
sem espaço nas pontas, senão "Administrativo" e "administrativo " viram duas
linhas diferentes no relatório.

### `aulas`

Aula assistida. Separada de `questoes` de propósito: assistir é consumo,
resolver é produção, e misturar os dois num número só esconde a semana em que
houve só aula.

### `minimos`

Um registro por pessoa por dia, chave primária composta. É o que alimenta o
streak. `registrar_minimo()` devolve `False` quando o dia já estava marcado, e
é assim que o `/estudei` sabe responder sem duplicar.

`streak()` calcula na leitura, percorrendo os dias: streak atual e recorde.
Quebra quando o último registro tem mais de um dia de diferença de hoje.

### `erros`

Contagem de erros lançados. `mensagem_id` é `UNIQUE` e aceita `NULL`: guarda o
id da mensagem quando o erro veio de `#erros-do-dia`, e o id do card quando veio
do `/erro`. **Nunca `0`** — o SQLite aceita vários `NULL` mas só um `0`, e o
zero engolia registros no `INSERT OR IGNORE`.

### `cards`

Fila de cards até a entrega ao Anki. Pendente é `entregue_em IS NULL`.

A fila existe porque o Anki não fica sempre aberto, e pode nem estar na mesma
máquina do bot. Sem ela, erro lançado com o Anki fechado se perderia, que é
justamente quando mais se estuda. Card só sai da fila quando a entrega deu
certo.

### `anki_snapshot`

Fotografia da coleção por dia e deck: novos, aprendendo, a revisar e revisados
hoje. Chave `(dia, deck)`, gravada com `INSERT OR REPLACE`, então a leitura mais
recente do dia vale.

Existe porque o bot pode estar de pé com o Anki fechado. O relatório lê daqui,
não do AnkiConnect, e por isso funciona às 20h de domingo com o Anki desligado.

### `anki_dificeis`

Card com mais lapsos, com facilidade e intervalo. É o único sinal do Anki que
muda o que estudar na semana seguinte: card que não gruda é conceito para voltar
ao bloco de conteúdo, não para revisar mais forte.

### `simulados`

Uma linha por janela de simulado: matéria, duração, início, fim previsto, a
mensagem que anunciou e a nota quando ela chega.

Fica no banco, e não em memória, porque simulado de 3h30 não pode depender de o
processo ficar de pé o tempo todo. `avisos` guarda as marcas já anunciadas
("metade", "30", "10"), então o bot que sobe no meio do simulado não repete o
aviso dos 30 minutos.

Simulado sem `total` é simulado sem nota lançada, e é o que o `/resultado`
procura. Simulado sem `encerrado_em` é simulado correndo, e é o que o loop de
um minuto vigia.

Nota de simulado não é gravada em `questoes` de propósito. Questão treinada e
prova sob pressão medem coisas diferentes, e somar as duas apaga a segunda.

### `log_diario`

Fechamento do dia, uma linha por pessoa, chave `(dia, usuario_id)`. Guardado, e
não só postado, porque é o que permite dizer depois "cumpriu 9 dos 14 dias da
S1", adesão ao plano, que nenhuma das outras tabelas responde sozinha.

`fechar_dia()` reagrega tudo do zero e grava com `INSERT OR REPLACE`, então é
idempotente: rodar de novo no mesmo dia recalcula em vez de duplicar.

### `confirmacoes` e `mensagens_marco`

`mensagens_marco` liga a mensagem do briefing aos marcos que ela cobrava;
`confirmacoes` guarda quem reagiu ✅ e quando. Marco confirmado some de
`marcos_ativos()`, e o bot para de cobrar.

Duas tabelas em vez de uma porque a mesma mensagem pode cobrar vários marcos.

## Migrações

`CREATE TABLE IF NOT EXISTS` não altera tabela que já existe. Coluna nova em
tabela antiga precisa entrar em **duas** listas do `db.py`:

```python
# 1. no ESQUEMA, para banco novo
# 2. em MIGRACOES, para banco que já existe
MIGRACOES = [
    ("log_diario", "aulas", "INTEGER NOT NULL DEFAULT 0"),
    ("log_diario", "minutos_aula", "INTEGER NOT NULL DEFAULT 0"),
]
```

`migrar()` consulta `pragma_table_info`, pula o que já existe, pula tabela que
ainda não foi criada e aplica o resto. Roda em toda conexão e imprime o que
aplicou.

Esquecer a segunda lista quebra em runtime, no `INSERT`, no servidor, com o
banco velho. Foi o que aconteceu quando `aulas` entrou no `log_diario`.

## API do `db.py`

Nenhum SQL vive fora deste arquivo.

| Função | Devolve |
|---|---|
| `conectar()` | conexão pronta, com esquema e migração aplicados |
| `abrir_sessao` / `fechar_sessao` | abre; fecha e devolve os segundos |
| `fechar_orfas(preservar)` | fecha sessão aberta por queda, teto de 4h, preservando quem está em call |
| `registrar_questoes` / `registrar_aula` / `registrar_erro` | grava |
| `registrar_minimo` | `False` se o dia já estava marcado |
| `streak(usuario_id)` | `(atual, recorde)` |
| `enfileirar_card` / `cards_pendentes` / `marcar_entregue` | fila do Anki |
| `periodo(dias)` / `resumo(desde, ate)` | janela e agregado do relatório |
| `aulas_periodo` / `aulas_por_pessoa` | aulas agregadas |
| `agregar_dia(dia)` | o dia por pessoa, sem gravar; é o que o `/hoje` usa |
| `fechar_dia(dia, semana)` | agrega, grava e devolve a linha de cada pessoa |
| `adesao(desde, ate)` | dias com log, dias com o mínimo e tempo, por pessoa |
| `materias(prefixo)` | matérias já usadas, da mais frequente para a menos |
| `abrir_simulado` / `simulado_aberto_de` / `simulados_abertos` | janela de simulado |
| `marcar_aviso` / `encerrar_simulado` | estado do cronômetro, que sobrevive a restart |
| `simulado_sem_resultado` / `registrar_resultado` / `simulados_periodo` | nota do simulado |
| `gravar_snapshot_anki` / `gravar_dificeis` | escrita vinda do `anki_sync` |
| `anki_ultimo_snapshot` / `anki_revisados` / `anki_top_dificeis` | leitura para relatório e `/anki` |
| `confirmar_marco` / `marcos_confirmados` / `vincular_mensagem` / `marcos_da_mensagem` | marcos |
| `migrar_estado_json(caminho)` | importa o `estado.json` da primeira versão |

`aulas_por_pessoa()` está pronta e ainda não tem comando que a use.

## Backup

O banco é o histórico inteiro: quantos dias foram cumpridos, o que não gruda,
quanto tempo em call. Não é recuperável a partir do Discord.

`backup.sh` roda com o bot no ar: usa o `.backup` do sqlite dentro do container,
que sai consistente mesmo com escrita acontecendo, e guarda os 14 mais recentes.
Copiar o arquivo na mão com o WAL ligado pode gerar um banco truncado.
