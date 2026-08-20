from datetime import datetime, timedelta

import pytest

import db
import sentinela


@pytest.fixture
def bot_com_banco(con, monkeypatch):
    monkeypatch.setattr(sentinela, "con", con)
    return con


def campos(embed) -> list[str]:
    return [campo.name for campo in embed.fields]


def texto(embed) -> str:
    return " ".join([embed.title or "", embed.description or ""] +
                    [f"{c.name} {c.value}" for c in embed.fields] +
                    [embed.footer.text or ""])


# -------------------------------------------------------------- formatadores

@pytest.mark.parametrize("segundos, esperado", [
    (0, "0min"), (59, "0min"), (600, "10min"), (3600, "1h00"), (5400, "1h30"),
])
def test_hm_formata_a_duracao(segundos, esperado):
    assert sentinela.hm(segundos) == esperado


@pytest.mark.parametrize("dias, trecho", [
    (-2, "passou há 2"), (0, "HOJE"), (1, "AMANHÃ"), (9, "9 dias"),
])
def test_texto_dias_fala_a_distancia(dias, trecho):
    assert trecho in sentinela.texto_dias(dias)


def test_farol_cobra_marco_critico_mais_cedo():
    assert sentinela.farol(5, critico=True)[0] == "🔴"
    assert sentinela.farol(5, critico=False)[0] == "🟡"
    assert sentinela.farol(-1, critico=True)[0] == "⚫"
    assert sentinela.farol(40, critico=True)[0] == "🟢"


def test_resumir_corta_sem_partir_palavra():
    assert sentinela.resumir("uma frase curta", 40) == "uma frase curta"
    cortado = sentinela.resumir("uma frase bem mais longa do que cabe", 20)
    assert cortado.endswith("…")
    assert len(cortado) <= 21


# ------------------------------------------------------------------- prazos

def test_marco_de_fonte_secundaria_nao_entra_na_contagem(bot_com_banco):
    verificados = {c["nome"] for c in sentinela.CONFIG["concursos"]
                   if c.get("verificado")}
    for marco in sentinela.marcos_ativos():
        assert marco["concurso"] in verificados


def test_marco_confirmado_some_da_cobranca(bot_com_banco):
    antes = sentinela.marcos_ativos()
    if not antes:
        pytest.skip("nenhum marco ativo no marcos.json")

    db.confirmar_marco(bot_com_banco, antes[0]["id"], 1, "Alguém")
    depois = [m["id"] for m in sentinela.marcos_ativos()]
    assert antes[0]["id"] not in depois


def test_briefing_separa_o_que_tem_edital_do_que_nao_tem(bot_com_banco):
    em, _ = sentinela.montar_briefing()
    assert "fonte secundária" in " ".join(campos(em)).lower()


# -------------------------------------------------------------------- bloco

def test_bloco_traz_horario_conteudo_e_minimo():
    dia = datetime.now(sentinela.TZ).date()
    em = sentinela.montar_bloco(dia, "Bloco de hoje")

    assert em.title.startswith("Bloco de hoje")
    assert "Estrutura" in campos(em)
    assert "Mínimo inegociável" in em.footer.text


# ---------------------------------------------------------------- log do dia

def test_log_parcial_de_dia_vazio_nao_e_vermelho():
    dia = datetime.now(sentinela.TZ).date()
    em = sentinela.montar_log_diario(dia, [], parcial=True)

    assert em.colour.value != 0xED4245
    assert "Ainda sem registro" in campos(em)[0]


def test_log_fechado_de_dia_vazio_e_vermelho():
    ontem = datetime.now(sentinela.TZ).date() - timedelta(days=1)
    em = sentinela.montar_log_diario(ontem, [])

    assert em.colour.value == 0xED4245
    assert "Dia sem registro" in campos(em)[0]
    assert "previsto" in texto(em)


def test_log_com_registro_mostra_uma_coluna_por_pessoa(bot_com_banco):
    db.registrar_questoes(bot_com_banco, 1, "Alguém", "administrativo", 20, 13)
    dia = datetime.now(sentinela.TZ).date()

    pessoas = db.agregar_dia(bot_com_banco, dia.isoformat())
    em = sentinela.montar_log_diario(dia, pessoas, parcial=True)

    assert "Alguém" in campos(em)
    assert "13/20" in texto(em)


# ----------------------------------------------------------------- relatorio

def test_relatorio_de_periodo_vazio_ainda_monta(bot_com_banco):
    em = sentinela.montar_relatorio(7, "Relatório da semana")
    assert "Nenhuma sessão no período" in texto(em)


def test_relatorio_poe_a_pior_materia_no_topo(bot_com_banco):
    db.registrar_questoes(bot_com_banco, 1, "Alguém", "administrativo", 10, 9)
    db.registrar_questoes(bot_com_banco, 1, "Alguém", "redes", 10, 2)

    em = sentinela.montar_relatorio(7, "Relatório da semana")
    por_materia = next(c.value for c in em.fields if "matéria" in c.name)

    assert por_materia.index("redes") < por_materia.index("administrativo")


def test_relatorio_avisa_quando_ha_aula_demais_e_questao_de_menos(bot_com_banco):
    db.registrar_aula(bot_com_banco, 1, "Alguém", "afo", None, "Aula 1", 180)
    db.registrar_questoes(bot_com_banco, 1, "Alguém", "afo", 5, 4)

    em = sentinela.montar_relatorio(7, "Relatório da semana")
    assert "pouca questão" in texto(em)


def test_relatorio_diz_que_aula_e_call_nao_somam(bot_com_banco):
    db.registrar_aula(bot_com_banco, 1, "Alguém", "afo", None, "Aula 1", 45)

    em = sentinela.montar_relatorio(7, "Relatório da semana")
    assert "não somam" in texto(em).lower()


# -------------------------------------------------------------------- adesao

def test_adesao_conta_a_semana_corrente(bot_com_banco):
    db.registrar_minimo(bot_com_banco, 1, "Alguém")
    db.fechar_dia(bot_com_banco, db.hoje(), "S1")

    em = sentinela.montar_adesao()
    assert "No plano inteiro" in campos(em)
    assert "Alguém" in texto(em)


def test_adesao_avisa_quando_o_plano_ainda_nao_comecou(bot_com_banco, monkeypatch):
    futuro = [(inicio + timedelta(days=3650), fim + timedelta(days=3650), rotulo, txt)
              for inicio, fim, rotulo, txt in sentinela.SEMANAS]
    monkeypatch.setattr(sentinela, "SEMANAS", futuro)

    em = sentinela.montar_adesao()
    assert "O plano começa em" in em.description


# ------------------------------------------------------------------ comandos

def test_a_arvore_registra_os_comandos_publicados():
    nomes = {c.name for c in sentinela.bot.tree.get_commands()}
    assert nomes == {"prazos", "relatorio", "agora", "estudei", "erro", "anki",
                     "aula", "questoes", "bloco", "hoje", "adesao"}
