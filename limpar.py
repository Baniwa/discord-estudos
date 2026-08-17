"""Apaga do servidor o que nao serve mais.

Apagar canal no Discord e DEFINITIVO: nao existe lixeira, nao existe restaurar.
Por isso o script separa em tres faixas e so age sozinho nas duas primeiras,
onde a perda e comprovadamente zero:

  1. VAZIO          canal com 0 mensagens, ou categoria sem nenhum canal
  2. SO BOT         todo o historico foi escrito por bot (log de entrada/saida,
                    avisos automaticos, comandos). Nenhuma frase de pessoa.
  3. TEM GENTE      alguem escreveu ali. NAO apaga sem --incluir-historico,
                    e mesmo assim lista antes.

Uso:
    python limpar.py                      # so classifica, nao apaga
    python limpar.py --apagar             # apaga faixa 1 e 2
    python limpar.py --apagar --incluir-historico NOME [NOME ...]
                                          # apaga tambem os nomeados da faixa 3
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

# Nunca entram na varredura, mesmo se estiverem vazios: sao a estrutura nova,
# que nasce vazia por definicao.
PROTEGIDOS_CATEGORIA = {
    "🔊 SALA DE ESTUDO", "🎯 COMANDO", "📚 CONHECIMENTO", "📋 LOGISTICA",
}

# Canal que a varredura classificaria como descartavel mas que ja foi decidido
# manter. O `rules` so tem uma mensagem de bot (JuniperBot, que saiu), entao
# cairia na faixa "so bot" - mas a decisao de manter IMPORTANTE de pe foi
# tomada pensando na hipotese de abrir o servidor para mais gente estudar.
PROTEGIDOS_CANAL = {
    "📕┇rules",
    "🤙🏽┇boas-vindas",
}

LIMITE_VARREDURA = 500


class Limpeza(discord.Client):
    def __init__(self, apagar: bool, incluir: list[str]):
        super().__init__(intents=discord.Intents.default())
        self.apagar = apagar
        self.incluir = set(incluir)

    async def on_ready(self):
        try:
            g = credenciais.resolver_guild(self, GUILD_ID)
            if g is None:
                return
            await self.executar(g)
        finally:
            await self.close()

    async def classificar(self, canal) -> tuple[str, str]:
        """Devolve (faixa, detalhe). Faixa: vazio | so_bot | tem_gente | manter."""
        if isinstance(canal, discord.VoiceChannel):
            return "manter", "canal de voz"

        if isinstance(canal, discord.ForumChannel):
            n = len(canal.threads)
            return ("vazio", "forum sem posts") if n == 0 else ("tem_gente", f"{n} post(s)")

        try:
            msgs = [m async for m in canal.history(limit=LIMITE_VARREDURA)]
        except discord.Forbidden:
            return "manter", "sem acesso de leitura"

        if not msgs:
            return "vazio", "0 mensagens"

        humanos = [m for m in msgs if not m.author.bot]
        if not humanos:
            autores = ", ".join(sorted({m.author.display_name for m in msgs}))
            return "so_bot", f"{len(msgs)} msg, todas de bot ({autores})"

        nomes = sorted({m.author.display_name for m in humanos})
        return "tem_gente", f"{len(humanos)} msg de gente ({', '.join(nomes[:3])})"

    async def executar(self, g: discord.Guild):
        vazios, so_bot, tem_gente = [], [], []

        for canal in g.channels:
            if isinstance(canal, discord.CategoryChannel):
                continue
            if canal.category and canal.category.name in PROTEGIDOS_CATEGORIA:
                continue
            if canal.name in PROTEGIDOS_CANAL:
                continue
            faixa, detalhe = await self.classificar(canal)
            if faixa == "vazio":
                vazios.append((canal, detalhe))
            elif faixa == "so_bot":
                so_bot.append((canal, detalhe))
            elif faixa == "tem_gente":
                tem_gente.append((canal, detalhe))

        cats_vazias = [c for c in g.categories
                       if c.name not in PROTEGIDOS_CATEGORIA and not c.channels]

        def bloco(titulo, itens):
            print(f"\n{titulo} ({len(itens)})")
            for c, d in itens:
                cat = c.category.name if c.category else "(sem categoria)"
                print(f"  {c.name:<26} {cat:<20} {d}")

        print(f"\n{g.name}")
        bloco("1. VAZIO — perda zero", vazios)
        bloco("2. SO BOT — nenhuma frase de pessoa", so_bot)
        bloco("3. TEM GENTE — nao apago sozinho", tem_gente)

        if cats_vazias:
            print(f"\nCATEGORIAS VAZIAS ({len(cats_vazias)})")
            for c in cats_vazias:
                print(f"  {c.name}")

        alvos = [c for c, _ in vazios] + [c for c, _ in so_bot]
        extras = [c for c, _ in tem_gente if c.name in self.incluir]
        nao_achados = self.incluir - {c.name for c, _ in tem_gente}

        if nao_achados:
            print(f"\nAVISO: nao encontrado na faixa 3: {', '.join(sorted(nao_achados))}")

        if not self.apagar:
            print(f"\n{len(alvos)} canais + {len(cats_vazias)} categorias seriam apagados.")
            if tem_gente:
                print("A faixa 3 fica intacta. Para incluir algum:")
                print("  python limpar.py --apagar --incluir-historico \"nome-do-canal\"")
            return

        print(f"\nApagando {len(alvos) + len(extras)} canais "
              f"e {len(cats_vazias)} categorias...")
        for c in alvos + extras:
            try:
                await c.delete(reason="limpar.py")
                print(f"  apagado: {c.name}")
            except discord.Forbidden:
                print(f"  SEM PERMISSAO: {c.name}")
            except discord.HTTPException as e:
                print(f"  falhou: {c.name} — {e}")

        for c in cats_vazias:
            try:
                await c.delete(reason="limpar.py")
                print(f"  apagada categoria: {c.name}")
            except discord.HTTPException as e:
                print(f"  falhou categoria: {c.name} — {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apagar", action="store_true",
                    help="apaga de fato (sem isto, so classifica)")
    ap.add_argument("--incluir-historico", nargs="*", default=[], metavar="NOME",
                    help="nomes da faixa 3 que voce autoriza apagar")
    args = ap.parse_args()

    Limpeza(args.apagar, args.incluir_historico).run(TOKEN, log_handler=None)
