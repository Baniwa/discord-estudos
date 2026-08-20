"""Sentinela — bot do servidor de estudos.

  1. Cobra prazo de edital, com escalada e confirmacao por reacao.
  2. Cronometra sozinho o tempo em call na SALA DE ESTUDO. Isto e o que
     sustenta os relatorios: dado que ninguem precisa lembrar de digitar.
  3. Conta os erros lancados em #erros-do-dia.
  4. Fecha relatorio semanal e sob demanda.
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

import anki_sync  # noqa: E402
import db  # noqa: E402
from config.agenda import MINIMO, SEMANAS, bloco_do_dia  # noqa: E402

CONFIG = json.loads((RAIZ / "config" / "marcos.json").read_text(encoding="utf-8"))
TZ = ZoneInfo(CONFIG["timezone"])

CANAL_PRAZOS = os.getenv("CANAL_PRAZOS", "editais-e-prazos")
CANAL_ERROS = "erros-do-dia"
CATEGORIA_ESTUDO = "🔊 SALA DE ESTUDO"
CARGO_ALVO = "⚔️ Maidens"

CANAL_BOAS_VINDAS = "🤙🏽┇boas-vindas"
CANAL_METAS = "metas-do-dia"
CANAL_AULAS = "aulas"

HORA_BRIEFING = time(hour=7, minute=0, tzinfo=TZ)
HORA_BLOCO_SEMANA = time(hour=17, minute=45, tzinfo=TZ)
HORA_BLOCO_FDS = time(hour=9, minute=15, tzinfo=TZ)
HORA_LOG = time(hour=2, minute=0, tzinfo=TZ)
HORA_RELATORIO = time(hour=20, minute=0, tzinfo=TZ)

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

    # 2b. Aulas. Separado de questoes de proposito: assistir e consumo,
    # resolver e producao. Semana so de aula aparece como semana sem producao.
    aulas_disc = db.aulas_periodo(con, desde, ate)
    if aulas_disc:
        total_min = sum(a["min"] or 0 for a in aulas_disc)
        linhas = [f"`{a['disciplina']:<16}` {a['n']} aula(s) · {a['min'] or 0} min"
                  for a in aulas_disc[:6]]
        alerta = ""
        if r["questoes_pessoa"]:
            feitas = sum(q["f"] for q in r["questoes_pessoa"])
            if total_min > 120 and feitas < total_min / 10:
                alerta = ("\n⚠️ **Muita aula e pouca questão no período.** "
                          "A prova é de questão, não de aula.")
        else:
            alerta = "\n⚠️ **Nenhuma questão registrada no período.**"
        # Aula e call medem coisas diferentes e PODEM se sobrepor: assistir
        # dentro da sala de voz conta nas duas. Sem esta nota, quem le
        # "2h em call" e "2h de aula" soma 4h, que nunca aconteceram.
        rodape = ("\n\n*Minutos de aula e tempo em call medem coisas diferentes e podem se sobrepor. Não somam.*")
        em.add_field(name=f"🎧 Aulas — {total_min} min",
                     value="\n".join(linhas) + alerta + rodape,
                     inline=False)

    # 3. Anki. O que ela errou de novo, que e o unico sinal que muda a semana.
    revisados = db.anki_revisados(con, desde, ate)
    dificeis = db.anki_top_dificeis(con, 5)
    snap = db.anki_ultimo_snapshot(con)

    if revisados or dificeis or snap:
        venc = sum((s["revisar"] or 0) + (s["aprender"] or 0) for s in snap)
        novos = sum(s["novos"] or 0 for s in snap)
        cabeca = [f"**{revisados}** revisão(ões) no período",
                  f"**{venc}** card(s) esperando · {novos} novo(s)"]
        em.add_field(name="🧠 Anki", value=" · ".join(cabeca), inline=False)

    if dificeis:
        linhas = []
        for c in dificeis:
            deck = c["deck"].split("::")[-1]
            fac = f" · facilidade {c['facilidade'] / 10:.0f}%" if c["facilidade"] else ""
            linhas.append(f"🔴 **{c['lapses']}x errado** · `{deck}`{fac}\n"
                          f"　{c['frente'][:96]}")
        em.add_field(
            name="O que não gruda (do Anki)",
            value="\n".join(linhas) +
                  "\n\n*Card com muito lapso é conceito para voltar ao bloco de "
                  "conteúdo, não para revisar mais forte.*",
            inline=False)

    # 4. Minimo inegociavel e erros.
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


# ------------------------------------------------------------------- adesao

def montar_adesao() -> discord.Embed:
    hoje = datetime.now(TZ).date()
    em = discord.Embed(title="Adesão ao plano", colour=0x5865F2)

    comecadas = [(inicio, fim, rotulo) for inicio, fim, rotulo, _ in SEMANAS
                 if inicio <= hoje]
    if not comecadas:
        em.description = ("O plano começa em "
                          f"{SEMANAS[0][0]:%d/%m/%Y}. Nada a cobrar ainda.")
        return em

    linhas = []
    for inicio, fim, rotulo in comecadas[-8:]:
        ate = min(fim, hoje)
        dias = (ate - inicio).days + 1
        pessoas = db.adesao(con, inicio.isoformat(), ate.isoformat())
        corpo = " · ".join(f"{p['usuario']} **{p['dias_com_minimo'] or 0}**/{dias}"
                           for p in pessoas) or f"ninguém — 0/{dias}"
        marca = "▶" if fim >= hoje else "　"
        linhas.append(f"{marca} `{rotulo.split(' — ')[0]:<7}` {corpo}")

    em.add_field(name="Dias com o mínimo, por semana do plano",
                 value="\n".join(linhas), inline=False)

    inicio_plano = SEMANAS[0][0]
    dias_plano = (hoje - inicio_plano).days + 1
    geral = db.adesao(con, inicio_plano.isoformat(), hoje.isoformat())
    if geral:
        em.add_field(
            name="No plano inteiro",
            value="\n".join(
                f"**{p['usuario']}** — {p['dias_com_minimo'] or 0}/{dias_plano} dias "
                f"com o mínimo · {p['dias_com_log'] or 0} com algum registro · "
                f"{hm(p['s'] or 0)} em call"
                for p in geral),
            inline=False)

    em.set_footer(text="Conta os dias já fechados. O de hoje entra no "
                       "fechamento das 02h.")
    return em


# --------------------------------------------------------------------- bot

class Sentinela(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        db.migrar_estado_json(con, RAIZ / "estado.json")
        briefing_diario.start()
        aviso_do_bloco.start()
        relatorio_semanal.start()
        fechamento_diario.start()
        ler_anki.start()

    async def on_ready(self):
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

        em_call = set()
        for canal in g.voice_channels:
            if canal.category and canal.category.name == CATEGORIA_ESTUDO:
                for m in canal.members:
                    if not m.bot:
                        em_call.add(m.id)
                        db.abrir_sessao(con, m.id, m.display_name, canal.name)

        orfas = db.fechar_orfas(con, preservar=em_call)
        if orfas:
            print(f"{orfas} sessão(ões) órfã(s) fechada(s) "
                  f"(quem está em call foi preservado).")
        print(f"Sentinela no ar como {self.user}. "
              f"{len(em_call)} em call de estudo agora.")


def guild_alvo(cliente: discord.Client):
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


def montar_bloco(dia, titulo: str) -> discord.Embed:
    b = bloco_do_dia(dia)
    em = discord.Embed(
        title=f"{titulo} — {b['hora']}",
        description=f"**{b['rotulo']}**\n{b['conteudo']}",
        colour=0xFEE75C)
    em.add_field(name="Estrutura", value=b["estrutura"], inline=False)
    em.set_footer(text=f"{MINIMO}  ·  prova em "
                       f"{(DATA_PROVA.date() - dia).days} dias")
    return em


@tasks.loop(time=[HORA_BLOCO_SEMANA, HORA_BLOCO_FDS])
async def aviso_do_bloco():
    agora = datetime.now(TZ)
    fim_de_semana = agora.weekday() >= 5
    if fim_de_semana != (agora.hour < 12):
        return

    canal = canal_por_nome(CANAL_METAS)
    if canal is None:
        return

    em = montar_bloco(agora.date(), "Bloco de hoje")
    cargo = discord.utils.get(canal.guild.roles, name=CARGO_ALVO)
    await canal.send(content=cargo.mention if cargo else None, embed=em)


def _sincronizar_anki_isolado() -> dict:
    c = db.conectar()
    try:
        pendentes = db.cards_pendentes(c)
        entregues = anki_sync.enviar_por_ankiconnect(c, pendentes) if pendentes else 0
        stats = anki_sync.coletar_stats(c)
        return {**stats, "entregues": entregues}
    finally:
        c.close()


@tasks.loop(minutes=30)
async def ler_anki():
    import asyncio
    try:
        if not await asyncio.to_thread(anki_sync.anki_disponivel):
            return
        s = await asyncio.to_thread(_sincronizar_anki_isolado)

        if s["entregues"]:
            canal = canal_por_nome(CANAL_ERROS)
            if canal:
                await canal.send(
                    f"📗 {s['entregues']} card(s) entregues ao Anki agora.")
        if s["entregues"] or s["dificeis"] or s["revisados_hoje"]:
            print(f"Anki: {s['entregues']} entregue(s) · "
                  f"{s['revisados_hoje']} revisão(ões) hoje · "
                  f"{s['dificeis']} difícil(eis).")
    except Exception as e:
        print(f"Anki: falha ({e}). A fila fica intacta, tento de novo em 30 min.")


def montar_log_diario(dia, pessoas: list[dict], parcial: bool = False) -> discord.Embed:
    b = bloco_do_dia(dia)
    houve = [p for p in pessoas
             if p["segundos_voz"] or p["questoes"] or p["erros"] or p["aulas"]]

    if parcial:
        vazio = 0xFEE75C
        titulo = f"Hoje, até agora — {DIAS_SEMANA[dia.weekday()]}"
    else:
        vazio = 0xED4245
        titulo = f"Log de {dia:%d/%m/%Y} — {DIAS_SEMANA[dia.weekday()]}"

    em = discord.Embed(
        title=titulo,
        description=f"**{b['rotulo']}** · bloco previsto {b['hora']}",
        colour=0x57F287 if houve else vazio)

    if not houve:
        em.add_field(
            name="⚪ Ainda sem registro" if parcial else "🔴 Dia sem registro",
            value="Nenhuma call, nenhuma questão, nenhum erro.\n"
                  + ("*O que está previsto:* " if parcial else "*O que estava previsto:* ")
                  + b["conteudo"][:220],
            inline=False)
        em.set_footer(text=MINIMO)
        return em

    for p in houve:
        pct = 100 * p["acertos"] / p["questoes"] if p["questoes"] else None
        linhas = [f"⏱️ **{hm(p['segundos_voz'])}** em call"]
        if p["questoes"]:
            sinal = "🟢" if pct >= 70 else "🟡" if pct >= 60 else "🔴"
            linhas.append(f"✏️ {sinal} {p['acertos']}/{p['questoes']} = {pct:.0f}%")
        else:
            linhas.append("✏️ nenhuma questão registrada")
        if p["aulas"]:
            linhas.append(f"🎧 {p['aulas']} aula(s), {p['minutos_aula']} min")
        linhas.append(f"📗 {p['erros']} erro(s) · {p['cards']} card(s) novo(s)")
        linhas.append("✅ mínimo fechado" if p["minimo"]
                      else "⚪ mínimo não registrado (`/estudei`)")
        em.add_field(name=p["usuario"], value="\n".join(linhas), inline=True)

    em.add_field(name="Previsto para hoje", value=b["conteudo"][:400], inline=False)
    em.set_footer(text=f"Prova em {(DATA_PROVA.date() - dia).days} dias")
    return em


@tasks.loop(time=HORA_LOG)
async def fechamento_diario():
    dia = datetime.now(TZ).date() - timedelta(days=1)   # fecha o dia que passou
    semana = bloco_do_dia(dia)["rotulo"]
    pessoas = db.fechar_dia(con, dia.isoformat(), semana)

    canal = canal_por_nome("diario")
    if canal:
        await canal.send(embed=montar_log_diario(dia, pessoas))


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
@fechamento_diario.before_loop
@ler_anki.before_loop
async def antes():
    await bot.wait_until_ready()


# ----------------------------------------------------------------- comandos

async def sugerir_materia(i: discord.Interaction, atual: str):
    return [app_commands.Choice(name=nome, value=nome)
            for nome in db.materias(con, atual)]


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
@app_commands.autocomplete(materia=sugerir_materia)
@app_commands.describe(materia="Matéria", pergunta="A frente do card",
                       resposta="O verso: o que é certo, e por quê")
async def cmd_erro(i: discord.Interaction, materia: str, pergunta: str, resposta: str):
    card_id = db.enfileirar_card(con, i.user.id, i.user.display_name,
                                 materia, pergunta, resposta, fonte="/erro")
    pend = len(db.cards_pendentes(con))
    db.registrar_erro(con, i.user.id, i.user.display_name, card_id)

    await i.response.send_message(
        f"📗 **{materia}** — card na fila do Anki *(#{card_id}, {pend} pendente(s))*\n"
        f"**F:** {pergunta}\n**V:** {resposta}")


@bot.tree.command(name="anki", description="Estado do Anki: fila, vencidos e o que não gruda")
async def cmd_anki(i: discord.Interaction):
    em = discord.Embed(title="Anki", colour=0x5865F2)

    pend = db.cards_pendentes(con)
    if pend:
        por_materia: dict[str, int] = {}
        for c in pend:
            por_materia[c["materia"]] = por_materia.get(c["materia"], 0) + 1
        em.add_field(
            name=f"📤 Fila do bot — {len(pend)} card(s)",
            value="\n".join(f"`{m:<16}` {n}" for m, n in
                            sorted(por_materia.items(), key=lambda x: -x[1])) +
                  "\n*Entregues no próximo `anki_sync`, ou sozinho se o Anki estiver aberto.*",
            inline=False)
    else:
        em.add_field(name="📤 Fila do bot", value="Vazia.", inline=False)

    snap = db.anki_ultimo_snapshot(con)
    if snap:
        linhas = []
        for s in snap:
            deck = s["deck"].split("::")[-1]
            total = (s["revisar"] or 0) + (s["aprender"] or 0)
            linhas.append(f"`{deck:<16}` {total} para hoje · {s['novos'] or 0} novo(s)")
        em.add_field(name=f"📚 Coleção (lida em {snap[0]['dia']})",
                     value="\n".join(linhas), inline=False)
    else:
        em.add_field(name="📚 Coleção",
                     value="Ainda não li o Anki. Abra o Anki com o AnkiConnect "
                           "e eu leio em até 30 min.", inline=False)

    dificeis = db.anki_top_dificeis(con, 5)
    if dificeis:
        em.add_field(
            name="🔴 O que não gruda",
            value="\n".join(
                f"**{c['lapses']}x** · `{c['deck'].split('::')[-1]}` — "
                f"{c['frente'][:70]}" for c in dificeis),
            inline=False)

    await i.response.send_message(embed=em)


@bot.tree.command(name="aula", description="Registra uma aula assistida")
@app_commands.autocomplete(disciplina=sugerir_materia)
@app_commands.describe(
    disciplina="Matéria da aula",
    aula="Qual aula (número e título)",
    minutos="Duração assistida, em minutos",
    professor="Quem dá a aula (opcional)",
    fonte="Onde (Estratégia, YouTube, PDF...)",
    nota="O que ficou dessa aula, em uma linha (opcional)")
async def cmd_aula(i: discord.Interaction, disciplina: str, aula: str, minutos: int,
                   professor: str = None, fonte: str = "Estratégia",
                   nota: str = None):
    if minutos <= 0 or minutos > 600:
        await i.response.send_message(
            "Minutos fora do razoável (1 a 600).", ephemeral=True)
        return

    db.registrar_aula(con, i.user.id, i.user.display_name, disciplina,
                      professor, aula, minutos, fonte, nota)

    em = discord.Embed(
        title=aula[:250],
        description=f"**{disciplina}**" + (f" · {professor}" if professor else ""),
        colour=0x5865F2)
    em.add_field(name="Duração", value=f"{minutos} min", inline=True)
    em.add_field(name="Fonte", value=fonte, inline=True)
    if nota:
        em.add_field(name="O que ficou", value=nota[:500], inline=False)
    em.set_footer(text=f"{i.user.display_name} · aula assistida não é questão "
                       f"resolvida. Fecha com /questoes.")

    canal = canal_por_nome(CANAL_AULAS)
    if canal and canal.id != i.channel_id:
        await canal.send(embed=em)
        await i.response.send_message(
            f"Registrada em {canal.mention}.", ephemeral=True)
    else:
        await i.response.send_message(embed=em)


@bot.tree.command(name="questoes", description="Registra questões feitas")
@app_commands.autocomplete(materia=sugerir_materia)
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


@bot.tree.command(name="bloco", description="O que estudar hoje, segundo o plano")
@app_commands.describe(quando="Hoje ou amanhã")
@app_commands.choices(quando=[
    app_commands.Choice(name="hoje", value=0),
    app_commands.Choice(name="amanhã", value=1),
])
async def cmd_bloco(i: discord.Interaction, quando: int = 0):
    dia = datetime.now(TZ).date() + timedelta(days=quando)
    await i.response.send_message(
        embed=montar_bloco(dia, "Bloco de amanhã" if quando else "Bloco de hoje"))


@bot.tree.command(name="hoje", description="O dia até agora, antes do fechamento das 02h")
async def cmd_hoje(i: discord.Interaction):
    dia = datetime.now(TZ).date()
    await i.response.send_message(
        embed=montar_log_diario(dia, db.agregar_dia(con, dia.isoformat()),
                                parcial=True))


@bot.tree.command(name="adesao", description="Quantos dias de cada semana do plano foram cumpridos")
async def cmd_adesao(i: discord.Interaction):
    await i.response.send_message(embed=montar_adesao())


if __name__ == "__main__":
    from config import credenciais
    TOKEN, GUILD_ID = credenciais.carregar()
    bot.run(TOKEN, log_handler=None)
