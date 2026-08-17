"""Lista e remove membros do servidor.

Exige a intent privilegiada "Server Members" ligada no portal:
    discord.com/developers/applications > sua app > Bot >
    Privileged Gateway Intents > SERVER MEMBERS INTENT

Uso:
    python membros.py              # so lista, nao remove nada
    python membros.py --remover    # remove os nao-isentos, um a um, com log

Isentos SEMPRE (nunca removidos, mesmo com --remover):
  - o dono do servidor
  - o proprio bot
  - quem estiver em ISENTOS abaixo

Remover um membro nao apaga as mensagens dele e nao e banimento: ele pode
voltar com um convite novo. Ainda assim e acao sobre contas de pessoas
reais - por isso a listagem vem antes e o --remover e explicito.
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

# Nomes de usuario (sem #tag) que nunca saem, ALEM do dono e do bot, que ja
# sao isentos por codigo. A Giulia e a dona do servidor, entao ja esta coberta
# por ali.
ISENTOS: set[str] = {
    "lariszm",      # Larissa, entrou em 17/08/2026
}


class Membros(discord.Client):
    def __init__(self, remover: bool):
        intents = discord.Intents.default()
        intents.members = True          # privilegiada - precisa estar ligada no portal
        super().__init__(intents=intents)
        self.remover = remover

    async def on_ready(self):
        try:
            g = credenciais.resolver_guild(self, GUILD_ID)
            if g is None:
                return

            membros = [m async for m in g.fetch_members(limit=None)]
            print(f"\n{g.name} — {len(membros)} membro(s)\n")
            print(f"{'nome':<26} {'tipo':<7} {'entrou':<12} {'cargos'}")
            print("-" * 78)

            alvos = []
            for m in sorted(membros, key=lambda m: m.joined_at or m.created_at):
                tipo = "BOT" if m.bot else "pessoa"
                cargos = ", ".join(r.name for r in m.roles if not r.is_default()) or "—"
                entrou = m.joined_at.strftime("%d/%m/%Y") if m.joined_at else "?"

                motivo_isencao = None
                if m.id == g.owner_id:
                    motivo_isencao = "DONO"
                elif m.id == self.user.id:
                    motivo_isencao = "e o bot"
                elif m.name.lower() in ISENTOS:
                    motivo_isencao = "isento"

                marca = f"  << {motivo_isencao}" if motivo_isencao else ""
                print(f"{m.name:<26} {tipo:<7} {entrou:<12} {cargos}{marca}")

                if not motivo_isencao:
                    alvos.append(m)

            if not self.remover:
                print(f"\n{len(alvos)} seriam removidos. "
                      "Rode com --remover para aplicar.")
                return

            if not alvos:
                print("\nNinguem a remover.")
                return

            print(f"\nRemovendo {len(alvos)}...")
            for m in alvos:
                try:
                    await m.kick(reason="Reconversao do servidor para estudos")
                    print(f"  removido: {m.name}")
                except discord.Forbidden:
                    print(f"  SEM PERMISSAO: {m.name} "
                          "(cargo acima do bot, ou o bot nao tem Kick Members)")
                except discord.HTTPException as e:
                    print(f"  falhou: {m.name} — {e}")
        finally:
            await self.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--remover", action="store_true",
                    help="remove de fato (sem isto, so lista)")
    args = ap.parse_args()

    try:
        Membros(args.remover).run(TOKEN, log_handler=None)
    except discord.PrivilegedIntentsRequired:
        sys.exit(
            "\nFalta a intent privilegiada SERVER MEMBERS.\n"
            "  discord.com/developers/applications > sua app > Bot >\n"
            "  Privileged Gateway Intents > ligar SERVER MEMBERS INTENT > Save.\n"
            "  (E so um botao; nao exige verificacao com menos de 100 servidores.)\n"
        )
