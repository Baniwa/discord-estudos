import sqlite3
from datetime import date, datetime, timedelta

import db


def marcar_minimo_em(con, usuario_id, dias: list[date]):
    con.executemany(
        "INSERT INTO minimos (usuario_id, usuario, dia, registrado) VALUES (?,?,?,?)",
        [(usuario_id, "Alguém", d.isoformat(), d.isoformat()) for d in dias])
    con.commit()


def test_conectar_liga_o_wal(con):
    modo = con.execute("PRAGMA journal_mode").fetchone()[0]
    assert modo.lower() == "wal"


def test_conectar_duas_vezes_nao_quebra(con, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "ARQUIVO", tmp_path / "estudos.db")
    outra = db.conectar()
    assert outra.execute("SELECT COUNT(*) FROM sessoes_voz").fetchone()[0] == 0
    outra.close()


# ------------------------------------------------------------------- sessoes

def test_entrar_duas_vezes_nao_abre_duas_sessoes(con):
    db.abrir_sessao(con, 1, "Alguém", "Estudo Silencioso")
    db.abrir_sessao(con, 1, "Alguém", "Estudo Silencioso")
    abertas = con.execute(
        "SELECT COUNT(*) FROM sessoes_voz WHERE fim IS NULL").fetchone()[0]
    assert abertas == 1


def test_fechar_sessao_inexistente_devolve_zero(con):
    assert db.fechar_sessao(con, 999) == 0


def test_orfa_e_fechada_com_teto_de_quatro_horas(con):
    inicio = datetime.now(db.TZ) - timedelta(hours=10)
    con.execute(
        "INSERT INTO sessoes_voz (usuario_id, usuario, canal, inicio) VALUES (?,?,?,?)",
        (1, "Alguém", "Estudo Silencioso", inicio.isoformat()))
    con.commit()

    assert db.fechar_orfas(con) == 1
    segundos = con.execute("SELECT segundos FROM sessoes_voz").fetchone()[0]
    assert segundos == 4 * 3600


def test_orfa_de_quem_esta_em_call_fica_aberta(con):
    db.abrir_sessao(con, 1, "Fica", "Estudo Silencioso")
    db.abrir_sessao(con, 2, "Sai", "Estudo Silencioso")

    assert db.fechar_orfas(con, preservar={1}) == 1
    abertas = [linha["usuario_id"] for linha in con.execute(
        "SELECT usuario_id FROM sessoes_voz WHERE fim IS NULL")]
    assert abertas == [1]


# ------------------------------------------------------------------- minimo

def test_minimo_vale_uma_vez_por_dia(con):
    assert db.registrar_minimo(con, 1, "Alguém") is True
    assert db.registrar_minimo(con, 1, "Alguém") is False


def test_streak_conta_dias_seguidos_e_guarda_o_recorde(con):
    hoje = datetime.now(db.TZ).date()
    seguidos = [hoje - timedelta(days=n) for n in range(3)]
    antigos = [hoje - timedelta(days=n) for n in (20, 19, 18, 17, 16)]
    marcar_minimo_em(con, 1, sorted(antigos + seguidos))

    atual, recorde = db.streak(con, 1)
    assert (atual, recorde) == (3, 5)


def test_streak_quebra_quando_o_ultimo_dia_e_velho(con):
    hoje = datetime.now(db.TZ).date()
    marcar_minimo_em(con, 1, [hoje - timedelta(days=n) for n in (5, 4, 3)])

    atual, recorde = db.streak(con, 1)
    assert atual == 0
    assert recorde == 3


def test_streak_de_quem_nunca_registrou(con):
    assert db.streak(con, 1) == (0, 0)


# -------------------------------------------------------------- erros e cards

def test_dois_erros_sem_mensagem_contam_os_dois(con):
    db.registrar_erro(con, 1, "Alguém", None)
    db.registrar_erro(con, 1, "Alguém", None)
    assert con.execute("SELECT COUNT(*) FROM erros").fetchone()[0] == 2


def test_erro_da_mesma_mensagem_conta_uma_vez(con):
    db.registrar_erro(con, 1, "Alguém", 42)
    db.registrar_erro(con, 1, "Alguém", 42)
    assert con.execute("SELECT COUNT(*) FROM erros").fetchone()[0] == 1


def test_card_da_mesma_mensagem_nao_duplica(con):
    primeiro = db.enfileirar_card(con, 1, "Alguém", "adm", "frente", "verso",
                                  mensagem_id=7)
    repetido = db.enfileirar_card(con, 1, "Alguém", "adm", "frente", "verso",
                                  mensagem_id=7)
    assert primeiro is not None
    assert repetido is None


def test_card_entregue_sai_da_fila(con):
    card = db.enfileirar_card(con, 1, "Alguém", "AFO ", "frente", "verso")
    assert [linha["materia"] for linha in db.cards_pendentes(con)] == ["afo"]

    db.marcar_entregue(con, [card], "TCDF::AFO")
    assert db.cards_pendentes(con) == []


# ------------------------------------------------------------- fechamento

def test_agregar_dia_nao_grava_nada(con):
    db.registrar_questoes(con, 1, "Alguém", "Administrativo", 20, 13)
    hoje = db.hoje()

    agregado = db.agregar_dia(con, hoje)

    assert agregado[0]["questoes"] == 20
    assert con.execute("SELECT COUNT(*) FROM log_diario").fetchone()[0] == 0


def test_fechar_dia_e_idempotente(con):
    db.registrar_questoes(con, 1, "Alguém", "Administrativo", 20, 13)
    hoje = db.hoje()

    db.fechar_dia(con, hoje, "S1")
    db.fechar_dia(con, hoje, "S1")

    linhas = con.execute("SELECT questoes FROM log_diario").fetchall()
    assert len(linhas) == 1
    assert linhas[0]["questoes"] == 20


def test_fechar_dia_junta_as_fontes_da_mesma_pessoa(con):
    db.registrar_questoes(con, 1, "Alguém", "Administrativo", 10, 7)
    db.registrar_aula(con, 1, "Alguém", "AFO", None, "Aula 3", 45)
    db.registrar_minimo(con, 1, "Alguém")
    db.enfileirar_card(con, 1, "Alguém", "adm", "frente", "verso")
    db.registrar_erro(con, 1, "Alguém", None)

    pessoa = db.fechar_dia(con, db.hoje(), "S1")[0]

    assert pessoa["questoes"] == 10
    assert pessoa["aulas"] == 1
    assert pessoa["minutos_aula"] == 45
    assert pessoa["cards"] == 1
    assert pessoa["erros"] == 1
    assert pessoa["minimo"] == 1


def test_adesao_conta_os_dias_ja_fechados(con):
    db.registrar_minimo(con, 1, "Alguém")
    hoje = db.hoje()
    db.fechar_dia(con, hoje, "S1")

    linha = db.adesao(con, hoje, hoje)[0]
    assert linha["dias_com_minimo"] == 1
    assert linha["dias_com_log"] == 1


# ------------------------------------------------------------------ materias

def test_materias_junta_as_tres_origens(con):
    db.registrar_questoes(con, 1, "Alguém", "Administrativo", 10, 7)
    db.enfileirar_card(con, 1, "Alguém", "Redes", "frente", "verso")
    db.registrar_aula(con, 1, "Alguém", "AFO", None, "Aula 3", 45)

    assert sorted(db.materias(con)) == ["administrativo", "afo", "redes"]


def test_materias_vem_da_mais_usada_para_a_menos(con):
    for _ in range(3):
        db.registrar_questoes(con, 1, "Alguém", "administrativo", 10, 7)
    db.registrar_questoes(con, 1, "Alguém", "redes", 10, 7)

    assert db.materias(con)[0] == "administrativo"


def test_materias_filtra_pelo_que_ja_foi_digitado(con):
    db.registrar_questoes(con, 1, "Alguém", "administrativo", 10, 7)
    db.registrar_questoes(con, 1, "Alguém", "redes", 10, 7)

    assert db.materias(con, "ADM") == ["administrativo"]


def test_materias_de_banco_vazio(con):
    assert db.materias(con) == []


# ----------------------------------------------------------------- simulados

def test_simulado_aberto_guarda_o_fim_previsto(con):
    db.abrir_simulado(con, 1, "Alguém", "CEBRASPE ", 210)

    aberto = db.simulado_aberto_de(con, 1)
    inicio = datetime.fromisoformat(aberto["inicio"])
    fim = datetime.fromisoformat(aberto["fim_previsto"])

    assert aberto["materia"] == "cebraspe"
    assert round((fim - inicio).total_seconds() / 60) == 210


def test_simulado_encerrado_sai_da_lista_de_abertos(con):
    simulado = db.abrir_simulado(con, 1, "Alguém", "cebraspe", 60)
    assert len(db.simulados_abertos(con)) == 1

    db.encerrar_simulado(con, simulado)
    assert db.simulados_abertos(con) == []
    assert db.simulado_aberto_de(con, 1) is None


def test_aviso_dado_fica_gravado_e_nao_duplica(con):
    simulado = db.abrir_simulado(con, 1, "Alguém", "cebraspe", 210)

    db.marcar_aviso(con, simulado, ["metade"])
    db.marcar_aviso(con, simulado, ["metade", "30"])

    avisos = db.simulados_abertos(con)[0]["avisos"]
    assert avisos.split(",") == ["metade", "30"]


def test_resultado_fecha_o_simulado_e_grava_a_nota(con):
    simulado = db.abrir_simulado(con, 1, "Alguém", "cebraspe", 210)

    db.registrar_resultado(con, simulado, 84, 120)

    assert db.simulados_abertos(con) == []
    assert db.simulado_sem_resultado(con, 1) is None
    linha = db.simulados_periodo(con, db.hoje(), db.hoje())[0]
    assert (linha["acertos"], linha["total"]) == (84, 120)


def test_simulado_sem_nota_e_o_que_o_resultado_procura(con):
    antigo = db.abrir_simulado(con, 1, "Alguém", "administrativo", 60)
    db.registrar_resultado(con, antigo, 10, 20)
    novo = db.abrir_simulado(con, 1, "Alguém", "cebraspe", 210)

    assert db.simulado_sem_resultado(con, 1)["id"] == novo


def test_simulado_sem_nota_nao_entra_no_relatorio(con):
    db.abrir_simulado(con, 1, "Alguém", "cebraspe", 210)
    assert db.simulados_periodo(con, db.hoje(), db.hoje()) == []


def test_materia_de_simulado_alimenta_o_autocomplete(con):
    db.abrir_simulado(con, 1, "Alguém", "cebraspe", 210)
    assert db.materias(con, "cebr") == ["cebraspe"]


# ------------------------------------------------------------------ migracao

def test_migracao_acrescenta_coluna_em_banco_que_ja_existia(tmp_path, monkeypatch):
    arquivo = tmp_path / "antigo.db"
    antigo = sqlite3.connect(arquivo)
    antigo.execute(
        "CREATE TABLE log_diario ("
        " dia TEXT NOT NULL, usuario_id INTEGER NOT NULL, usuario TEXT NOT NULL,"
        " semana TEXT, segundos_voz INTEGER NOT NULL DEFAULT 0,"
        " questoes INTEGER NOT NULL DEFAULT 0, acertos INTEGER NOT NULL DEFAULT 0,"
        " erros INTEGER NOT NULL DEFAULT 0, cards INTEGER NOT NULL DEFAULT 0,"
        " minimo INTEGER NOT NULL DEFAULT 0, fechado_em TEXT NOT NULL,"
        " PRIMARY KEY (dia, usuario_id))")
    antigo.execute(
        "INSERT INTO log_diario (dia, usuario_id, usuario, fechado_em)"
        " VALUES ('2026-08-17', 1, 'Alguém', '2026-08-18T02:00:00')")
    antigo.commit()
    antigo.close()

    monkeypatch.setattr(db, "ARQUIVO", arquivo)
    con = db.conectar()

    colunas = {linha["name"] for linha in
               con.execute("SELECT name FROM pragma_table_info('log_diario')")}
    assert {"aulas", "minutos_aula"} <= colunas
    assert con.execute("SELECT COUNT(*) FROM log_diario").fetchone()[0] == 1
    con.close()


def test_periodo_inclui_as_duas_pontas(con):
    desde, ate = db.periodo(7)
    assert (date.fromisoformat(ate) - date.fromisoformat(desde)).days == 6
    assert ate == db.hoje()
