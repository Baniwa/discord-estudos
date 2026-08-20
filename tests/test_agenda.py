from datetime import date

from config.agenda import SEMANAS, bloco_do_dia, semana_de


def test_dia_util_cai_no_bloco_da_noite():
    segunda = date(2026, 8, 24)
    assert bloco_do_dia(segunda)["hora"] == "18h00 às 19h45"


def test_sabado_e_domingo_tem_bloco_proprio():
    sabado = date(2026, 8, 22)
    domingo = date(2026, 8, 23)
    assert bloco_do_dia(sabado)["hora"] == "09h30 às 12h30"
    assert bloco_do_dia(domingo)["hora"] == "09h30 às 11h30"
    assert bloco_do_dia(sabado)["hora"] != bloco_do_dia(domingo)["hora"]


def test_semana_do_plano_traz_rotulo_e_conteudo():
    inicio, _, rotulo, _ = SEMANAS[1]
    assert semana_de(inicio) == (rotulo, SEMANAS[1][3])


def test_data_fora_do_plano_nao_inventa_semana():
    assert semana_de(date(2030, 1, 1)) is None
    assert bloco_do_dia(date(2030, 1, 1))["rotulo"] == "Fora do plano"


def test_semanas_do_plano_nao_se_sobrepoem():
    for anterior, seguinte in zip(SEMANAS, SEMANAS[1:], strict=False):
        assert anterior[1] < seguinte[0]


def test_toda_semana_termina_depois_de_comecar():
    for inicio, fim, rotulo, _ in SEMANAS:
        assert inicio <= fim, rotulo
