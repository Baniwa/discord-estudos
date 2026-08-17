"""Banco do bot. SQLite, arquivo unico, sem servidor.

Por que SQLite e nao o estado.json de antes: relatorio precisa de serie
temporal (quanto tempo, em que dia, em que materia) e de agregacao. Em JSON
isso vira leitura do arquivo inteiro a cada consulta e corrompe facil se o
processo morrer no meio da escrita.

Nada aqui apaga registro. Sessao de voz em aberto e fechada na proxima subida
do bot, nao descartada.
"""

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ARQUIVO = Path(__file__).parent / "estudos.db"
TZ = ZoneInfo("America/Sao_Paulo")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS sessoes_voz (
    id          INTEGER PRIMARY KEY,
    usuario_id  INTEGER NOT NULL,
    usuario     TEXT    NOT NULL,
    canal       TEXT    NOT NULL,
    inicio      TEXT    NOT NULL,
    fim         TEXT,
    segundos    INTEGER
);
CREATE INDEX IF NOT EXISTS ix_voz_usuario ON sessoes_voz(usuario_id, inicio);

CREATE TABLE IF NOT EXISTS questoes (
    id          INTEGER PRIMARY KEY,
    usuario_id  INTEGER NOT NULL,
    usuario     TEXT    NOT NULL,
    dia         TEXT    NOT NULL,
    materia     TEXT    NOT NULL,
    feitas      INTEGER NOT NULL,
    acertos     INTEGER NOT NULL,
    registrado  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_questoes_dia ON questoes(dia);

CREATE TABLE IF NOT EXISTS minimos (
    usuario_id  INTEGER NOT NULL,
    usuario     TEXT    NOT NULL,
    dia         TEXT    NOT NULL,
    registrado  TEXT    NOT NULL,
    PRIMARY KEY (usuario_id, dia)
);

CREATE TABLE IF NOT EXISTS erros (
    id          INTEGER PRIMARY KEY,
    usuario_id  INTEGER NOT NULL,
    usuario     TEXT    NOT NULL,
    dia         TEXT    NOT NULL,
    mensagem_id INTEGER UNIQUE
);

-- Card fica no banco do bot ate ser entregue ao Anki. A fila existe porque o
-- Anki nao esta sempre aberto (e pode nem estar na mesma maquina do bot). Sem
-- ela, erro lancado com o Anki fechado se perderia, que e justamente quando a
-- pessoa mais estuda.
CREATE TABLE IF NOT EXISTS cards (
    id           INTEGER PRIMARY KEY,
    usuario_id   INTEGER NOT NULL,
    usuario      TEXT    NOT NULL,
    dia          TEXT    NOT NULL,
    materia      TEXT    NOT NULL,
    frente       TEXT    NOT NULL,
    verso        TEXT    NOT NULL,
    fonte        TEXT,
    mensagem_id  INTEGER UNIQUE,
    entregue_em  TEXT,
    destino      TEXT
);
CREATE INDEX IF NOT EXISTS ix_cards_pendente ON cards(entregue_em);

CREATE TABLE IF NOT EXISTS confirmacoes (
    marco_id    TEXT PRIMARY KEY,
    usuario_id  INTEGER,
    usuario     TEXT,
    em          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mensagens_marco (
    mensagem_id INTEGER NOT NULL,
    marco_id    TEXT    NOT NULL,
    PRIMARY KEY (mensagem_id, marco_id)
);
"""


def conectar() -> sqlite3.Connection:
    con = sqlite3.connect(ARQUIVO)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")   # sobrevive a queda no meio da escrita
    con.executescript(ESQUEMA)
    return con


def hoje() -> str:
    return datetime.now(TZ).date().isoformat()


# ------------------------------------------------------------------ voz

def abrir_sessao(con, usuario_id: int, usuario: str, canal: str) -> None:
    aberta = con.execute(
        "SELECT id FROM sessoes_voz WHERE usuario_id=? AND fim IS NULL",
        (usuario_id,)).fetchone()
    if aberta:
        return
    con.execute(
        "INSERT INTO sessoes_voz (usuario_id, usuario, canal, inicio) VALUES (?,?,?,?)",
        (usuario_id, usuario, canal, datetime.now(TZ).isoformat()))
    con.commit()


def fechar_sessao(con, usuario_id: int) -> int:
    """Fecha a sessao aberta e devolve a duracao em segundos (0 se nao havia)."""
    linha = con.execute(
        "SELECT id, inicio FROM sessoes_voz WHERE usuario_id=? AND fim IS NULL",
        (usuario_id,)).fetchone()
    if not linha:
        return 0
    agora = datetime.now(TZ)
    inicio = datetime.fromisoformat(linha["inicio"])
    segundos = max(0, int((agora - inicio).total_seconds()))
    con.execute("UPDATE sessoes_voz SET fim=?, segundos=? WHERE id=?",
                (agora.isoformat(), segundos, linha["id"]))
    con.commit()
    return segundos


def fechar_orfas(con) -> int:
    """Sessao que ficou aberta porque o bot caiu. Fecha pelo ultimo instante
    conhecido em vez de jogar fora - perder hora estudada desmotiva mais que
    contar de menos."""
    abertas = con.execute(
        "SELECT id, inicio FROM sessoes_voz WHERE fim IS NULL").fetchall()
    for linha in abertas:
        inicio = datetime.fromisoformat(linha["inicio"])
        # Teto de 4h: sessao aberta alem disso quase certamente e o bot que caiu.
        fim = min(datetime.now(TZ), inicio + timedelta(hours=4))
        con.execute("UPDATE sessoes_voz SET fim=?, segundos=? WHERE id=?",
                    (fim.isoformat(), int((fim - inicio).total_seconds()), linha["id"]))
    con.commit()
    return len(abertas)


# -------------------------------------------------------------- registros

def registrar_questoes(con, usuario_id, usuario, materia, feitas, acertos) -> None:
    con.execute(
        "INSERT INTO questoes (usuario_id, usuario, dia, materia, feitas, acertos, registrado)"
        " VALUES (?,?,?,?,?,?,?)",
        (usuario_id, usuario, hoje(), materia.lower().strip(), feitas, acertos,
         datetime.now(TZ).isoformat()))
    con.commit()


def registrar_minimo(con, usuario_id, usuario) -> bool:
    """True se registrou agora, False se o dia ja estava marcado."""
    try:
        con.execute(
            "INSERT INTO minimos (usuario_id, usuario, dia, registrado) VALUES (?,?,?,?)",
            (usuario_id, usuario, hoje(), datetime.now(TZ).isoformat()))
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def registrar_erro(con, usuario_id, usuario, mensagem_id) -> None:
    con.execute(
        "INSERT OR IGNORE INTO erros (usuario_id, usuario, dia, mensagem_id)"
        " VALUES (?,?,?,?)", (usuario_id, usuario, hoje(), mensagem_id))
    con.commit()


def enfileirar_card(con, usuario_id, usuario, materia, frente, verso,
                    fonte=None, mensagem_id=None) -> int | None:
    """Devolve o id do card, ou None se a mensagem ja tinha virado card."""
    cur = con.execute(
        "INSERT OR IGNORE INTO cards"
        " (usuario_id, usuario, dia, materia, frente, verso, fonte, mensagem_id)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (usuario_id, usuario, hoje(), materia.lower().strip(),
         frente.strip(), verso.strip(), fonte, mensagem_id))
    con.commit()
    return cur.lastrowid if cur.rowcount else None


def cards_pendentes(con, materia: str | None = None) -> list:
    sql = "SELECT * FROM cards WHERE entregue_em IS NULL"
    args = []
    if materia:
        sql += " AND materia=?"
        args.append(materia.lower().strip())
    return con.execute(sql + " ORDER BY id", args).fetchall()


def marcar_entregue(con, ids: list[int], destino: str) -> None:
    agora = datetime.now(TZ).isoformat()
    con.executemany("UPDATE cards SET entregue_em=?, destino=? WHERE id=?",
                    [(agora, destino, i) for i in ids])
    con.commit()


def confirmar_marco(con, marco_id, usuario_id, usuario) -> None:
    con.execute(
        "INSERT OR REPLACE INTO confirmacoes (marco_id, usuario_id, usuario, em)"
        " VALUES (?,?,?,?)",
        (marco_id, usuario_id, usuario, datetime.now(TZ).isoformat()))
    con.commit()


def marcos_confirmados(con) -> set[str]:
    return {r["marco_id"] for r in con.execute("SELECT marco_id FROM confirmacoes")}


def vincular_mensagem(con, mensagem_id, marco_id) -> None:
    con.execute("INSERT OR IGNORE INTO mensagens_marco VALUES (?,?)",
                (mensagem_id, marco_id))
    con.commit()


def marcos_da_mensagem(con, mensagem_id) -> list[str]:
    return [r["marco_id"] for r in con.execute(
        "SELECT marco_id FROM mensagens_marco WHERE mensagem_id=?", (mensagem_id,))]


# -------------------------------------------------------------- relatorio

def streak(con, usuario_id: int) -> tuple[int, int]:
    """(streak atual, recorde) de dias com o minimo registrado."""
    dias = [date.fromisoformat(r["dia"]) for r in con.execute(
        "SELECT dia FROM minimos WHERE usuario_id=? ORDER BY dia", (usuario_id,))]
    if not dias:
        return 0, 0

    melhor = atual = 1
    for anterior, seguinte in zip(dias, dias[1:]):
        atual = atual + 1 if (seguinte - anterior).days == 1 else 1
        melhor = max(melhor, atual)

    ultimo = dias[-1]
    ref = datetime.now(TZ).date()
    if (ref - ultimo).days > 1:      # quebrou
        atual = 0
    return atual, melhor


def periodo(dias: int) -> tuple[str, str]:
    fim = datetime.now(TZ).date()
    return (fim - timedelta(days=dias - 1)).isoformat(), fim.isoformat()


def resumo(con, desde: str, ate: str) -> dict:
    """Agregado do periodo, por pessoa e por materia."""
    voz = con.execute(
        "SELECT usuario, usuario_id, SUM(segundos) s, COUNT(*) n FROM sessoes_voz"
        " WHERE date(inicio) BETWEEN ? AND ? AND segundos IS NOT NULL"
        " GROUP BY usuario_id ORDER BY s DESC", (desde, ate)).fetchall()

    q_pessoa = con.execute(
        "SELECT usuario, usuario_id, SUM(feitas) f, SUM(acertos) a FROM questoes"
        " WHERE dia BETWEEN ? AND ? GROUP BY usuario_id ORDER BY f DESC",
        (desde, ate)).fetchall()

    q_materia = con.execute(
        "SELECT materia, SUM(feitas) f, SUM(acertos) a FROM questoes"
        " WHERE dia BETWEEN ? AND ? GROUP BY materia ORDER BY f DESC",
        (desde, ate)).fetchall()

    minimos = con.execute(
        "SELECT usuario, usuario_id, COUNT(*) n FROM minimos"
        " WHERE dia BETWEEN ? AND ? GROUP BY usuario_id", (desde, ate)).fetchall()

    erros = con.execute(
        "SELECT usuario, COUNT(*) n FROM erros WHERE dia BETWEEN ? AND ?"
        " GROUP BY usuario_id", (desde, ate)).fetchall()

    return {"voz": voz, "questoes_pessoa": q_pessoa, "questoes_materia": q_materia,
            "minimos": minimos, "erros": erros, "desde": desde, "ate": ate}


def migrar_estado_json(con, caminho: Path) -> int:
    """Traz o que existia no estado.json antigo. Roda uma vez, e idempotente."""
    if not caminho.exists():
        return 0
    import json
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    n = 0
    for marco_id, info in (dados.get("confirmados") or {}).items():
        em = info.get("em") if isinstance(info, dict) else str(info)
        con.execute("INSERT OR IGNORE INTO confirmacoes (marco_id, em) VALUES (?,?)",
                    (marco_id, em))
        n += 1
    con.commit()
    return n
