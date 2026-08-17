"""Publica no servidor o conteúdo que não muda: regras e calendário.

Idempotente por edição: se a mensagem do bot já existe no canal, ela é
EDITADA em vez de reenviada. Reenviar empurraria a versão antiga para cima e
o canal viraria histórico de versões de regra, que ninguém lê.

Uso:
    python publicar.py --dry-run
    python publicar.py
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import discord
from dotenv import load_dotenv

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ))

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config import credenciais  # noqa: E402
from config.agenda import MINIMO, ROTINA, SEMANAS  # noqa: E402

TOKEN, GUILD_ID = credenciais.carregar()

CANAL_REGRAS = "📕┇rules"
CANAL_CALENDARIO = "calendario"
CATEGORIA_COMANDO = "🎯 COMANDO"


REGRAS = """\
# Como este servidor funciona

Isto aqui não é servidor de comunidade. É sala de estudo de duas pessoas com
uma prova marcada para **22 de novembro de 2026**.

## As regras

**1. `#erros-do-dia` é obrigatório.**
Todo item errado entra ali, no dia. Um erro por mensagem. Dia sem mensagem
nesse canal é dia que não aconteceu, mesmo que você tenha lido o PDF inteiro.

**2. Entrar em 🔇 Estudo Silencioso é o registro de ponto.**
Mic e câmera desligados. Ninguém fala. A presença da outra é o mecanismo, não
a conversa. O bot cronometra sozinho, não precisa avisar nada.

**3. Reduzir vale, pular não.**
O mínimo em dia ruim é 1 hora: 30 min de conteúdo e 10 questões. Abaixo disso
o dia não conta para o streak.

**4. Fórum é por tema, nunca por dia.**
Título é o conceito, não a data. Quando o assunto voltar, edite o post que já
existe em vez de abrir outro. Resumo de PDF e transcrição de aula não entram:
isso vira card no Anki.

**5. Em `#editais-e-prazos` só entra fonte primária.**
Edital em PDF, Diário Oficial, site do órgão ou da banca. Infográfico de
Instagram, notícia e post de professor não valem, e não geram contagem
regressiva. Já houve dois alarmes falsos por causa disso.

**6. Não crie canal novo.**
A estrutura é por matéria justamente para não crescer. Assunto novo é uma tag
ou um post dentro de um fórum que já existe.

## O destino

**Auditor Fiscal de TI da SEFAZ-DF.** Os quatro concursos abaixo são degraus,
nesta ordem: **TCDF** (22/11/2026) · **BB** · **ANPD** · **BACEN**.

Até novembro o foco é o TCDF, sozinho. Os outros três se beneficiam do que for
estudado aqui e não viram frente paralela.

## O bot

`/erro` lança erro e já vira card do Anki · `/questoes` registra questões ·
`/estudei` marca o mínimo do dia · `/relatorio` fecha o período ·
`/prazos` mostra os editais · `/agora` diz quem está em call · `/anki` mostra
a fila de cards.

Ele cobra prazo de edital às 7h e fecha o relatório da semana no domingo às 20h.
"""


def montar_calendario() -> str:
    linhas = ["# Calendário de estudo", "",
              "Tirado do plano de 100 dias, montado com o edital lido na íntegra.",
              "", "## A semana", ""]
    for r in ROTINA:
        linhas.append(f"**{r['dias']} — {r['hora']}** *({r['dur']})*")
        linhas.append(f"　{r['estrutura']}")
        linhas.append("")
    linhas += [f"> {MINIMO}", "", "## As semanas até a prova", ""]

    hoje = date.today()
    fase_atual = None
    for inicio, fim, rotulo, _ in SEMANAS:
        if inicio <= hoje <= fim:
            fase_atual = rotulo
        marca = "▶" if inicio <= hoje <= fim else ("✓" if fim < hoje else "　")
        linhas.append(f"{marca} `{inicio:%d/%m}–{fim:%d/%m}`  **{rotulo}**")

    linhas += ["", f"*Semana atual: {fase_atual or 'fora do plano'}. "
                   f"Faltam {(date(2026, 11, 22) - hoje).days} dias para a prova.*",
               "", "O conteúdo detalhado de cada semana sai no aviso diário das "
                   "17h45, 15 minutos antes do bloco."]
    return "\n".join(linhas)


async def publicar(canal: discord.TextChannel, texto: str, me, dry: bool):
    """Edita a mensagem que o bot já postou, ou posta a primeira vez."""
    anterior = None
    async for m in canal.history(limit=50):
        if m.author.id == me.id:
            anterior = m
            break

    if anterior:
        if anterior.content.strip() == texto.strip():
            print(f"  = #{canal.name}: sem mudança")
            return
        print(f"  ~ #{canal.name}: editando a mensagem existente")
        if not dry:
            await anterior.edit(content=texto)
        return

    print(f"  + #{canal.name}: primeira publicação")
    if not dry:
        msg = await canal.send(texto)
        try:
            await msg.pin(reason="publicar.py")
        except discord.HTTPException as e:
            print(f"    (não consegui fixar: {e})")


class Publicador(discord.Client):
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

            regras = discord.utils.get(g.text_channels, name=CANAL_REGRAS)
            if regras:
                await publicar(regras, REGRAS, self.user, self.dry)
            else:
                print(f"  ? canal {CANAL_REGRAS} não encontrado")

            cal = discord.utils.get(g.text_channels, name=CANAL_CALENDARIO)
            if cal is None:
                cat = discord.utils.get(g.categories, name=CATEGORIA_COMANDO)
                print(f"  + criando #{CANAL_CALENDARIO} em {CATEGORIA_COMANDO}")
                if not self.dry:
                    cal = await g.create_text_channel(
                        CANAL_CALENDARIO, category=cat,
                        topic="Calendário do plano de 100 dias. Só o bot posta.",
                        overwrites={g.default_role: discord.PermissionOverwrite(
                            send_messages=False, view_channel=True,
                            read_message_history=True)},
                        reason="publicar.py")
            if cal:
                await publicar(cal, montar_calendario(), self.user, self.dry)
        finally:
            await self.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    Publicador(args.dry_run).run(TOKEN, log_handler=None)
