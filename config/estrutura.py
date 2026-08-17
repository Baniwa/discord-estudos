"""Estrutura do servidor de estudos.

Fonte unica da verdade: o setup_servidor.py le daqui e cria o que faltar.
Editar aqui e rodar de novo e a forma certa de mudar o servidor - o script
e idempotente, entao nada e duplicado nem apagado.
"""

# Cargos. Servidor de duas pessoas nao precisa de hierarquia -
# os cargos existem so para mencao e para separar o bot.
CARGOS = [
    {"nome": "concurseira", "cor": 0xFEE75C, "hoist": True,
     "motivo": "Giulia e Larissa. Mencionavel para puxar a outra pro estudo silencioso."},
    {"nome": "bot", "cor": 0x5865F2, "hoist": False,
     "motivo": "Sentinela de Prazos."},
]


# Estrutura de canais.
#   tipo: "voz" | "texto" | "forum"
#   somente_leitura: True -> @everyone nao posta (canal de referencia/bot)
#   tags: so para forum
ESTRUTURA = [
    {
        "categoria": "🔊 SALA DE ESTUDO",
        "proposito": "O coracao do servidor. Voz e o produto; texto e o arquivo.",
        "canais": [
            {"tipo": "voz", "nome": "🔇 Estudo Silencioso",
             "topico": "Mic e camera OFF. Regra unica: entrou, esta estudando."},
            {"tipo": "voz", "nome": "🍅 Pomodoro 25-5",
             "topico": "Ciclo 25 min foco / 5 min pausa."},
            {"tipo": "voz", "nome": "🗣️ Discussao",
             "topico": "Mic ON. Para destravar questao, nao para conversar."},
        ],
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
