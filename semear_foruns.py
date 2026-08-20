"""Fecha a configuração dos fóruns: reação padrão e post inicial.

Os dois itens que sobram no checklist do Discord existem por um motivo real,
não são enfeite:

  - A reação padrão vira o gesto de um clique que todo post recebe. Se ela não
    significar nada, ninguém usa. Aqui ela significa uma coisa só, e diferente
    por fórum.
  - O primeiro post de um fórum define o formato de todos os outros. Se o
    primeiro for bagunçado, o resto segue.

Idempotente: não recria post que já existe.

Uso:
    python semear_foruns.py --dry-run
    python semear_foruns.py
"""

import argparse
import sys
from pathlib import Path

import discord
from dotenv import load_dotenv

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ))

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config import credenciais  # noqa: E402

TOKEN, GUILD_ID = credenciais.carregar()


FORUNS = {
    "nucleo-ti": {
        # 📗 é o mesmo emoji que o bot usa quando um erro vira card. Manter o
        # mesmo símbolo nos dois lugares evita ter que lembrar de dois códigos.
        "reacao": "📗",
        "reacao_significa": "virou card no Anki",
        "post": {
            "titulo": "Como usar este fórum",
            "tag": "eng-software",
            "corpo": """\
**Um post por tema, nunca por dia.**

O título é o conceito: `Normalização: 3FN e quando quebrar de propósito`.
Não é `Estudo de 17/08`. Data não se procura depois, conceito sim.

**Quando o assunto voltar, volte no post e edite.** Não abra outro. O post
cresce e vira a página daquele conceito, do mesmo jeito que a nota do Obsidian
se reescreve em vez de virar pilha cronológica.

**A tag é a matéria.** Uma só, a principal.

**📗 significa que aquilo já virou card no Anki.** É o mesmo emoji que o bot
usa em `#erros-do-dia`. Post sem 📗 é conhecimento que ainda não está na
revisão espaçada, ou seja, conhecimento que você vai perder.

**O que não entra aqui:** resumo de PDF e transcrição de aula. Isso é trabalho
que ninguém relê. Resumo vira card. Fórum é para o que você concluiu e para o
que te confundiu.

Este fórum é o que paga nos cinco alvos ao mesmo tempo. Segurança da Informação
e LGPD são as matérias de maior retorno de toda a trilha.""",
        },
    },
    "auditoria-e-direito": {
        "reacao": "📗",
        "reacao_significa": "virou card no Anki",
        "post": {
            "titulo": "Como usar este fórum",
            "tag": "auditoria-sistemas",
            "corpo": """\
**Mesma regra do `#nucleo-ti`: um post por tema, título é o conceito, edite em
vez de abrir outro.**

Duas coisas específicas daqui:

**1. Lei seca antes de resumo de terceiro.** A banca cobra a redação do
dispositivo. Uma palavra trocada muda o gabarito. Quando citar, cole o artigo
e marque a fonte.

**2. Auditoria de sistemas é o único vermelho de TI das duas.** E é justamente
o que separa dev que sabe TI de auditor de TI, que é o destino da trilha.
Este fórum merece mais post que todos os outros juntos.

Peso na prova do TCDF: Direito Administrativo e AFO valem 70 dos pontos, quase
metade da objetiva, e as duas começam do zero. É por aqui que a prova é
decidida.""",
        },
    },
    "basicas": {
        "reacao": "📗",
        "reacao_significa": "virou card no Anki",
        "post": {
            "titulo": "Como usar este fórum",
            "tag": "portugues",
            "corpo": """\
**Português é diário e não espera novembro.** 20 minutos todo dia: 1 texto
CEBRASPE e 5 itens de gramática.

O que vale postar aqui é **padrão de erro**, não regra de gramática. Regra
está no livro. O que o livro não tem é a lista do que *você* erra sempre.

Padrões já mapeados na EMBRATUR, que a banca lê como falha de estrutura
textual: frase sem verbo principal, `onde` usado como conectivo genérico, e
período inteiro em gerúndio.

**Inglês e conhecimentos bancários** valem 17,5% da prova do BB e nada nos
outros alvos. Prioridade baixa até o edital sair, mas o fórum fica de pé para
quando sair.""",
        },
    },
    "duvidas": {
        # Aqui ✅ não é "curti", é "está resolvida". Gesto de um clique que
        # muda o estado da dúvida.
        "reacao": "✅",
        "reacao_significa": "resolvida",
        "post": {
            "titulo": "Como usar este fórum",
            "tag": "aberta",
            "corpo": """\
**Abra a dúvida com a tag `aberta`. Quando fechar, troque para `resolvida` e
reaja com ✅.**

Dúvida aberta é fila. Dúvida resolvida é material de revisão. Sem essa troca,
o fórum vira só uma lista de coisas que ninguém sabe.

**Escreva o que você já tentou.** "Não entendi convalidação" não dá para
responder. "Entendi que convalida vício de competência, mas não sei se vale
quando a competência é exclusiva" dá.

**Por que este fórum tende a funcionar:** os perfis aqui são
complementares, e engenharia de software fica coberta pelos dois lados.

E o mais importante: **redes, infraestrutura e auditoria de sistemas são
vermelho de todo mundo.** Ninguém tem vantagem ali, e é onde estudar em par
rende mais.""",
        },
    },
}


class Semeador(discord.Client):
    def __init__(self, dry: bool):
        super().__init__(intents=discord.Intents.default())
        self.dry = dry

    async def on_ready(self):
        try:
            g = credenciais.resolver_guild(self, GUILD_ID)
            if g is None:
                return
            if self.dry:
                print(">>> DRY-RUN: nada será alterado.\n")

            for nome, spec in FORUNS.items():
                forum = discord.utils.get(g.forums, name=nome)
                if forum is None:
                    print(f"  ? fórum não encontrado: {nome}")
                    continue
                print(f"\n#{nome}")
                await self.reacao(forum, spec)
                await self.primeiro_post(forum, spec)
        finally:
            await self.close()

    async def reacao(self, forum: discord.ForumChannel, spec: dict):
        atual = forum.default_reaction_emoji
        alvo = spec["reacao"]
        if atual and str(atual) == alvo:
            print(f"  = reação padrão já é {alvo}")
            return
        print(f"  + reação padrão {alvo}  ({spec['reacao_significa']})")
        if not self.dry:
            await forum.edit(default_reaction_emoji=alvo,
                             reason="semear_foruns.py")

    async def primeiro_post(self, forum: discord.ForumChannel, spec: dict):
        p = spec["post"]
        existente = discord.utils.get(forum.threads, name=p["titulo"])
        if existente:
            print(f"  = post inicial já existe: {p['titulo']}")
            return

        print(f"  + post inicial: {p['titulo']}  [tag {p['tag']}]")
        if self.dry:
            return

        tag = discord.utils.get(forum.available_tags, name=p["tag"])
        thread = await forum.create_thread(
            name=p["titulo"], content=p["corpo"],
            applied_tags=[tag] if tag else [],
            reason="semear_foruns.py")
        # Fixar deixa o post no topo, que é onde uma convenção precisa ficar.
        try:
            await thread.thread.edit(pinned=True)
        except discord.HTTPException as e:
            print(f"    (não consegui fixar: {e})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    Semeador(args.dry_run).run(TOKEN, log_handler=None)
