"""Estrutura do servidor de estudos.

Fonte unica da verdade: o setup_servidor.py le daqui e cria o que faltar.
Editar aqui e rodar de novo e a forma certa de mudar o servidor - o script
e idempotente, entao nada e duplicado nem apagado.
"""

# --------------------------------------------------------------- cargos
#
# O servidor ja tinha uma identidade propria (Comand Maidens Dynasty, desde
# 02/2023) e ela fica. Nenhum cargo novo e criado: ⚔️ Maidens passa a ser o
# cargo das duas, e os outros dois ficam de pe pensando na hipotese de abrir
# o servidor para mais gente estudar mais adiante.
CARGOS_MANTER = ["⚔️ Maidens", "🛡️ Domain", "🧭 Outsider"]

CARGOS = []  # nada a criar

# Nota de desenho, para quando a ideia de abrir o servidor virar plano:
# a estrutura toda vive neste arquivo como DADO, nao como clique. Isso ja
# torna o repo um molde - outra pessoa clona, troca marcos.json e roda o
# setup no servidor dela. Manter assim.


# Estrutura de canais.
#   tipo: "voz" | "texto" | "forum"
#   somente_leitura: True -> @everyone nao posta (canal de referencia/bot)
#   tags: so para forum
ESTRUTURA = [
    {
        # As salas de voz NAO sao criadas: sao as quatro que ja existiam em
        # VOIP, renomeadas (ver REAPROVEITAR). Criar novas deixaria oito canais
        # de voz num servidor de duas pessoas.
        "categoria": "🔊 SALA DE ESTUDO",
        "proposito": "O coracao do servidor. Voz e o produto; texto e o arquivo.",
        "canais": [],
    },
    {
        "categoria": "🎯 COMANDO",
        "proposito": "O que se olha todo dia.",
        "canais": [
            {"tipo": "texto", "nome": "alvo", "somente_leitura": True,
             "topico": "SEFAZ Auditor de TI e o destino. TCDF > BB > ANPD > BACEN sao os degraus."},
            {"tipo": "texto", "nome": "metas-do-dia",
             "topico": "Uma linha, ANTES de comecar. O que vai fazer hoje."},
            {"tipo": "texto", "nome": "diario",
             "topico": "Fechamento do dia. Alimentado pelo webhook do vault."},
            {"tipo": "texto", "nome": "erros-do-dia",
             "topico": "O canal mais importante. Todo item errado entra aqui e vira card no Anki. "
                       "Dia sem mensagem aqui e dia que nao aconteceu."},
            {"tipo": "texto", "nome": "simulados",
             "topico": "So resultado por materia. Formato: data | simulado | materia | acertos/total | %"},
        ],
    },
    {
        "categoria": "📚 CONHECIMENTO",
        "proposito": "Foruns, um post por tema. Organizado por MATERIA, nunca por concurso - "
                     "concurso sem edital morre e leva o conhecimento junto.",
        "canais": [
            {"tipo": "forum", "nome": "nucleo-ti",
             "topico": "O que paga nos cinco alvos. Um post por tema, discussao dentro do post.",
             "tags": ["eng-software", "banco-de-dados", "redes-infra",
                      "seguranca", "governanca", "algoritmos"]},
            {"tipo": "forum", "nome": "auditoria-e-direito",
             "topico": "O que separa dev que sabe TI de auditor de TI.",
             "tags": ["auditoria-sistemas", "controles-riscos", "administrativo",
                      "tributario", "lgpd", "afo", "legislacao-df"]},
            {"tipo": "forum", "nome": "basicas",
             "topico": "Materias comuns a todos os alvos.",
             "tags": ["portugues", "rlm-estatistica", "ingles", "bancarios", "redacao"]},
            {"tipo": "texto", "nome": "aulas",
             "topico": "Aula assistida vai aqui, pelo /aula. Serve para a outra "
                       "saber onde voce esta na trilha, e para o relatorio separar "
                       "consumo de producao."},
            {"tipo": "forum", "nome": "duvidas",
             "topico": "Duvida assincrona. Perfis complementares (fullstack x frontend) - "
                       "e aqui que estudar em par rende mais.",
             "tags": ["aberta", "resolvida", "ti", "direito", "basicas"]},
        ],
    },
    {
        "categoria": "📋 LOGISTICA",
        "proposito": "Prazo, material e marco. Nada de conteudo de estudo aqui.",
        "canais": [
            {"tipo": "texto", "nome": "editais-e-prazos", "somente_leitura": True,
             "topico": "O bot posta aqui. SO FONTE PRIMARIA (DOU, orgao, banca). "
                       "Infografico de Instagram entra marcado como nao verificado."},
            {"tipo": "texto", "nome": "biblioteca",
             "topico": "PDFs, lei seca, links. Um link por mensagem, com a fonte."},
            {"tipo": "texto", "nome": "marcos",
             "topico": "Aprovacao, nota, streak fechado. O contrapeso do #erros-do-dia."},
        ],
    },
]


# --------------------------------------------- reconversao do que ja existia
#
# Caminho C: o servidor inteiro vira servidor de estudos. Nada e apagado -
# o que sai de cena vai para uma categoria de arquivo, e continua legivel.

# Canal existente que muda de nome e/ou de categoria.
#   de: nome exato hoje · para: nome novo (None = manter) · categoria: destino
REAPROVEITAR = [
    # As 4 salas de voz de VOIP viram as salas de estudo. Ja existem, tem
    # historico e ninguem precisa de oito canais de voz.
    {"de": "🛋 ┇ Salão Comunal", "para": "🔇 Estudo Silencioso",
     "categoria": "🔊 SALA DE ESTUDO",
     "motivo": "sala principal - mic e camera off, so presenca"},
    {"de": "🎶 ┇ Rádio 24/7", "para": "🍅 Pomodoro 25-5",
     "categoria": "🔊 SALA DE ESTUDO",
     "motivo": "o bot de radio sai; o espaco vira o ciclo 25/5"},
    {"de": "🎶 ┇ Música", "para": "🗣️ Discussão",
     "categoria": "🔊 SALA DE ESTUDO",
     "motivo": "mic on, para destravar questao"},
    {"de": "🛋 ┇ English Class", "para": "📺 Aula em grupo",
     "categoria": "🔊 SALA DE ESTUDO",
     "motivo": "sala para assistir aula junto; Ingles do BB cabe aqui tambem"},

    # Canal de curso que ja era do assunto.
    {"de": "📊┇analise-de-sistemas", "para": None,
     "categoria": "📚 CONHECIMENTO",
     "motivo": "ja e do tema - e o cargo da OTT dela"},

    # Erro de digitacao que estava la desde 2023, no canal vazio.
    {"de": "┇phyton", "para": "┇python", "categoria": None,
     "motivo": "grafia errada; canal vazio, entao renomear nao custa nada"},
]

# Fica exatamente como esta, so muda de dono do proposito.
MANTER = {
    "📓 CURSOS": "🇯🇵┇日本語 continua - idioma e treino, nao distracao",
    "👅 LINGUAGENS": "javascript, html-e-css, python, bash, linux: pratica de dev, "
                     "distinta da teoria de concurso que vive nos foruns",
    "☕ CYBER LOUNGE": "bate-papo, memes, img: descompressao. Servidor so de "
                      "cobranca nao dura",
    "📌 IMPORTANTE": "rules e boas-vindas ficam de pe pensando na hipotese de "
                     "abrir o servidor mais adiante",
}

# Vai para 🗄️ ARQUIVO. NUNCA apagado - historico de 3 anos nao se joga fora.
ARQUIVAR = [
    {"canal": "moderator-only", "motivo": "sem categoria, parado ha 26 meses"},
    {"canal": "┇saída", "motivo": "log do Loritta, parado ha 30 meses; o bot sai"},
    {"canal": "🌐┇advertisement", "motivo": "vazio, e nao ha o que anunciar"},
    {"canal": "🤖┇comandos", "motivo": "era dos bots que saem"},
]

# Categorias que sobram vazias depois do arquivamento.
CATEGORIAS_OBSOLETAS = ["👑 STAFF", "📝 Registros", "🤖 COMANDOS", "🔊 VOIP"]

CATEGORIA_ARQUIVO = "🗄️ ARQUIVO"


# Mensagem fixada em #alvo. Escrita uma vez, travada.
MENSAGEM_ALVO = """\
**O destino: Auditor de TI da SEFAZ-DF.**

Os quatro concursos abaixo nao sao alvos concorrentes. Sao degraus - cada um
cobra um pedaco do que o auditor de TI precisa saber, e cada aprovacao e uma
posicao melhor para esperar o edital que ainda nao saiu.

**A ordem, e ela nao muda:**

> `1.` **TCDF 2026** - prova 22/11/2026 - CEBRASPE - *edital lido na integra*
> `2.` **BB Agente de Tecnologia** - edital previsto 2o sem/2026
> `3.` **ANPD** - Especialista em Regulacao de Protecao de Dados - Brasilia
> `4.` **BACEN** - Tecnico / Auditor / Procurador

**Ate 22/11 o foco e o TCDF, sozinho.** Os outros tres se beneficiam do que
for estudado aqui - nao viram frente paralela.

**As tres materias de maior retorno**, porque pagam nos cinco alvos ao mesmo tempo:
Seguranca da Informacao · LGPD · Auditoria de Sistemas.

Auditoria de Sistemas e o unico 🔴 dentro de TI das duas - e e exatamente
o que define o destino.

*Quando bater duvida sobre por que estudar AFO, e este canal que responde.*
"""
