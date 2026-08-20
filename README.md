# Sentinela — servidor de estudos no Discord

[![CI](https://github.com/Baniwa/discord-estudos/actions/workflows/ci.yml/badge.svg)](https://github.com/Baniwa/discord-estudos/actions/workflows/ci.yml)

Bot e estrutura de servidor para quem estuda para concurso em dupla ou em grupo
pequeno. O servidor deixa de ser lugar de conversa e vira ambiente de execução:
a sala de voz é cronometrada sozinha, o erro vira card no Anki, o dia fecha em
log e a semana fecha em relatório.

`Python 3.12` · `discord.py` · `SQLite` · `AnkiConnect` · `Docker`

<!--
  Screenshots entram aqui, em docs/imagens/: briefing das 07h, /relatorio,
  log diário e /anki. Precisam ser tiradas do servidor rodando.
-->

## O princípio

O único número em que dá para confiar é o que o bot mede sozinho.

Relatório feito só de auto-declaração mede disciplina de preencher formulário,
não estudo. Então tempo em call, revisão do Anki e card que não gruda são
capturados sem digitação, e só sobra para digitar o que nenhum sensor pega:
questão feita, erro cometido e aula assistida.

## O que se digita, e o que não

| | Como | Esforço |
|---|---|---|
| Tempo estudado | entrar em `🔇 Estudo Silencioso` | **zero** |
| Revisões do Anki | abrir o Anki e revisar | **zero** |
| Cards que mais se erra | idem | **zero** |
| Questões feitas | `/questoes` | ~15 s por dia |
| Cada erro | `/erro` | ~20 s por erro |
| Aula assistida | `/aula` | ~20 s por aula |
| Fechou o mínimo | `/estudei` | 1 clique |

Menos de um minuto de digitação no dia inteiro.

## Comandos

| Comando | O quê |
|---|---|
| `/erro materia pergunta resposta` | lança o erro e enfileira o card do Anki |
| `/questoes materia feitas acertos` | registra o ciclo de questões |
| `/aula disciplina aula minutos` | registra a aula assistida em `#aulas` |
| `/estudei` | marca o mínimo do dia e alimenta o streak |
| `/hoje` | o dia até agora, sem esperar o fechamento das 02h |
| `/bloco` | o que estudar hoje ou amanhã, segundo o plano |
| `/relatorio periodo` | fecha 7, 14 ou 30 dias |
| `/adesao` | quantos dias de cada semana do plano foram cumpridos |
| `/anki` | fila do bot, estado da coleção e o que não gruda |
| `/prazos` | contagem regressiva dos editais |
| `/agora` | quem está em call de estudo |

Matéria tem autocomplete em `/erro`, `/questoes` e `/aula`, alimentado pelo que
já foi registrado. É o que impede "adm" e "administrativo" de virarem duas
linhas no relatório da pior matéria.

Parâmetro por parâmetro, validação e comportamento em
[docs/COMANDOS.md](docs/COMANDOS.md).

## O que o bot faz sozinho

| Quando | O quê |
|---|---|
| **07h00** | cobra prazo de edital, com escalada e confirmação por ✅ |
| **17h45** (seg a sex) | avisa o conteúdo do bloco, 15 min antes |
| **09h15** (sáb e dom) | idem, no horário do bloco de fim de semana |
| **02h00** | fecha o log do dia anterior e posta em `#diario` |
| **domingo 20h** | relatório da semana |
| **a cada 30 min** | entrega os cards ao Anki e fotografa a coleção |
| contínuo | cronometra call, conta erro em `#erros-do-dia`, dá boas-vindas |

### O log diário

Às 02h o bot fecha o **dia anterior** e grava. O log traz tempo em call, questões
com percentual, aulas, erros, cards novos e se o mínimo foi fechado, **ao lado do
que o calendário mandava estudar naquele dia**.

Fecha às 02h, e não às 22h30, porque sessão que atravessa a meia-noite é comum
em quem estuda depois do trabalho. Com o corte antes da virada, a noite mais
produtiva ficava fora do próprio log.

Dia sem nada registrado sai em vermelho, dizendo o que estava previsto e não
aconteceu. É isso que permite depois responder "cumpri 9 dos 14 dias da S1", que
nenhum outro número responde sozinho. `/adesao` faz exatamente essa pergunta.

### A regra que vale mais que o resto

**Marco de fonte secundária não recebe contagem regressiva.**

Infográfico de Instagram, notícia e post de professor entram no `marcos.json`
com `"verificado": false`, e o bot só lembra de conferir a fonte primária. Ele
não conta dias em cima disso.

Essa regra existe porque o projeto já emitiu dois alarmes vermelhos que se
revelaram falsos, os dois vindos de fonte secundária. Contar dias para uma data
que ninguém publicou é fabricar urgência, e urgência fabricada estraga a
confiança no bot inteiro.

## As três decisões que explicam o resto

**Canais por matéria, nunca por concurso.** Categoria por concurso morre junto
com o edital que não sai, e leva o conteúdo junto. Por matéria, os vários alvos
viram filtro sobre a mesma base.

**Voz antes de texto.** O que faz duas pessoas estudarem juntas é estar na mesma
sala em silêncio, não ter fórum bem organizado. As salas de voz são o centro; o
texto é o arquivo.

**O bot mede, não pergunta.** O que dá para medir sozinho, o bot mede. O que
precisa de digitação cabe em três comandos curtos.

## Estrutura do servidor

```
🔊 SALA DE ESTUDO    Estudo Silencioso · Pomodoro 25-5 · Discussão · English Class
🎯 COMANDO           #alvo · #metas-do-dia · #diario · #erros-do-dia · #simulados
📚 CONHECIMENTO      #nucleo-ti · #auditoria-e-direito · #basicas · #duvidas (fóruns) · #aulas
📋 LOGÍSTICA         #editais-e-prazos · #biblioteca · #marcos
🗄️ ARQUIVO           o que saiu de cena, em somente leitura
```

`#erros-do-dia` é o mais importante. Dia sem mensagem nele é dia que não
aconteceu.

O `setup_servidor.py` **reconverte** um servidor que já existe em vez de criar
tudo do zero: sala de voz antiga vira sala de estudo por renomeação, e o que sai
de cena vai para `🗄️ ARQUIVO`, em somente leitura. Nada é apagado.

## Instalação

```bash
pip install -r requirements.txt
cp .env.example .env
```

No `.env` só o token é obrigatório. `DISCORD_GUILD_ID` é opcional: com o bot em
um servidor só, os scripts descobrem sozinhos.

O token fica em discord.com/developers/applications, aba **Bot** (não em General
Information), botão Reset Token. Ligue também a intent privilegiada
**SERVER MEMBERS** e, se quiser que mensagem solta em `#erros-do-dia` vire card,
**MESSAGE CONTENT**.

Convide o bot pelo link que o `convite.py` gera. Ele precisa de Administrador, e
o cargo dele tem que ficar **acima** dos cargos que ele vai gerenciar, senão
expulsar membro e atribuir cargo falham por hierarquia.

Para deixar de pé 24 horas, em Docker numa VM, veja [DEPLOY.md](DEPLOY.md).

## Scripts

```bash
python convite.py                    # link de convite do bot
python diagnostico.py                # inventário do servidor, só leitura
python setup_servidor.py --dry-run   # mostra o que faria, sem tocar em nada
python setup_servidor.py             # cria e reconverte a estrutura
python semear_foruns.py              # reação padrão e post inicial dos fóruns
python publicar.py                   # regras e calendário
python membros.py                    # lista membros (--remover para aplicar)
python limpar.py                     # apaga o que não serve, em 3 faixas
python anki_sync.py                  # entrega cards e lê estatística
python sentinela.py                  # sobe o bot
```

Rode sempre o `--dry-run` antes. `setup_servidor.py` é idempotente: cria só o
que falta, não duplica e não apaga.

## Como adaptar ao seu concurso

Toda a estrutura vive em `config/`, como dado. Não precisa mexer no código.

| Arquivo | O que você troca |
|---|---|
| `config/marcos.json` | seus concursos, datas e marcos, cada um marcado como fonte primária ou não |
| `config/agenda.py` | as semanas do seu plano: `(início, fim, rótulo, conteúdo)` e os blocos fixos da rotina |
| `config/estrutura.py` | categorias, canais, fóruns, tags e o plano de reconversão |
| `.env` | token, guild, canal de prazos e quem é isento no `membros.py` |

O que vem no repo é o plano real de uma dupla mirando o **TCDF 2026** (Analista
de Controle Externo), com BB, ANPD e BACEN como alvos seguintes e prova em
22/11/2026. Serve como exemplo completo e testado, não como sugestão de estudo:
troque por seus dados.

Constantes que talvez você queira ajustar, todas no topo do `sentinela.py`:
horário das tarefas (`HORA_*`), nomes de canal (`CANAL_*`), a categoria das
salas de estudo e o cargo mencionado nas cobranças.

O mapeamento de matéria para deck do Anki fica em `MAPA_DECK`, no
`anki_sync.py`.

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check .
```

55 testes, sem token, sem Discord e sem Anki. A CI roda os dois comandos em
Python 3.12 e 3.13 a cada push e pull request. Detalhes em
[docs/TESTES.md](docs/TESTES.md).

## Documentação

O código não leva comentário narrativo. O "porquê" de cada decisão mora aqui.

| Documento | Para quê |
|---|---|
| [COMO-USAR.md](COMO-USAR.md) | o ciclo do dia, para quem só vai estudar |
| [docs/COMANDOS.md](docs/COMANDOS.md) | todo comando, parâmetro, validação, evento e tarefa |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | módulos, ciclo de vida, os cinco loops e as armadilhas que já custaram bug |
| [docs/BANCO.md](docs/BANCO.md) | tabela por tabela, migrações e a API do `db.py` |
| [docs/TESTES.md](docs/TESTES.md) | como rodar, o que a suíte garante e como escrever mais |
| [DEPLOY.md](DEPLOY.md) | subir e manter no ar |

Mudou comportamento, muda o documento no mesmo commit. Documento que descreve
horário que não é mais o horário é pior que documento nenhum.

## Arquivos

| Arquivo | O quê |
|---|---|
| `sentinela.py` | o bot: eventos, tarefas, comandos e os embeds |
| `db.py` | SQLite: sessões, questões, aulas, erros, cards, log diário, snapshot do Anki |
| `anki_sync.py` | entrega de cards e leitura da coleção |
| `config/estrutura.py` | categorias, canais, fóruns, tags e o plano de reconversão |
| `config/agenda.py` | as semanas do plano |
| `config/marcos.json` | concursos e datas, marcando fonte primária ou secundária |
| `config/credenciais.py` | valida token e guild id, e diz qual campo do portal foi colado errado |
| `estudos.db` | gerado em runtime, fora do git |

`.env`, `estudos.db` e `*.apkg` estão no `.gitignore`.

## Branches

Gitflow. `main` é o que está rodando, `develop` é a integração, e cada mudança
nasce em `feature/<nome>` a partir de `develop`.

```bash
git checkout develop
git checkout -b feature/minha-mudanca
git push -u origin feature/minha-mudanca
```

Merge para `develop` via PR, com `--no-ff`. Direto na `main` só release.

## Licença

MIT. Veja [LICENSE](LICENSE).
