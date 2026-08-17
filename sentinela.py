"""Sentinela — bot do servidor de estudos.

Faz quatro coisas:

  1. Cobra prazo de edital, com escalada e confirmacao por reacao.
  2. Cronometra sozinho o tempo em call na SALA DE ESTUDO. Isto e o que
     sustenta os relatorios: dado que ninguem precisa lembrar de digitar.
  3. Conta os erros lancados em #erros-do-dia.
  4. Fecha relatorio semanal e sob demanda.

O ponto de desenho: o unico numero em que da para confiar e o que o bot mede
sozinho. Relatorio feito so de auto-declaracao mede disciplina de preencher
formulario, nao estudo.

Uso:
    python sentinela.py
"""

import json
import os
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ))

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import db  # noqa: E402
from config.agenda import MINIMO, bloco_do_dia  # noqa: E402

CONFIG = json.loads((RAIZ / "config" / "marcos.json").read_text(encoding="utf-8"))
TZ = ZoneInfo(CONFIG["timezone"])

CANAL_PRAZOS = os.getenv("CANAL_PRAZOS", "editais-e-prazos")
CANAL_ERROS = "erros-do-dia"
CATEGORIA_ESTUDO = "🔊 SALA DE ESTUDO"
CARGO_ALVO = "⚔️ Maidens"

CANAL_BOAS_VINDAS = "🤙🏽┇boas-vindas"
CANAL_METAS = "metas-do-dia"

HORA_BRIEFING = time(hour=7, minute=0, tzinfo=TZ)
HORA_BLOCO = time(hour=17, minute=45, tzinfo=TZ)       # 15 min antes do bloco
HORA_RELATORIO = time(hour=20, minute=0, tzinfo=TZ)   # domingo

DATA_PROVA = datetime(2026, 11, 22, tzinfo=TZ)
DIAS_SEMANA = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
               "Sexta-feira", "Sábado", "Domingo"]

TOKEN: str = ""
GUILD_ID: int = 0
con = db.conectar()


# ------------------------------------------------------------------ prazos

def marcos_ativos() -> list[dict]:
    confirmados = db.marcos_confirmados(con)
    saida = []
    for c in CONFIG["concursos"]:
        if not c.get("verificado"):
            continue
        for m in c.get("marcos", []):
            if m["id"] in confirmados:
                continue
            quando = datetime.fromisoformat(m["quando"]).replace(tzinfo=TZ)
            saida.append({**m, "quando_dt": quando, "concurso": c["nome"]})
    return sorted(saida, key=lambda m: m["quando_dt"])


def farol(dias: int, critico: bool) -> tuple[str, int]:
    limite = 7 if critico else 3
    if dias < 0:
        return "⚫", 0x2B2D31
    if dias <= limite:
        return "🔴", 0xED4245
    if dias <= 15:
        return "🟡", 0xFEE75C
    return "🟢", 0x57F287


def resumir(texto: str, limite: int) -> str:
    if len(texto) <= limite:
        return texto
    return texto[:limite].rsplit(" ", 1)[0] + "…"


def texto_dias(dias: int) -> str:
    if dias < 0:
        return f"passou há {abs(dias)} dia(s)"
    if dias == 0:
        return "**É HOJE**"
    if dias == 1:
        return "**é AMANHÃ**"
    return f"em **{dias} dias**"


def montar_briefing() -> tuple[discord.Embed, list[dict]]:
    agora = datetime.now(TZ)
    ativos = marcos_ativos()

    def dias_ate(m):
        return (m["quando_dt"].date() - agora.date()).days

    prox = ativos[0] if ativos else None
    _, cor = farol(dias_ate(prox) if prox else 999,
                   prox.get("critico", False) if prox else False)

    em = discord.Embed(
        title="Sentinela de Prazos",
        description=f"{DIAS_SEMANA[agora.weekday()]}, {agora:%d/%m/%Y}",
        colour=cor)

    a_cobrar = []
    if ativos:
        linhas = []
        for m in ativos[:6]:
            d = dias_ate(m)
            ic, _ = farol(d, m.get("critico", False))
            linhas.append(f"{ic} **{m['titulo']}**\n"
                          f"　{m['quando_dt']:%d/%m/%Y %H:%M} — {texto_dias(d)}\n"
                          f"　*{m['acao']}*")
            if d <= (7 if m.get("critico") else 3):
                a_cobrar.append(m)
        em.add_field(name="Confirmado por fonte primária",
                     value="\n\n".join(linhas), inline=False)

    pendentes = [c for c in CONFIG["concursos"]
                 if not c.get("verificado") and c.get("prioridade") != "ALVO-REAL"]
    if pendentes:
        em.add_field(
            name="Sem edital — fonte secundária, sem contagem regressiva",
            value="\n".join(f"⚪ **{c['nome']}** — {resumir(c['aguardando'], 110)}"
                            for c in pendentes), inline=False)

    em.set_footer(text=f"Prova do TCDF em {(DATA_PROVA.date() - agora.date()).days} dias")
    return em, a_cobrar


# --------------------------------------------------------------- relatorio

def hm(segundos: int) -> str:
    h, m = divmod(int(segundos) // 60, 60)
    return f"{h}h{m:02d}" if h else f"{m}min"


def montar_relatorio(dias: int, titulo: str) -> discord.Embed:
    desde, ate = db.periodo(dias)
    r = db.resumo(con, desde, ate)
    agora = datetime.now(TZ)

    em = discord.Embed(
        title=titulo,
        description=f"{datetime.fromisoformat(desde):%d/%m} a "
                    f"{datetime.fromisoformat(ate):%d/%m/%Y}",
        colour=0x5865F2)

    # 1. Tempo medido pelo bot. O unico numero que ninguem digitou.
    if r["voz"]:
        linhas = []
        for v in r["voz"]:
            atual, recorde = db.streak(con, v["usuario_id"])
            media = v["s"] / dias
            linhas.append(f"**{v['usuario']}** — {hm(v['s'])} em {v['n']} sessão(ões)\n"
                          f"　média {hm(media)}/dia · streak {atual}d (recorde {recorde}d)")
        em.add_field(name="⏱️ Tempo em call de estudo", value="\n".join(linhas),
                     inline=False)
    else:
        em.add_field(name="⏱️ Tempo em call de estudo",
                     value="Nenhuma sessão no período.\n"
                           "*Entrar em 🔇 Estudo Silencioso já conta, sem digitar nada.*",
                     inline=False)

    # 2. Questoes, por pessoa e por materia.
    if r["questoes_pessoa"]:
        linhas = []
        for q in r["questoes_pessoa"]:
            pct = 100 * q["a"] / q["f"] if q["f"] else 0
            sinal = "🟢" if pct >= 70 else "🟡" if pct >= 60 else "🔴"
            linhas.append(f"{sinal} **{q['usuario']}** — {q['a']}/{q['f']} = {pct:.0f}%")
        em.add_field(name="✏️ Questões", value="\n".join(linhas), inline=False)

        piores = []
        for m in r["questoes_materia"]:
            pct = 100 * m["a"] / m["f"] if m["f"] else 0
            piores.append((pct, m["materia"], m["a"], m["f"]))
        piores.sort()
        linhas = [f"{'🔴' if p < 60 else '🟡' if p < 70 else '🟢'} "
                  f"`{mat:<18}` {a}/{f} = {p:.0f}%"
                  for p, mat, a, f in piores[:8]]
        em.add_field(name="Por matéria (pior primeiro)", value="\n".join(linhas),
                     inline=False)

    # 3. Minimo inegociavel e erros.
    rodape = []
    for m in r["minimos"]:
        rodape.append(f"{m['usuario']}: {m['n']}/{dias} dias com o mínimo")
    for e in r["erros"]:
        rodape.append(f"{e['usuario']}: {e['n']} erro(s) lançado(s)")
    if rodape:
        em.add_field(name="📌 Consistência", value="\n".join(rodape), inline=False)

    # 4. Regua contra a prova. Ritmo, nao so volume.
    faltam = (DATA_PROVA.date() - agora.date()).days
    total_q = sum(q["f"] for q in r["questoes_pessoa"]) or 0
    projecao = int(total_q / dias * faltam) if dias and total_q else 0
    em.set_footer(text=f"Prova em {faltam} dias · nesse ritmo, mais ~{projecao} questões "
                       f"até lá")
    return em


# --------------------------------------------------------------------- bot

class Sentinela(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()   # ja inclui voice_states e reactions
        intents.members = True                # privilegiada: para dar boas-vindas
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        orfas = db.fechar_orfas(con)
        if orfas:
            print(f"{orfas} sessão(ões) de voz órfã(s) fechada(s).")
        db.migrar_estado_json(con, RAIZ / "estado.json")
        briefing_diario.start()
        aviso_do_bloco.start()
        relatorio_semanal.start()

    async def on_ready(self):
        # O sync dos comandos NAO pode ir no setup_hook: la o cache de guilds
        # ainda esta vazio, e usar o GUILD_ID cru quebra se o .env estiver com
        # a application id. Aqui a guild ja esta resolvida de verdade.
        global GUILD_ID
        g = guild_alvo(self)
        if g is None:
            print("Bot nao esta em nenhum servidor. Rode convite.py.")
            return
        GUILD_ID = g.id

        if not getattr(self, "_comandos_sincronizados", False):
            alvo = discord.Object(id=g.id)
            self.tree.copy_global_to(guild=alvo)
            await self.tree.sync(guild=alvo)
            self._comandos_sincronizados = True
            print(f"Comandos sincronizados em {g.name}.")

        # Quem ja estava em call quando o bot subiu tambem conta.
        if g:
            for canal in g.voice_channels:
                if canal.category and canal.category.name == CATEGORIA_ESTUDO:
                    for m in canal.members:
                        if not m.bot:
                            db.abrir_sessao(con, m.id, m.display_name, canal.name)
        print(f"Sentinela no ar como {self.user}.")


def guild_alvo(cliente: discord.Client):
    """A guild em que o bot opera. Aceita GUILD_ID vazio ou errado: com o bot
    em um servidor so, nao ha ambiguidade."""
    if GUILD_ID and GUILD_ID != cliente.user.id:
        g = cliente.get_guild(GUILD_ID)
        if g:
            return g
    return cliente.guilds[0] if cliente.guilds else None


bot = Sentinela()


def canal_por_nome(nome: str):
    g = guild_alvo(bot)
    return discord.utils.get(g.text_channels, name=nome) if g else None


def e_canal_de_estudo(canal) -> bool:
    return bool(canal and canal.category and canal.category.name == CATEGORIA_ESTUDO)


# ------------------------------------------------------------------ eventos

@bot.event
async def on_member_join(membro: discord.Member):
    """Boas-vindas. Curto de proposito: as tres coisas que a pessoa precisa
    fazer, e nao um tour pelos 15 canais."""
    if membro.bot:
        return
    canal = canal_por_nome(CANAL_BOAS_VINDAS)
    if canal is None:
        return

    faltam = (DATA_PROVA.date() - datetime.now(TZ).date()).days
    regras = canal_por_nome("📕┇rules")
    metas = canal_por_nome(CANAL_METAS)
    erros = canal_por_nome(CANAL_ERROS)
    sala = discord.utils.get(canal.guild.voice_channels, name="🔇 Estudo Silencioso")

    await canal.send(
        f"Chegou {membro.mention}. Bem-vinda.\n\n"
        f"Aqui não tem tour. São três coisas:\n\n"
        f"**1.** Antes de estudar, uma linha em "
        f"{metas.mention if metas else '#metas-do-dia'}. O que você vai fazer hoje.\n"
        f"**2.** Entra em {sala.mention if sala else '🔇 Estudo Silencioso'}. "
        f"Mic e câmera off, ninguém fala. Eu cronometro sozinho.\n"
        f"**3.** Todo erro vai para {erros.mention if erros else '#erros-do-dia'}, "
        f"na hora. É o canal que vira card no Anki, e o único cuja ausência "
        f"significa que o dia não aconteceu.\n\n"
        f"O resto está em {regras.mention if regras else '#rules'}. "
        f"Use `/estudei` quando fechar o mínimo de 1h.\n\n"
        f"**Faltam {faltam} dias para a prova do TCDF.**")


@bot.event
async def on_voice_state_update(membro, antes, depois):
    if membro.bot:
        return
    saiu = e_canal_de_estudo(antes.channel)
    entrou = e_canal_de_estudo(depois.channel)

    if saiu and antes.channel != depois.channel:
        segundos = db.fechar_sessao(con, membro.id)
        if segundos >= 600:            # abaixo de 10 min nao vale anuncio
            canal = canal_por_nome("diario")
            if canal:
                await canal.send(
                    f"⏱️ **{membro.display_name}** fechou {hm(segundos)} "
                    f"em {antes.channel.name}.")

    if entrou and antes.channel != depois.channel:
        db.abrir_sessao(con, membro.id, membro.display_name, depois.channel.name)


@bot.event
async def on_message(msg: discord.Message):
    """Erro lancado em #erros-do-dia.

    Sem a intent message_content, `msg.content` vem VAZIO: da para contar que
    houve um erro, mas nao para montar o card. Entao:
      - com a intent ligada, a convencao `pergunta :: resposta` vira card;
      - sem ela, conta o erro e avisa que o card so sai pelo /erro.
    """
    if msg.author.bot or not msg.guild:
        return
    if getattr(msg.channel, "name", None) != CANAL_ERROS:
        return

    db.registrar_erro(con, msg.author.id, msg.author.display_name, msg.id)

    texto = (msg.content or "").strip()
    if "::" in texto:
        frente, verso = texto.split("::", 1)
        materia = "geral"
        if frente.startswith("[") and "]" in frente:
            materia, frente = frente[1:].split("]", 1)
        db.enfileirar_card(con, msg.author.id, msg.author.display_name,
                           materia, frente, verso, fonte="#erros-do-dia",
                           mensagem_id=msg.id)
        await msg.add_reaction("📗")     # virou card
    else:
        await msg.add_reaction("📝")     # contado, mas nao virou card


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id or str(payload.emoji) != "✅":
        return
    marcos = db.marcos_da_mensagem(con, payload.message_id)
    if not marcos:
        return
    ja = db.marcos_confirmados(con)
    novos = [m for m in marcos if m not in ja]
    if not novos:
        return

    nome = payload.member.display_name if payload.member else "alguém"
    for marco_id in novos:
        db.confirmar_marco(con, marco_id, payload.user_id, nome)

    canal = bot.get_channel(payload.channel_id)
    await canal.send(f"✅ Confirmado por **{nome}** em "
                     f"{datetime.now(TZ):%d/%m/%Y %H:%M}: {', '.join(novos)}.\n"
                     f"Paro de cobrar. Registre a evidência no cofre.")


# ------------------------------------------------------------------ tarefas

@tasks.loop(time=HORA_BRIEFING)
async def briefing_diario():
    canal = canal_por_nome(CANAL_PRAZOS)
    if canal is None:
        return
    em, a_cobrar = montar_briefing()
    if not a_cobrar and datetime.now(TZ).weekday() != 0:
        return

    conteudo = None
    if a_cobrar:
        cargo = discord.utils.get(canal.guild.roles, name=CARGO_ALVO)
        mencao = cargo.mention if cargo else ""
        conteudo = (f"{mencao} — reaja com ✅ quando fizer. "
                    f"Sem reação, eu cobro de novo amanhã.")

    msg = await canal.send(content=conteudo, embed=em)
    if a_cobrar:
        await msg.add_reaction("✅")
        for m in a_cobrar:
            db.vincular_mensagem(con, msg.id, m["id"])


@tasks.loop(time=HORA_BLOCO)
async def aviso_do_bloco():
    """15 min antes do bloco, diz o que estudar hoje. Sem isto, o comeco do
    bloco vira decisao, e decisao no fim do dia e onde o plano se perde."""
    canal = canal_por_nome(CANAL_METAS)
    if canal is None:
        return
    hoje = datetime.now(TZ).date()
    b = bloco_do_dia(hoje)

    em = discord.Embed(
        title=f"Bloco de hoje — {b['hora']}",
        description=f"**{b['rotulo']}**\n{b['conteudo']}",
        colour=0xFEE75C)
    em.add_field(name="Estrutura", value=b["estrutura"], inline=False)
    em.set_footer(text=f"{MINIMO}  ·  prova em "
                       f"{(DATA_PROVA.date() - hoje).days} dias")

    cargo = discord.utils.get(canal.guild.roles, name=CARGO_ALVO)
    await canal.send(content=cargo.mention if cargo else None, embed=em)


@tasks.loop(time=HORA_RELATORIO)
async def relatorio_semanal():
    if datetime.now(TZ).weekday() != 6:      # so domingo
        return
    canal = canal_por_nome("marcos") or canal_por_nome("diario")
    if canal:
        await canal.send(embed=montar_relatorio(7, "Relatório da semana"))


@briefing_diario.before_loop
@aviso_do_bloco.before_loop
@relatorio_semanal.before_loop
async def antes():
    await bot.wait_until_ready()


# ----------------------------------------------------------------- comandos

@bot.tree.command(name="prazos", description="Contagem regressiva dos editais")
async def cmd_prazos(i: discord.Interaction):
    em, _ = montar_briefing()
    await i.response.send_message(embed=em)


@bot.tree.command(name="relatorio", description="Relatório de estudo do período")
@app_commands.describe(periodo="Janela do relatório")
@app_commands.choices(periodo=[
    app_commands.Choice(name="semana (7 dias)", value=7),
    app_commands.Choice(name="quinzena (14 dias)", value=14),
    app_commands.Choice(name="mês (30 dias)", value=30),
])
async def cmd_relatorio(i: discord.Interaction, periodo: app_commands.Choice[int]):
    await i.response.defer()
    await i.followup.send(embed=montar_relatorio(
        periodo.value, f"Relatório — {periodo.name}"))


@bot.tree.command(name="agora", description="Quem está em call de estudo agora")
async def cmd_agora(i: discord.Interaction):
    linhas = []
    for canal in i.guild.voice_channels:
        if e_canal_de_estudo(canal) and canal.members:
            gente = ", ".join(m.display_name for m in canal.members if not m.bot)
            if gente:
                linhas.append(f"🔊 **{canal.name}** — {gente}")
    await i.response.send_message(
        "\n".join(linhas) if linhas else "Ninguém em call agora.")


@bot.tree.command(name="estudei", description="Registra o mínimo inegociável de hoje")
async def cmd_estudei(i: discord.Interaction):
    novo = db.registrar_minimo(con, i.user.id, i.user.display_name)
    atual, recorde = db.streak(con, i.user.id)
    if not novo:
        await i.response.send_message(
            f"Hoje já está registrado. Streak: **{atual}** dia(s).", ephemeral=True)
        return
    marca = "🔥" if atual >= 7 else "✅"
    await i.response.send_message(
        f"{marca} **{i.user.display_name}** fechou o mínimo. "
        f"Streak: **{atual}** dia(s) · recorde {recorde}.\n"
        f"*{CONFIG['rotina']['descricao_minimo']}*")


@bot.tree.command(name="erro", description="Lança um erro e já vira card do Anki")
@app_commands.describe(materia="Matéria", pergunta="A frente do card",
                       resposta="O verso: o que é certo, e por quê")
async def cmd_erro(i: discord.Interaction, materia: str, pergunta: str, resposta: str):
    card_id = db.enfileirar_card(con, i.user.id, i.user.display_name,
                                 materia, pergunta, resposta, fonte="/erro")
    pend = len(db.cards_pendentes(con))
    db.registrar_erro(con, i.user.id, i.user.display_name, card_id or 0)

    await i.response.send_message(
        f"📗 **{materia}** — card na fila do Anki *(#{card_id}, {pend} pendente(s))*\n"
        f"**F:** {pergunta}\n**V:** {resposta}")


@bot.tree.command(name="anki", description="Mostra a fila de cards para o Anki")
async def cmd_anki(i: discord.Interaction):
    pend = db.cards_pendentes(con)
    if not pend:
        await i.response.send_message("Fila vazia. Nada esperando o Anki.")
        return
    por_materia: dict[str, int] = {}
    for c in pend:
        por_materia[c["materia"]] = por_materia.get(c["materia"], 0) + 1
    linhas = [f"`{m:<18}` {n}" for m, n in
              sorted(por_materia.items(), key=lambda x: -x[1])]
    await i.response.send_message(
        f"**{len(pend)} card(s) na fila**\n" + "\n".join(linhas) +
        "\n\nRode `python anki_sync.py` para entregar.")


@bot.tree.command(name="questoes", description="Registra questões feitas")
@app_commands.describe(materia="Matéria", feitas="Quantas", acertos="Quantas certas")
async def cmd_questoes(i: discord.Interaction, materia: str, feitas: int, acertos: int):
    if feitas <= 0 or not 0 <= acertos <= feitas:
        await i.response.send_message(
            "Números inconsistentes: acertos tem que estar entre 0 e feitas.",
            ephemeral=True)
        return

    db.registrar_questoes(con, i.user.id, i.user.display_name, materia, feitas, acertos)
    pct = 100 * acertos / feitas
    alerta = "" if pct >= 60 else "  ⚠️ abaixo da meta de 60%"
    await i.response.send_message(
        f"**{materia}** — {acertos}/{feitas} = **{pct:.0f}%**{alerta}\n"
        f"Os erros vão para **#{CANAL_ERROS}** e viram card no Anki.")


if __name__ == "__main__":
    from config import credenciais
    TOKEN, GUILD_ID = credenciais.carregar()
    bot.run(TOKEN, log_handler=None)
