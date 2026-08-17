"""Gera o link de convite do bot, com os escopos e permissoes certos.

Autentica so para descobrir a Application ID (para um bot, e o proprio user id),
monta a URL de autorizacao e sai. Nao altera nada.

Uso:
    python convite.py
"""

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

# Administrador. O setup cria categorias, canais, foruns, tags e cargos, e
# ajusta permissoes - montar a mascara exata daria na mesma e quebraria a cada
# canal novo. Servidor privado de duas pessoas: o custo disso e baixo.
PERMISSOES = discord.Permissions(administrator=True)


class Convite(discord.Client):
    async def on_ready(self):
        try:
            url = discord.utils.oauth_url(
                self.user.id,
                permissions=PERMISSOES,
                scopes=("bot", "applications.commands"),
            )
            ja_esta = self.get_guild(GUILD_ID) is not None

            print(f"\nBot autenticado: {self.user}  (application id {self.user.id})")
            print(f"Servidor alvo  : {GUILD_ID}")

            if GUILD_ID == self.user.id:
                print(
                    "\n>>> DISCORD_GUILD_ID esta com a APPLICATION ID do bot, "
                    "nao com o ID do servidor.\n"
                    "    O ID do servidor NAO vem do portal de desenvolvedores - "
                    "vem do proprio Discord:\n"
                    "      Configuracoes > Avancado > Modo desenvolvedor (ligar)\n"
                    "      botao direito no nome do servidor > Copiar ID do servidor\n"
                )
                print("Ainda assim, o convite abaixo e valido - autorize primeiro:\n")
                print(f"  {url}\n")
                return

            print(f"Ja esta la?    : {'SIM' if ja_esta else 'NAO'}")

            if ja_esta:
                g = self.get_guild(GUILD_ID)
                print(f"\nNada a fazer - o bot ja esta em '{g.name}'.")
                print("Pode rodar:  python setup_servidor.py --dry-run")
            else:
                print("\nAbra este link, escolha o servidor e autorize:\n")
                print(f"  {url}\n")
                print("Depois rode:  python convite.py   (para confirmar)")
        finally:
            await self.close()


if __name__ == "__main__":
    Convite(intents=discord.Intents.default()).run(TOKEN, log_handler=None)
