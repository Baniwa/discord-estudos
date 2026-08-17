# Servidor de estudos

Estrutura e bot de prazos do servidor onde eu e a Larissa estudamos para concurso.

O destino é **Auditor Fiscal de TI da SEFAZ-DF**. Os quatro concursos abaixo são
degraus até lá, nesta ordem:

| # | Concurso | Situação |
|---|---|---|
| 1 | **TCDF 2026**, Analista Adm. de Controle Externo | edital publicado, prova em 22/11/2026, CEBRASPE |
| 2 | **BB**, Agente de Tecnologia | sem edital |
| 3 | **ANPD**, Especialista em Regulação de Proteção de Dados | sem edital |
| 4 | **BACEN**, Técnico / Auditor / Procurador | sem edital |

## Por que os canais são por matéria

Porque categoria por concurso morre junto com o edital que não sai.

Eu já tinha um cronograma inteiro montado em cima do concurso da SEFAZ-DF, que
nunca foi publicado. Quando troquei o alvo para o TCDF, tive que resgatar à mão
uns 70% do conteúdo, que era o mesmo. Organizando por matéria isso não acontece:
os cinco alvos viram filtro sobre a mesma base, e concurso vira só logística.

A segunda decisão é que **voz vem antes de texto**. O que faz duas pessoas
estudarem juntas é estar na mesma sala em silêncio, não ter fórum bem organizado.
Por isso as salas de voz são o centro do servidor.

## Estrutura

```
🔊 SALA DE ESTUDO    Estudo Silencioso · Pomodoro 25-5 · Discussão · English Class
🎯 COMANDO           #alvo · #metas-do-dia · #diario · #erros-do-dia · #simulados
📚 CONHECIMENTO      #nucleo-ti · #auditoria-e-direito · #basicas · #duvidas (fóruns)
📋 LOGÍSTICA         #editais-e-prazos · #biblioteca · #marcos
👅 LINGUAGENS        javascript · html-e-css · python · bash · linux
☕ CYBER LOUNGE      bate-papo · memes · img
🗄️ ARQUIVO           o que saiu de cena, em somente leitura
```

`#erros-do-dia` é o canal mais importante. Todo item que eu errar entra ali e
vira card no Anki. Dia sem mensagem nele é dia que não aconteceu.

O servidor já existia desde fevereiro de 2023 com outra função, então o setup
reconverte em vez de criar do zero. As salas de voz antigas viraram as salas de
estudo por renomeação, e o `analise-de-sistemas` continuou onde estava porque já
era do tema. Nada foi apagado: o que saiu de cena foi para `🗄️ ARQUIVO`.

## Instalação

```bash
pip install -r requirements.txt
cp .env.example .env
```

No `.env` só o token é obrigatório:

* `DISCORD_BOT_TOKEN` fica em discord.com/developers/applications, aba **Bot**
  (não em General Information), botão Reset Token. Aparece uma vez só.
* `DISCORD_GUILD_ID` é opcional. Se o bot estiver em um servidor só, os scripts
  descobrem sozinhos.

Convide o bot pelo link que o `convite.py` gera. Ele precisa de Administrador.

## Comandos

```bash
python convite.py                    # gera o link de convite do bot
python diagnostico.py                # inventário do servidor, só leitura
python setup_servidor.py --dry-run   # mostra o que faria, sem tocar em nada
python setup_servidor.py             # aplica
python membros.py                    # lista membros
python sentinela.py                  # sobe o bot de prazos
```

`setup_servidor.py` é idempotente. Cria só o que falta, não duplica e não apaga.
Para mudar o servidor, edite `config/estrutura.py` e rode de novo.

Sempre rode o `--dry-run` antes. Ele mostra o que seria criado, o que seria
renomeado e o que iria para o arquivo.

## O bot de prazos

Posta em `#editais-e-prazos` às 7h, com escalada por urgência: verde acima de 15
dias, amarelo até 15, vermelho até 3 (ou até 7 se o marco for crítico).

Você marca ✅ na mensagem e ele para de cobrar. Sem a reação ele assume que não
foi feito e cobra de novo no dia seguinte. Dia sem nada a cobrar não gera post,
tirando segunda-feira, que traz o panorama da semana.

Comandos: `/prazos`, `/estudei` (streak do mínimo de 1h) e `/questoes`.

### A regra que importa mais que o resto

**Marco de fonte secundária não recebe contagem regressiva.**

Infográfico de Instagram, notícia e post de professor entram no `marcos.json`
com `"verificado": false`, e o bot só lembra de conferir a fonte primária. Ele
não conta dias em cima disso.

Isso está aqui porque eu já levei dois alarmes vermelhos que se revelaram falsos,
os dois vindos de fonte secundária. Contar dias para uma data que ninguém publicou
é fabricar urgência, e urgência fabricada estraga a confiança no bot inteiro.

Só entra com `"verificado": true` o que vier de edital em PDF, Diário Oficial,
site do órgão ou da banca.

## Arquivos

| Arquivo | O quê |
|---|---|
| `config/estrutura.py` | categorias, canais, fóruns, tags, o plano de reconversão e a mensagem fixada do `#alvo` |
| `config/marcos.json` | concursos e datas, marcando fonte primária ou secundária |
| `config/credenciais.py` | valida token e guild id, e diz qual campo do portal foi colado errado |
| `convite.py` | link de convite do bot |
| `diagnostico.py` | inventário do servidor, somente leitura |
| `setup_servidor.py` | cria e reconverte a estrutura |
| `membros.py` | lista e remove membros |
| `sentinela.py` | bot de prazos, streak e questões |
| `estado.json` | gerado em runtime, fora do git |

`.env` e `estado.json` estão no `.gitignore`.

## Branches

Gitflow. `main` é o que está rodando, `develop` é a integração, e cada mudança
nasce em `feature/<nome>` a partir de `develop`.

```bash
git checkout develop
git checkout -b feature/minha-mudanca
# trabalha, commita
git push -u origin feature/minha-mudanca
```

Merge para `develop` via PR, com `--no-ff` para o histórico não achatar.
Direto na `main` só release.

## Se você quiser montar o seu

A estrutura toda vive em `config/`, como dado. Clona o repo, troca o
`marcos.json` pelos seus concursos, ajusta o `estrutura.py` e roda o setup no
seu servidor. Não precisa mexer no código.
