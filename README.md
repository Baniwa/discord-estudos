# Servidor de estudos — trilha SEFAZ Auditor de TI

Infraestrutura de um servidor Discord de estudo para duas pessoas (Giulia e Larissa),
com bot de prazos de edital.

O destino da trilha é **Auditor Fiscal de TI da SEFAZ-DF**. Os quatro concursos
abaixo são degraus, nesta ordem:

| # | Concurso | Situação |
|---|---|---|
| 1 | **TCDF 2026** — Analista Adm. de Controle Externo | edital publicado · prova **22/11/2026** · CEBRASPE |
| 2 | **BB** — Agente de Tecnologia | sem edital |
| 3 | **ANPD** — Especialista em Regulação de Proteção de Dados | sem edital |
| 4 | **BACEN** — Técnico / Auditor / Procurador | sem edital |

## A decisão que organiza tudo

**Canais por matéria, nunca por concurso.**

Categoria por concurso morre quando o edital não sai, e leva o conhecimento junto —
foi exatamente o que aconteceu com um cronograma anterior montado em torno de um
edital da SEFAZ-DF que nunca foi publicado. Por matéria, os cinco alvos viram
filtros sobre a mesma base, e concurso vira só logística.

A segunda decisão: **voz é o produto, texto é o arquivo.** O que faz duas pessoas
estudarem juntas é estar na mesma sala em silêncio, não ter fórum bem organizado.

## Estrutura

```
🔊 SALA DE ESTUDO     🔇 Estudo Silencioso · 🍅 Pomodoro 25-5 · 🗣️ Discussão
🎯 COMANDO            #alvo · #metas-do-dia · #diario · #erros-do-dia · #simulados
📚 CONHECIMENTO       #nucleo-ti · #auditoria-e-direito · #basicas · #duvidas   (fóruns com tags)
📋 LOGÍSTICA          #editais-e-prazos · #biblioteca · #marcos
```

`#erros-do-dia` é o canal mais importante: todo item errado entra ali e vira card
no Anki. Dia sem mensagem nele é dia que não aconteceu.

## Instalação

```bash
pip install -r requirements.txt
cp .env.example .env
```

Preencher o `.env`:

- **`DISCORD_BOT_TOKEN`** — `discord.com/developers/applications` › New Application ›
  Bot › Reset Token. Aparece uma vez só.
- **`DISCORD_GUILD_ID`** — no Discord, ligar Configurações › Avançado › Modo
  desenvolvedor, depois botão direito no servidor › Copiar ID.

Convidar o bot no servidor com permissão de **Administrador** (OAuth2 › URL
Generator › escopos `bot` + `applications.commands`).

## Uso

```bash
python setup_servidor.py --dry-run   # mostra o que seria criado, sem tocar em nada
python setup_servidor.py             # cria categorias, canais, fóruns, tags e cargos
python sentinela.py                  # sobe o bot de prazos
```

`setup_servidor.py` é **idempotente**: cria só o que falta, nunca apaga nem duplica.
Para mudar o servidor, edite `config/estrutura.py` e rode de novo.

## O bot

Posta em `#editais-e-prazos` às **07h (BRT)**, com escalada por urgência
(🟢 acima de 15 dias · 🟡 até 15 · 🔴 até 3, ou até 7 se o marco for crítico).

**Confirmação por reação:** você marca ✅ e ele para de cobrar. Sem reação, ele
assume que não foi feito e cobra de novo no dia seguinte.

Dia sem nada a cobrar não gera post — exceto segunda-feira, para o panorama semanal.

Comandos: `/prazos` · `/estudei` (streak do mínimo de 1h) · `/questoes`.

### A regra que vale mais que o resto

Marco de **fonte secundária não recebe contagem regressiva.** Infográfico de
Instagram, notícia e post de professor entram em `config/marcos.json` com
`"verificado": false` e o bot só lembra de conferir a fonte primária — não conta
dias em cima deles.

Isso existe porque dois alarmes 🔴 anteriores se revelaram falsos por virem de
fonte secundária. Contar dias para uma data que ninguém publicou é fabricar
urgência, e urgência fabricada destrói a confiança no bot inteiro.

Só entra com `"verificado": true` o que vier de edital em PDF, Diário Oficial,
site do órgão ou da banca.

## Arquivos

| Arquivo | O quê |
|---|---|
| `config/estrutura.py` | categorias, canais, fóruns, tags, cargos e a mensagem fixada de `#alvo` |
| `config/marcos.json` | concursos e datas, com marcação de fonte primária/secundária |
| `setup_servidor.py` | cria a estrutura no Discord |
| `sentinela.py` | bot de prazos, streak e questões |
| `estado.json` | gerado em runtime — confirmações e streak (fora do git) |

`.env` e `estado.json` estão no `.gitignore`.
