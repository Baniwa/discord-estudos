"""Calendário de estudo, tirado do plano de 100 dias do cofre.

Fonte: concursos/tcdf-plano-100-dias.md, montado em 14/08/2026 com o edital
lido na íntegra. Não é extrapolação.

Se o plano do cofre mudar, muda aqui. Este arquivo é o que o bot lê para dizer
o conteúdo do dia, então divergir dele é pior que não ter.
"""

from datetime import date

# Blocos fixos da semana. O horário não se negocia, o conteúdo sim.
ROTINA = [
    {"dias": "Segunda a sexta", "hora": "18h00 às 19h45", "dur": "1h45",
     "estrutura": "20 min Português · 45 min conteúdo novo · 40 min questões CEBRASPE"},
    {"dias": "Sábado", "hora": "09h30 às 12h30", "dur": "3h",
     "estrutura": "Trilha da discursiva: peça técnica + revisão da semana"},
    {"dias": "Domingo", "hora": "09h30 às 11h30", "dur": "2h",
     "estrutura": "Simulado misto + Adm. Geral e Pública + revisão dos erros"},
]

MINIMO = ("Mínimo inegociável em dia ruim: 1 hora. "
          "30 min de conteúdo + 10 questões. Reduzir vale, pular não.")

# Semanas do plano. (inicio, fim, rotulo, conteudo)
SEMANAS = [
    (date(2026, 8, 14), date(2026, 8, 23), "Fase 0 — Fundação",
     "Manual de Redação do TCDF, edital em PDF, montar os 5 decks do Anki e "
     "1ª leitura da Lei Orgânica do DF. **Inscrição abre 26/08.**"),

    (date(2026, 8, 24), date(2026, 8, 30), "S1 — Direito Administrativo I",
     "Estado, governo e administração, fontes, princípios expressos e implícitos, "
     "regime jurídico-administrativo, **ato administrativo** (requisitos, atributos, "
     "espécies, extinção, convalidação) e **poderes** (hierárquico, disciplinar, "
     "regulamentar, polícia, uso e abuso)."),
    (date(2026, 8, 31), date(2026, 9, 6), "S2 — Direito Administrativo II",
     "**Agentes públicos**: cargo, emprego e função, provimento, vacância, "
     "estabilidade, remuneração, deveres, responsabilidades e PAD. Casado com a "
     "**LC 840/2011**, o regime jurídico dos servidores do DF."),
    (date(2026, 9, 7), date(2026, 9, 13), "S3 — Direito Administrativo III",
     "Responsabilidade civil do Estado, serviços públicos, organização "
     "administrativa, controle da administração, **improbidade (Lei 8.429)** e "
     "**Lei 9.784/1999**."),
    (date(2026, 9, 14), date(2026, 9, 20), "S4 — Licitações e contratos",
     "**Lei 14.133/2021**, Decreto distrital 44.330/2023 e gestão de contratos "
     "(IN 5/2017, fiscal e preposto, níveis de serviço, penalidades, reajuste "
     "versus repactuação). **Inscrição encerra 17/09 às 18h.**"),
    (date(2026, 9, 21), date(2026, 9, 27), "S5 — AFO I",
     "Orçamento público (conceito, técnicas, princípios, ciclo), **PPA, LDO e LOA**, "
     "classificações orçamentárias, estrutura programática e créditos adicionais."),
    (date(2026, 9, 28), date(2026, 10, 4), "S6 — AFO II",
     "Receita e despesa (conceitos, estágios, dívida ativa), **restos a pagar**, "
     "suprimento de fundos, **LRF (LC 101/2000)**, **Lei 4.320/1964** e Decreto "
     "distrital 32.598/2010."),

    (date(2026, 10, 5), date(2026, 10, 11), "S7 — Lei Orgânica do TCDF",
     "**LO do TCDF + Regimento Interno** (Res. 296/2016, arts. 1º a 116). "
     "A matéria da casa: lei seca curta, pouca gente estuda, retorno alto."),
    (date(2026, 10, 12), date(2026, 10, 18), "S8 — Constitucional dirigido",
     "Princípios fundamentais, aplicabilidade das normas, direitos e garantias, "
     "**administração pública (art. 37 a 41)**, poderes e **fiscalização contábil, "
     "financeira e orçamentária (art. 70 a 75)**. É revisão: as semanas 01 a 04 do "
     "plano antigo já cobriram parte."),
    (date(2026, 10, 19), date(2026, 10, 25), "S9 — Previdenciário e Civil",
     "Leis 8.212 e 8.213, **RPPS/DF (LC 769/2008)**, previdência complementar, e "
     "noções de Direito Civil (LINDB, pessoas, bens, negócio jurídico, prescrição "
     "e decadência)."),
    (date(2026, 10, 26), date(2026, 11, 1), "S10 — Tributário e Dados",
     "Noções de Direito Tributário (fontes, princípios, limitações ao poder de "
     "tributar, espécies de tributo) + **Análise de Dados, Estatística e IA** "
     "(descritiva, outliers, séries históricas, IA generativa, Excel e Power "
     "Query). Semana mais leve de propósito: o bloco de dados é terreno seu."),

    (date(2026, 11, 2), date(2026, 11, 8), "S11 — Português e LODF",
     "Português em profundidade (coesão, morfossintaxe, pontuação, concordância, "
     "regência, crase, reescrita) + **Lei Orgânica do DF**, agora cobrando."),
    (date(2026, 11, 9), date(2026, 11, 15), "S12 — DF, Socorros e RLM",
     "Conhecimentos do DF e Política para Mulheres (RIDE, Plano Distrital, Lei "
     "Maria da Penha) + **Primeiros Socorros** (o conteúdo mais curto do edital, "
     "pontos baratos) + RLM e Matemática Financeira."),
    (date(2026, 11, 16), date(2026, 11, 22), "S13 — Reta final",
     "2 simulados completos cronometrados (150 itens, 4h), revisão só dos erros e "
     "releitura de lei seca (LO TCDF, LC 840, LODF, 14.133). "
     "**Prova domingo, 22/11.**"),
]


def semana_de(quando: date):
    """(rotulo, conteudo) da semana, ou None se estiver fora do plano."""
    for inicio, fim, rotulo, conteudo in SEMANAS:
        if inicio <= quando <= fim:
            return rotulo, conteudo
    return None


def bloco_do_dia(quando: date) -> dict:
    """O bloco de hoje: horário, estrutura e o que estudar."""
    dia = quando.weekday()
    if dia <= 4:
        base = ROTINA[0]
    elif dia == 5:
        base = ROTINA[1]
    else:
        base = ROTINA[2]
    semana = semana_de(quando)
    return {"hora": base["hora"], "dur": base["dur"], "estrutura": base["estrutura"],
            "rotulo": semana[0] if semana else "Fora do plano",
            "conteudo": semana[1] if semana else "Sem semana definida para esta data."}
