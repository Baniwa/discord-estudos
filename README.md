# Servidor de estudos

Estrutura e bot do servidor onde eu e a Larissa estudamos para concurso.

O destino é **Auditor Fiscal de TI da SEFAZ-DF**. Os quatro concursos abaixo são
degraus até lá, nesta ordem:

| # | Concurso | Situação |
|---|---|---|
| 1 | **TCDF 2026**, Analista Adm. de Controle Externo | edital publicado, prova em 22/11/2026, CEBRASPE |
| 2 | **BB**, Agente de Tecnologia | sem edital |
| 3 | **ANPD**, Especialista em Regulação de Proteção de Dados | sem edital |
| 4 | **BACEN**, Técnico / Auditor / Procurador | sem edital |

## As três decisões que explicam o resto

**Canais por matéria, nunca por concurso.** Categoria por concurso morre junto
com o edital que não sai. Eu já tinha um cronograma inteiro montado em cima do
concurso da SEFAZ-DF, que nunca foi publicado, e tive que resgatar à mão uns 70%
do conteúdo quando troquei para o TCDF. Por matéria, os cinco alvos viram filtro
sobre a mesma base.

**Voz antes de texto.** O que faz duas pessoas estudarem juntas é estar na mesma
sala em silêncio, não ter fórum bem organizado. As salas de voz são o centro.

**O bot mede, não pergunta.** Relatório feito só de auto-declaração mede
disciplina de preencher formulário. O que dá para medir sozinho (tempo em call,
revisão do Anki, card que não gruda) o bot mede.

## O que você digita, e o que não

| | Como | Esforço |
|---|---|---|
| Tempo estudado | entrar em `🔇 Estudo Silencioso` | **zero** |
| Revisões do Anki | abrir o Anki e revisar | **zero** |
| Cards que você mais erra | idem | **zero** |
| Questões feitas | `/questoes` | ~15 s por dia |
| Cada erro | `/erro` | ~20 s por erro |
| Aula assistida | `/aula` | ~20 s por aula |
| Fechou 1h | `/estudei` | 1 clique |

Menos de um minuto de digitação no dia inteiro.

## Comandos

| Comando | O quê |
|---|---|
| `/erro materia pergunta resposta` | lança o erro e enfileira o card do Anki |
| `/questoes materia feitas acertos` | registra o ciclo de questões |
| `/aula disciplina aula minutos` | registra a aula assistida em `#aulas` |
| `/estudei` | marca o mínimo de 1h do dia e alimenta o streak |
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
aqui. Com o corte antes da virada, a noite mais produtiva ficava fora do próprio
log.

Dia sem nada registrado sai em vermelho, dizendo o que estava previsto e não
aconteceu. É isso que permite depois responder "cumpri 9 dos 14 dias da S1", que
nenhum outro número responde sozinho.

### A regra que vale mais que o resto

**Marco de fonte secundária não recebe contagem regressiva.**

Infográfico de Instagram, notícia e post de professor entram no `marcos.json`
com `"verificado": false`, e o bot só lembra de conferir a fonte primária. Ele
não conta dias em cima disso.

Isso está aqui porque eu já levei dois alarmes vermelhos que se revelaram falsos,
os dois vindos de fonte secundária. Contar dias para uma data que ninguém publicou
é fabricar urgência, e urgência fabricada estraga a confiança no bot inteiro.

## Estrutura do servidor

```
🔊 SALA DE ESTUDO    Estudo Silencioso · Pomodoro 25-5 · Discussão · English Class
🎯 COMANDO           #alvo · #calendario · #metas-do-dia · #diario · #erros-do-dia · #simulados
📚 CONHECIMENTO      #nucleo-ti · #auditoria-e-direito · #basicas · #duvidas (fóruns) · #aulas
📋 LOGÍSTICA         #editais-e-prazos · #biblioteca · #marcos
👅 LINGUAGENS        javascript · html-e-css · python · bash · linux
☕ CYBER LOUNGE      bate-papo · memes · img
🗄️ ARQUIVO           o que saiu de cena, em somente leitura
```

`#erros-do-dia` é o mais importante. Dia sem mensagem nele é dia que não
aconteceu.

O servidor existia desde fevereiro de 2023 com outra função, então o setup
reconverte em vez de criar do zero. As salas de voz antigas viraram as de estudo
por renomeação. Nada foi apagado: o que saiu de cena foi para `🗄️ ARQUIVO`.

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

## Anki

`/erro` põe o card numa fila no banco. O bot entrega ao Anki a cada 30 minutos,
quando o Anki estiver aberto, e avisa em `#erros-do-dia` quando entregou.

A fila existe porque o Anki não fica sempre aberto, e pode nem estar na mesma
máquina do bot. Card só sai da fila quando a entrega deu certo, então Anki
fechado não perde nada.

Sem AnkiConnect, o `anki_sync.py` gera um `.apkg` para importar à mão.

O tipo de nota é descoberto na coleção, não chumbado: numa instalação em
português ele chama `Básico`, com campos `Frente` e `Verso`.

Decks: `TCDF::Administrativo`, `::AFO`, `::Lei local`, `::Específicos`,
`::Português`. Matéria que não casa cai em Específicos, em vez de criar deck novo
a cada digitação diferente.

## Arquivos

| Arquivo | O quê |
|---|---|
| `config/estrutura.py` | categorias, canais, fóruns, tags e o plano de reconversão |
| `config/agenda.py` | as 14 semanas do plano de 100 dias |
| `config/marcos.json` | concursos e datas, marcando fonte primária ou secundária |
| `config/credenciais.py` | valida token e guild id, e diz qual campo do portal foi colado errado |
| `db.py` | SQLite: sessões, questões, erros, cards, log diário, snapshot do Anki |
| `sentinela.py` | o bot |
| `anki_sync.py` | entrega de cards e leitura da coleção |
| `estudos.db` | gerado em runtime, fora do git |

`.env`, `estudos.db` e `*.apkg` estão no `.gitignore`.

## Documentação

O código não leva comentário. O "porquê" de cada decisão mora aqui.

| Documento | Para quê |
|---|---|
| [COMO-USAR.md](COMO-USAR.md) | o ciclo do dia, para quem só vai estudar |
| [docs/COMANDOS.md](docs/COMANDOS.md) | todo comando, parâmetro, validação, evento e tarefa |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | módulos, ciclo de vida, os cinco loops e as armadilhas que já custaram bug |
| [docs/BANCO.md](docs/BANCO.md) | tabela por tabela, migrações e a API do `db.py` |
| [DEPLOY.md](DEPLOY.md) | subir e manter no ar |

Mudou comportamento, muda o documento no mesmo commit. Documento que descreve
horário que não é mais o horário é pior que documento nenhum.

## Branches

Gitflow. `main` é o que está rodando, `develop` é a integração, e cada mudança
nasce em `feature/<nome>` a partir de `develop`.

```bash
git checkout develop
git checkout -b feature/minha-mudanca
git push -u origin feature/minha-mudanca
```

Merge para `develop` via PR, com `--no-ff`. Direto na `main` só release.

## Se você quiser montar o seu

A estrutura toda vive em `config/`, como dado. Clona o repo, troca o
`marcos.json` pelos seus concursos, ajusta `estrutura.py` e `agenda.py`, e roda o
setup no seu servidor. Não precisa mexer no código.
