"""Validacao das credenciais antes de qualquer chamada ao Discord.

Existe por um motivo concreto: a tela inicial do portal de desenvolvedores mostra
a APPLICATION ID, a PUBLIC KEY e o CLIENT SECRET - e nenhum dos tres e o token do
bot, que fica na aba "Bot". Colar o valor errado produz um `401 Unauthorized` sem
explicacao. Melhor dizer qual campo foi colado e onde esta o certo.
"""

import os
import re
import sys

# Token de bot: <base64 do app id>.<timestamp>.<hmac> - 3 partes, 2 pontos.
RE_TOKEN = re.compile(r"^[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{20,}$")


def _diagnosticar(v: str) -> str:
    """Adivinha qual campo do portal foi colado, pelo formato."""
    if re.fullmatch(r"[0-9a-fA-F]{64}", v):
        return ("isso e a PUBLIC KEY (64 caracteres hexadecimais), da aba "
                "'General Information'. Ela e publica e nao serve para autenticar.")
    if re.fullmatch(r"\d{17,20}", v):
        return ("isso e a APPLICATION ID (so digitos), da aba "
                "'General Information'.")
    if re.fullmatch(r"[A-Za-z0-9_-]{32}", v):
        return ("isso parece o CLIENT SECRET (32 caracteres), da aba OAuth2. "
                "Ele serve para OAuth, nao para o bot.")
    if v.startswith("Bot "):
        return "tire o prefixo 'Bot ' - a biblioteca ja adiciona sozinha."
    return f"formato nao reconhecido ({len(v)} caracteres, {v.count('.')} ponto(s))."


def carregar() -> tuple[str, int]:
    """Devolve (token, guild_id) ou encerra com uma mensagem util."""
    token = (os.getenv("DISCORD_BOT_TOKEN") or "").strip()
    guild = (os.getenv("DISCORD_GUILD_ID") or "").strip()

    if not token:
        sys.exit("DISCORD_BOT_TOKEN vazio no .env.")

    if not RE_TOKEN.fullmatch(token):
        sys.exit(
            "\nO valor em DISCORD_BOT_TOKEN nao tem formato de token de bot.\n"
            f"  Diagnostico: {_diagnosticar(token)}\n\n"
            "  Um token de bot tem TRES partes separadas por dois pontos,\n"
            "  algo como  MTIzNDU2Nzg5.GaBcDe.xxxxxxxxxxxxxxxxxxxxxxxxxxx\n\n"
            "  Onde pegar: discord.com/developers/applications > sua aplicacao\n"
            "  > menu da ESQUERDA > 'Bot' > Reset Token > Copy.\n"
            "  (Nao e a aba 'General Information'.) Ele aparece uma vez so.\n"
        )

    # Guild id e OPCIONAL: se o bot estiver em um servidor so, resolver_guild()
    # descobre sozinho. Exigir o campo so criava uma chance a mais de colar o
    # valor errado - foi o que aconteceu duas vezes.
    return token, int(guild) if guild.isdigit() else 0


def resolver_guild(client, configurado: int):
    """Devolve o Guild alvo, ou None com uma explicacao impressa.

    Ordem: usa o configurado se fizer sentido; senao, se o bot estiver em
    exatamente um servidor, usa esse.
    """
    if configurado and configurado != client.user.id:
        g = client.get_guild(configurado)
        if g:
            return g
        print(f"\nO bot nao esta no servidor {configurado}.")
        print("  Rode  python convite.py  para gerar o link de autorizacao.")
        return None

    if configurado == client.user.id:
        print("\nAviso: DISCORD_GUILD_ID esta com a APPLICATION ID do bot, "
              "nao com o ID do servidor.")

    if len(client.guilds) == 1:
        g = client.guilds[0]
        print(f"Resolvido automaticamente: '{g.name}' ({g.id}).")
        print(f"Para fixar, ponha no .env:  DISCORD_GUILD_ID={g.id}\n")
        return g

    if not client.guilds:
        print("\nO bot nao esta em nenhum servidor. Rode  python convite.py")
        return None

    print("\nO bot esta em mais de um servidor. Escolha um e ponha no .env:")
    for g in client.guilds:
        print(f"  DISCORD_GUILD_ID={g.id}   # {g.name}")
    return None
