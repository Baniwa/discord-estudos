"""Inventario do servidor. SOMENTE LEITURA - nao cria, nao edita, nao apaga.

Serve para decidir o que fazer antes de rodar o setup: o que ja existe, o que
tem historico que vale preservar e o que esta morto e pode ser reaproveitado.

Nao usa a intent privilegiada de message_content: le so metadado (quantas
mensagens, quando foi a ultima, quem escreveu), nunca o texto. Para decidir
"vivo ou morto" isso basta, e evita pedir permissao privilegiada por um
diagnostico.

Uso:
    python diagnostico.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import discord
from dotenv import load_dotenv

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ))

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config import credenciais  # noqa: E402
from config.estrutura import ESTRUTURA  # noqa: E402

TOKEN, GUILD_ID = credenciais.carregar()

ICONE = {
    discord.ChannelType.text: "#",
    discord.ChannelType.voice: "🔊",
    discord.ChannelType.forum: "📋",
    discord.ChannelType.stage_voice: "🎙",
    discord.ChannelType.news: "📢",
}


def idade(dt: datetime | None) -> str:
    if dt is None:
        return "vazio"
    dias = (datetime.now(timezone.utc) - dt).days
    if dias == 0:
        return "hoje"
    if dias == 1:
        return "ontem"
    if dias < 30:
        return f"ha {dias}d"
    return f"ha {dias // 30}m"


class Diagnostico(discord.Client):
    async def on_ready(self):
        try:
            g = self.get_guild(GUILD_ID)
            if g is None:
                if GUILD_ID == self.user.id:
                    print("\nERRO: DISCORD_GUILD_ID esta com a APPLICATION ID do bot.")
                else:
                    print(f"\nERRO: o bot nao esta no servidor {GUILD_ID}. "
                          "Rode  python convite.py")
                return

            await self.panorama(g)
            await self.canais(g)
            self.cargos(g)
            await self.confronto(g)
        finally:
            await self.close()

    async def panorama(self, g: discord.Guild):
        print("=" * 60)
        print(f"SERVIDOR: {g.name}")
        print("=" * 60)
        print(f"  criado em : {g.created_at:%d/%m/%Y}")
        print(f"  membros   : {g.member_count}")
        print(f"  dono      : {g.owner}")
        print(f"  canais    : {len(g.text_channels)} texto · "
              f"{len(g.voice_channels)} voz · {len(g.forums)} forum")
        print(f"  categorias: {len(g.categories)}")

    async def canais(self, g: discord.Guild):
        print("\n" + "=" * 60)
        print("ESTRUTURA ATUAL")
        print("=" * 60)

        grupos: list[tuple[str, list]] = []
        soltos = [c for c in g.channels
                  if c.category is None and not isinstance(c, discord.CategoryChannel)]
        if soltos:
            grupos.append(("(sem categoria)", soltos))
        for cat in sorted(g.categories, key=lambda c: c.position):
            grupos.append((cat.name, cat.channels))

        for nome, canais in grupos:
            print(f"\n  {nome}")
            for c in canais:
                ic = ICONE.get(c.type, "?")
                extra = await self.atividade(c)
                print(f"    {ic} {c.name:<28} {extra}")

    async def atividade(self, canal) -> str:
        """Ultima atividade, so por metadado."""
        if isinstance(canal, discord.VoiceChannel):
            return f"({len(canal.members)} conectado(s))"
        if isinstance(canal, discord.ForumChannel):
            n = len(canal.threads)
            tags = ", ".join(t.name for t in canal.available_tags) or "sem tags"
            return f"({n} post(s) · {tags})"
        if isinstance(canal, discord.TextChannel):
            try:
                ultima = [m async for m in canal.history(limit=1)]
            except discord.Forbidden:
                return "(sem acesso a leitura)"
            if not ultima:
                return "(VAZIO)"
            m = ultima[0]
            return f"(ultima: {idade(m.created_at)}, por {m.author.display_name})"
        return ""

    def cargos(self, g: discord.Guild):
        print("\n" + "=" * 60)
        print("CARGOS")
        print("=" * 60)
        for r in sorted(g.roles, key=lambda r: -r.position):
            if r.is_default():
                continue
            marca = "ADMIN" if r.permissions.administrator else ""
            print(f"  {r.name:<24} {len(r.members)} membro(s)  {marca}")

    async def confronto(self, g: discord.Guild):
        """O que o setup criaria x o que ja existe."""
        print("\n" + "=" * 60)
        print("O QUE O setup_servidor.py FARIA")
        print("=" * 60)

        nomes = {c.name for c in g.channels}
        novos, reaproveitados = [], []

        for bloco in ESTRUTURA:
            cat_existe = discord.utils.get(g.categories, name=bloco["categoria"])
            for canal in bloco["canais"]:
                alvo = (canal["nome"] if canal["tipo"] == "voz"
                        else canal["nome"].lower().replace(" ", "-"))
                (reaproveitados if alvo in nomes else novos).append(
                    f"{bloco['categoria']} / {canal['nome']}")
            if not cat_existe:
                novos.append(f"[categoria] {bloco['categoria']}")

        print(f"\n  CRIARIA ({len(novos)}):")
        for n in novos:
            print(f"    + {n}")

        if reaproveitados:
            print(f"\n  JA EXISTE, seria mantido ({len(reaproveitados)}):")
            for n in reaproveitados:
                print(f"    = {n}")

        orfaos = [c.name for c in g.channels
                  if not isinstance(c, discord.CategoryChannel)
                  and c.name not in {
                      (x["nome"] if x["tipo"] == "voz"
                       else x["nome"].lower().replace(" ", "-"))
                      for b in ESTRUTURA for x in b["canais"]}]
        if orfaos:
            print(f"\n  FORA DO PLANO, ficaria intacto ({len(orfaos)}):")
            print(f"    {', '.join(orfaos)}")
            print("\n  (o setup nunca apaga nada - decidir a mao o que fazer com esses)")


if __name__ == "__main__":
    Diagnostico(intents=discord.Intents.default()).run(TOKEN, log_handler=None)
