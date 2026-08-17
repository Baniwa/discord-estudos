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
from config import credenciais  # noqa: E402
from config.estrutura import (  # noqa: E402
    ARQUIVAR, CARGOS, CATEGORIA_ARQUIVO, CATEGORIAS_OBSOLETAS,
    ESTRUTURA, MENSAGEM_ALVO, REAPROVEITAR,
)

load_dotenv()

criados: list[str] = []
existiam: list[str] = []

# Em dry-run as categorias novas nao chegam a existir, entao um "mover para
# categoria X" ficaria invisivel e o relatorio mentiria por omissao. Este
# conjunto guarda as que existem OU que seriam criadas nesta passada.
categorias_previstas: set[str] = set()


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

        categorias_previstas.add(nome_cat)
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


async def reaproveitar(guild: discord.Guild, dry: bool) -> None:
    """Renomeia e remaneja o que ja existia, em vez de criar duplicata."""
    print("\nREAPROVEITAR (o que ja existia muda de funcao)")
    for spec in REAPROVEITAR:
        canal = discord.utils.get(guild.channels, name=spec["de"])
        if canal is None:
            print(f"  ? nao encontrado: {spec['de']}  (ja renomeado?)")
            continue

        novo_nome = spec["para"]
        destino = None
        if spec["categoria"]:
            destino = discord.utils.get(guild.categories, name=spec["categoria"])

        mudancas = []
        if novo_nome and canal.name != novo_nome:
            mudancas.append(f"nome -> {novo_nome}")
        if destino and canal.category_id != destino.id:
            mudancas.append(f"categoria -> {spec['categoria']}")
        elif destino is None and spec["categoria"] in categorias_previstas:
            # dry-run: a categoria ainda nao existe, mas seria criada agora
            mudancas.append(f"categoria -> {spec['categoria']}")

        if not mudancas:
            log_existe("ok", spec["de"])
            continue

        print(f"  ~ {spec['de']:<26} {' · '.join(mudancas)}")
        print(f"      ({spec['motivo']})")
        if not dry:
            kwargs = {"reason": "setup_servidor.py — reconversao"}
            if novo_nome:
                kwargs["name"] = novo_nome
            if destino:
                kwargs["category"] = destino
            await canal.edit(**kwargs)
        criados.append(f"reaproveitado: {spec['de']}")


async def arquivar(guild: discord.Guild, dry: bool) -> None:
    """Move para a categoria de arquivo. Nada e apagado."""
    print(f"\nARQUIVAR (move para {CATEGORIA_ARQUIVO}, nao apaga)")
    destino = discord.utils.get(guild.categories, name=CATEGORIA_ARQUIVO)

    if destino is None:
        if dry:
            log_novo("categoria", CATEGORIA_ARQUIVO)
        else:
            overwrites = {guild.default_role: discord.PermissionOverwrite(
                send_messages=False, read_message_history=True)}
            destino = await guild.create_category(
                CATEGORIA_ARQUIVO, overwrites=overwrites, position=99,
                reason="setup_servidor.py")
            log_novo("categoria", CATEGORIA_ARQUIVO)

    for spec in ARQUIVAR:
        canal = discord.utils.get(guild.channels, name=spec["canal"])
        if canal is None:
            print(f"  ? nao encontrado: {spec['canal']}")
            continue
        if destino and canal.category_id == destino.id:
            log_existe("arquivado", spec["canal"])
            continue
        print(f"  → {spec['canal']:<26} ({spec['motivo']})")
        if not dry and destino:
            await canal.edit(category=destino, reason="setup_servidor.py — arquivo")
        criados.append(f"arquivado: {spec['canal']}")


def categorias_vazias(guild: discord.Guild) -> None:
    """So relata. Apagar categoria e decisao dela, nao do script."""
    sobrando = [c for c in guild.categories
                if c.name in CATEGORIAS_OBSOLETAS and not c.channels]
    if sobrando:
        print("\nCATEGORIAS VAZIAS (o script nao apaga - apagar a mao se quiser)")
        for c in sobrando:
            print(f"  · {c.name}")


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
            guild = credenciais.resolver_guild(client, GUILD_ID)
            if guild is None:
                return

            print(f"\nServidor: {guild.name}  ({guild.id})")
            if dry:
                print(">>> DRY-RUN: nada sera criado.\n")

            await garantir_cargos(guild, dry)
            await garantir_estrutura(guild, dry)
            await reaproveitar(guild, dry)
            await arquivar(guild, dry)
            categorias_vazias(guild)
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

    TOKEN, GUILD_ID = credenciais.carregar()
    asyncio.run(main(args.dry_run))
