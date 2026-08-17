"""Monta a estrutura do servidor de estudos no Discord.

Idempotente: cria so o que falta, nunca apaga nem duplica. Rodar de novo depois
de editar config/estrutura.py aplica so a diferenca.

Uso:
    python setup_servidor.py            # aplica
    python setup_servidor.py --dry-run  # so mostra o que faria
"""

import argparse
import asyncio
import os
import sys

import discord
from dotenv import load_dotenv

# O console do Windows abre em cp1252 e quebra ao imprimir o emoji dos nomes
# de canal. Sem isto o script morre com UnicodeEncodeError antes de criar nada.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.estrutura import CARGOS, ESTRUTURA, MENSAGEM_ALVO  # noqa: E402

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

criados: list[str] = []
existiam: list[str] = []


def log_novo(tipo: str, nome: str) -> None:
    criados.append(f"{tipo}: {nome}")
    print(f"  + {tipo:9} {nome}")


def log_existe(tipo: str, nome: str) -> None:
    existiam.append(f"{tipo}: {nome}")
    print(f"  = {tipo:9} {nome}  (ja existia)")


async def garantir_cargos(guild: discord.Guild, dry: bool) -> dict[str, discord.Role]:
    print("\nCARGOS")
    encontrados = {}
    for spec in CARGOS:
        role = discord.utils.get(guild.roles, name=spec["nome"])
        if role:
            log_existe("cargo", spec["nome"])
        elif dry:
            log_novo("cargo", spec["nome"])
            continue
        else:
            role = await guild.create_role(
                name=spec["nome"],
                colour=discord.Colour(spec["cor"]),
                hoist=spec["hoist"],
                reason="setup_servidor.py",
            )
            log_novo("cargo", spec["nome"])
        encontrados[spec["nome"]] = role
    return encontrados


def overwrites_leitura(guild: discord.Guild) -> dict:
    """@everyone le mas nao posta. Usado em #alvo e #editais-e-prazos."""
    return {
        guild.default_role: discord.PermissionOverwrite(
            send_messages=False,
            add_reactions=True,       # a confirmacao do bot e por reacao
            read_message_history=True,
            view_channel=True,
        ),
        guild.me: discord.PermissionOverwrite(send_messages=True, manage_messages=True),
    }


async def garantir_estrutura(guild: discord.Guild, dry: bool) -> None:
    for bloco in ESTRUTURA:
        nome_cat = bloco["categoria"]
        print(f"\n{nome_cat}")
        print(f"  ({bloco['proposito']})")

        categoria = discord.utils.get(guild.categories, name=nome_cat)
        if categoria:
            log_existe("categoria", nome_cat)
        elif dry:
            log_novo("categoria", nome_cat)
        else:
            categoria = await guild.create_category(nome_cat, reason="setup_servidor.py")
            log_novo("categoria", nome_cat)

        for canal in bloco["canais"]:
            await garantir_canal(guild, categoria, canal, dry)


async def garantir_canal(guild, categoria, spec: dict, dry: bool) -> None:
    tipo = spec["tipo"]
    nome = spec["nome"]

    # Discord normaliza nome de canal de texto/forum: minusculo, sem espaco.
    procurado = nome if tipo == "voz" else nome.lower().replace(" ", "-")
    existente = discord.utils.get(guild.channels, name=procurado)

    if existente:
        log_existe(tipo, nome)
        # Tag nova em forum ja existente e aplicada; nada e removido.
        if tipo == "forum" and not dry:
            await sincronizar_tags(existente, spec.get("tags", []))
        return

    if dry:
        log_novo(tipo, nome)
        return

    kwargs = {"category": categoria, "reason": "setup_servidor.py"}
    if spec.get("somente_leitura"):
        kwargs["overwrites"] = overwrites_leitura(guild)

    if tipo == "voz":
        await guild.create_voice_channel(nome, **kwargs)
    elif tipo == "texto":
        await guild.create_text_channel(nome, topic=spec.get("topico"), **kwargs)
    elif tipo == "forum":
        tags = [discord.ForumTag(name=t) for t in spec.get("tags", [])]
        await guild.create_forum(nome, topic=spec.get("topico"),
                                 available_tags=tags, **kwargs)
    else:
        raise ValueError(f"tipo de canal desconhecido: {tipo}")

    log_novo(tipo, nome)


async def sincronizar_tags(forum: discord.ForumChannel, desejadas: list[str]) -> None:
    """Adiciona tag que falta. Nunca remove - tag em uso carrega posts."""
    atuais = {t.name for t in forum.available_tags}
    faltando = [t for t in desejadas if t not in atuais]
    if not faltando:
        return
    novas = list(forum.available_tags) + [discord.ForumTag(name=t) for t in faltando]
    await forum.edit(available_tags=novas, reason="setup_servidor.py")
    for t in faltando:
        log_novo("tag", f"{forum.name} / {t}")


async def fixar_alvo(guild: discord.Guild, dry: bool) -> None:
    canal = discord.utils.get(guild.text_channels, name="alvo")
    if not canal or dry:
        return
    fixadas = await canal.pins()
    if fixadas:
        log_existe("fixada", "#alvo")
        return
    msg = await canal.send(MENSAGEM_ALVO)
    await msg.pin(reason="setup_servidor.py")
    log_novo("fixada", "#alvo")


async def main(dry: bool) -> None:
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        try:
            guild = client.get_guild(int(GUILD_ID))
            if guild is None:
                print(f"ERRO: o bot nao esta no servidor {GUILD_ID}. "
                      "Convide-o com permissao de Administrador primeiro.")
                return

            print(f"\nServidor: {guild.name}  ({guild.id})")
            if dry:
                print(">>> DRY-RUN: nada sera criado.\n")

            await garantir_cargos(guild, dry)
            await garantir_estrutura(guild, dry)
            await fixar_alvo(guild, dry)

            print("\n" + "-" * 52)
            print(f"criados: {len(criados)}   ja existiam: {len(existiam)}")
            if dry:
                print("Nada foi alterado (--dry-run).")
        finally:
            await client.close()

    await client.start(TOKEN)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="mostra o que seria criado, sem alterar nada")
    args = ap.parse_args()

    if not TOKEN or not GUILD_ID:
        sys.exit("Faltando DISCORD_BOT_TOKEN ou DISCORD_GUILD_ID no .env")

    asyncio.run(main(args.dry_run))
