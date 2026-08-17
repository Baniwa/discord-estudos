"""Sentinela de Prazos — bot do servidor de estudos.

O que ele faz, em ordem de importancia:

  1. Contagem regressiva diaria (07h BRT) para cada marco de edital, com escalada.
  2. Confirmacao por reacao: voce marca ✅ e ele para de cobrar. Sem confirmacao
     ele ASSUME QUE NAO FOI FEITO — a regra certa dado o historico de arrasto.
  3. Streak do minimo inegociavel (1h).
  4. Contador de questoes, alimentado por /questoes.

Regra que vale mais que as quatro: marco de fonte secundaria NAO recebe contagem
regressiva. So um lembrete de conferir a fonte primaria. Ver config/marcos.json.

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

load_dotenv()

# Idem setup_servidor.py: console cp1252 no Windows quebra no log do discord.py.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).parent
CONFIG = json.loads((RAIZ / "config" / "marcos.json").read_text(encoding="utf-8"))
ESTADO_ARQ = RAIZ / "estado.json"

TZ = ZoneInfo(CONFIG["timezone"])
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
CANAL_PRAZOS = os.getenv("CANAL_PRAZOS", "editais-e-prazos")
HORA_BRIEFING = time(hour=7, minute=0, tzinfo=TZ)


# ---------------------------------------------------------------- estado

def carregar_estado() -> dict:
    if ESTADO_ARQ.exists():
        return json.loads(ESTADO_ARQ.read_text(encoding="utf-8"))
    return {"confirmados": {}, "mensagens": {}, "streak": {}, "questoes": {}}


def salvar_estado(e: dict) -> None:
    ESTADO_ARQ.write_text(json.dumps(e, indent=2, ensure_ascii=False), encoding="utf-8")


estado = carregar_estado()


# ---------------------------------------------------------------- marcos

def marcos_ativos() -> list[dict]:
    """Marcos verificados, ainda nao confirmados, ordenados por data."""
    saida = []
    for c in CONFIG["concursos"]:
        if not c.get("verificado"):
            continue
        for m in c.get("marcos", []):
            if m["id"] in estado["confirmados"]:
                continue
            quando = datetime.fromisoformat(m["quando"]).replace(tzinfo=TZ)
            saida.append({**m, "quando_dt": quando, "concurso": c["nome"], "banca": c["banca"]})
    return sorted(saida, key=lambda m: m["quando_dt"])


def aguardando_edital() -> list[dict]:
    return [c for c in CONFIG["concursos"] if not c.get("verificado")]


def farol(dias: int, critico: bool) -> tuple[str, int]:
    """Emoji + cor por urgencia. Marco critico escala mais cedo."""
    limite_vermelho = 3 if not critico else 7
    if dias < 0:
        return "⚫", 0x2B2D31
    if dias <= limite_vermelho:
        return "🔴", 0xED4245
    if dias <= 15:
        return "🟡", 0xFEE75C
    return "🟢", 0x57F287


DIAS_SEMANA = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
               "Sexta-feira", "Sábado", "Domingo"]


def resumir(texto: str, limite: int) -> str:
    """Corta na fronteira de palavra - truncar no meio de uma palavra faz o
    aviso parecer erro de bot e o leitor para de confiar nele."""
    if len(texto) <= limite:
        return texto
    return texto[:limite].rsplit(" ", 1)[0] + "…"


def texto_dias(dias: int) -> str:
    if dias < 0:
        return f"passou ha {abs(dias)} dia(s)"
    if dias == 0:
        return "**É HOJE**"
    if dias == 1:
        return "**é AMANHÃ**"
    return f"em **{dias} dias**"


def montar_briefing() -> tuple[discord.Embed, list[dict]]:
    hoje = datetime.now(TZ)
    ativos = marcos_ativos()

    # Diferenca por DATA de calendario, nao por 24h corridas: faltando 8 dias e
    # 14 horas, a pessoa conta 9 dias, e timedelta.days truncaria para 8.
    def dias_ate(m: dict) -> int:
        return (m["quando_dt"].date() - hoje.date()).days

    proximo = ativos[0] if ativos else None
    dias_prox = dias_ate(proximo) if proximo else 999
    _, cor = farol(dias_prox, proximo.get("critico", False) if proximo else False)

    em = discord.Embed(
        title="Sentinela de Prazos",
        description=f"{DIAS_SEMANA[hoje.weekday()]}, {hoje:%d/%m/%Y} · trilha SEFAZ Auditor de TI",
        colour=cor,
    )

    a_cobrar = []
    if ativos:
        linhas = []
        for m in ativos[:6]:
            dias = dias_ate(m)
            ic, _ = farol(dias, m.get("critico", False))
            linhas.append(
                f"{ic} **{m['titulo']}**\n"
                f"　{m['quando_dt'].strftime('%d/%m/%Y %H:%M')} — {texto_dias(dias)}\n"
                f"　*{m['acao']}*"
            )
            limite = 7 if m.get("critico") else 3
            if dias <= limite:
                a_cobrar.append(m)
        em.add_field(name="Confirmado por fonte primária", value="\n\n".join(linhas), inline=False)
    else:
        em.add_field(name="Confirmado por fonte primária",
                     value="Nenhum marco aberto.", inline=False)

    pendentes = aguardando_edital()
    if pendentes:
        linhas = [f"⚪ **{c['nome']}** — {resumir(c['aguardando'], 110)}\n　`{c['checar_em']}`"
                  for c in pendentes if c.get("prioridade") != "ALVO-REAL"]
        if linhas:
            em.add_field(
                name="Sem edital — fonte secundária, sem contagem regressiva",
                value="\n".join(linhas), inline=False)

    dias_prova = (datetime(2026, 11, 22, tzinfo=TZ).date() - hoje.date()).days
    s = estado["streak"].get("atual", 0)
    em.set_footer(text=f"Prova do TCDF em {dias_prova} dias · streak do mínimo: {s} dia(s)")
    return em, a_cobrar


# ---------------------------------------------------------------- bot

class Sentinela(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.reactions = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        if GUILD_ID:
            g = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=g)
            await self.tree.sync(guild=g)
        briefing_diario.start()


bot = Sentinela()


def canal_prazos() -> discord.TextChannel | None:
    g = bot.get_guild(GUILD_ID)
    return discord.utils.get(g.text_channels, name=CANAL_PRAZOS) if g else None


@tasks.loop(time=HORA_BRIEFING)
async def briefing_diario():
    canal = canal_prazos()
    if canal is None:
        return

    em, a_cobrar = montar_briefing()

    # Dia calmo nao gera post. So fala quando ha o que cobrar ou e segunda.
    if not a_cobrar and datetime.now(TZ).weekday() != 0:
        return

    conteudo = None
    if a_cobrar:
        cargo = discord.utils.get(canal.guild.roles, name="concurseira")
        mencao = cargo.mention if cargo else ""
        conteudo = f"{mencao} — reaja com ✅ quando fizer. Sem reação, eu cobro de novo amanhã."

    msg = await canal.send(content=conteudo, embed=em)

    if a_cobrar:
        await msg.add_reaction("✅")
        for m in a_cobrar:
            estado["mensagens"][str(msg.id)] = m["id"]
        salvar_estado(estado)


@briefing_diario.before_loop
async def antes():
    await bot.wait_until_ready()


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id or str(payload.emoji) != "✅":
        return
    marco_id = estado["mensagens"].get(str(payload.message_id))
    if not marco_id or marco_id in estado["confirmados"]:
        return

    agora = datetime.now(TZ)
    estado["confirmados"][marco_id] = {
        "em": agora.isoformat(),
        "por": payload.user_id,
    }
    salvar_estado(estado)

    canal = bot.get_channel(payload.channel_id)
    await canal.send(
        f"✅ **{marco_id}** confirmado em {agora.strftime('%d/%m/%Y %H:%M')}. "
        f"Paro de cobrar. Registre a evidência no cofre."
    )


# ---------------------------------------------------------------- comandos

@bot.tree.command(name="prazos", description="Mostra a contagem regressiva agora")
async def cmd_prazos(interacao: discord.Interaction):
    em, _ = montar_briefing()
    await interacao.response.send_message(embed=em)


@bot.tree.command(name="estudei", description="Registra o mínimo inegociável de hoje (1h)")
async def cmd_estudei(interacao: discord.Interaction):
    hoje = datetime.now(TZ).date().isoformat()
    if estado["streak"].get("ultimo") == hoje:
        await interacao.response.send_message(
            f"Hoje já está registrado. Streak: **{estado['streak'].get('atual', 0)}** dia(s).",
            ephemeral=True)
        return

    ontem = (datetime.now(TZ).date() - timedelta(days=1)).isoformat()
    atual = estado["streak"].get("atual", 0)
    atual = atual + 1 if estado["streak"].get("ultimo") == ontem else 1

    estado["streak"] = {"ultimo": hoje, "atual": atual,
                        "recorde": max(atual, estado["streak"].get("recorde", 0))}
    salvar_estado(estado)

    marca = "🔥" if atual >= 7 else "✅"
    await interacao.response.send_message(
        f"{marca} Registrado. Streak: **{atual}** dia(s) · recorde: {estado['streak']['recorde']}.\n"
        f"*{CONFIG['rotina']['descricao_minimo']}*")


@bot.tree.command(name="questoes", description="Registra questões feitas hoje")
@app_commands.describe(materia="Matéria", feitas="Quantas", acertos="Quantas certas")
async def cmd_questoes(interacao: discord.Interaction, materia: str, feitas: int, acertos: int):
    hoje = datetime.now(TZ).date().isoformat()
    reg = estado["questoes"].setdefault(hoje, {})
    m = reg.setdefault(materia.lower(), {"feitas": 0, "acertos": 0})
    m["feitas"] += feitas
    m["acertos"] += acertos
    salvar_estado(estado)

    pct = 100 * m["acertos"] / m["feitas"] if m["feitas"] else 0
    alerta = "" if pct >= 60 else "  ⚠️ abaixo da meta de 60%"
    await interacao.response.send_message(
        f"**{materia}** hoje: {m['acertos']}/{m['feitas']} = **{pct:.0f}%**{alerta}\n"
        f"Os erros vão para **#erros-do-dia** e viram card no Anki.")


if __name__ == "__main__":
    if not TOKEN or not GUILD_ID:
        sys.exit("Faltando DISCORD_BOT_TOKEN ou DISCORD_GUILD_ID no .env")
    bot.run(TOKEN)
