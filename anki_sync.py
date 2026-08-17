"""Entrega ao Anki os cards que o bot enfileirou.

Dois caminhos, nesta ordem:

  1. AnkiConnect (add-on, API local em 127.0.0.1:8765). Empurra direto para a
     coleção aberta. Exige o Anki de desktop rodando na mesma máquina.
  2. Arquivo .apkg (genanki). Gera um pacote para importar à mão. Funciona sem
     Anki instalado, e serve para quem usa AnkiWeb ou celular.

A fila mora no banco do bot, então o Anki pode ficar dias fechado sem perder
nada. Card só é marcado como entregue depois que a entrega deu certo.

Uso:
    python anki_sync.py                 # detecta o AnkiConnect, senão exporta
    python anki_sync.py --apkg          # força o .apkg
    python anki_sync.py --status        # só mostra a fila
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).parent
sys.path.insert(0, str(RAIZ))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import db  # noqa: E402

ANKICONNECT = "http://127.0.0.1:8765"
BARALHO_RAIZ = "TCDF"

# Os 5 decks do plano de 100 dias. Matéria que não casar cai em Específicos.
MAPA_DECK = {
    "administrativo": "Administrativo", "adm": "Administrativo",
    "afo": "AFO", "orcamento": "AFO",
    "lodf": "Lei local", "lei local": "Lei local", "lc840": "Lei local",
    "portugues": "Português", "português": "Português", "redacao": "Português",
    "constitucional": "Específicos", "auditoria": "Específicos",
    "lgpd": "Específicos", "seguranca": "Específicos", "ti": "Específicos",
}


def deck_de(materia: str) -> str:
    return f"{BARALHO_RAIZ}::{MAPA_DECK.get(materia.lower().strip(), 'Específicos')}"


# ------------------------------------------------------------ AnkiConnect

def anki(acao: str, **params):
    corpo = json.dumps({"action": acao, "version": 6, "params": params}).encode()
    req = urllib.request.Request(ANKICONNECT, data=corpo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        resposta = json.loads(r.read())
    if resposta.get("error"):
        raise RuntimeError(resposta["error"])
    return resposta.get("result")


def anki_disponivel() -> bool:
    try:
        anki("version")
        return True
    except (urllib.error.URLError, OSError, RuntimeError, TimeoutError):
        return False


def modelo_basico() -> tuple[str, str, str]:
    """(modelo, campo_frente, campo_verso), descobertos na coleção.

    Não dá para chumbar "Basic"/"Front"/"Back": numa instalação em português o
    tipo de nota chama "Básico" com campos "Frente" e "Verso", e o addNote
    falha com `model was not found`. Foi o que aconteceu no primeiro teste.
    """
    nomes = anki("modelNames")
    preferidos = ["Básico", "Basic", "Basico"]
    escolhido = next((p for p in preferidos if p in nomes), None)

    if escolhido is None:  # último recurso: o primeiro com exatamente 2 campos
        for n in nomes:
            if len(anki("modelFieldNames", modelName=n)) == 2:
                escolhido = n
                break
    if escolhido is None:
        raise RuntimeError(f"nenhum tipo de nota de 2 campos na coleção: {nomes}")

    campos = anki("modelFieldNames", modelName=escolhido)
    return escolhido, campos[0], campos[1]


def enviar_por_ankiconnect(con, pendentes) -> int:
    for deck in {deck_de(c["materia"]) for c in pendentes}:
        anki("createDeck", deck=deck)

    modelo, campo_frente, campo_verso = modelo_basico()
    print(f"  (tipo de nota: {modelo} · campos {campo_frente}/{campo_verso})")

    enviados = []
    for c in pendentes:
        nota = {
            "deckName": deck_de(c["materia"]),
            "modelName": modelo,
            "fields": {campo_frente: c["frente"], campo_verso: c["verso"]},
            "tags": ["discord", c["materia"], c["usuario"]],
            "options": {"allowDuplicate": False,
                        "duplicateScope": "deck"},
        }
        try:
            anki("addNote", note=nota)
            enviados.append(c["id"])
            print(f"  + [{c['materia']}] {c['frente'][:52]}")
        except RuntimeError as e:
            # Duplicata não é falha: o card já está lá, então a fila pode
            # seguir. Qualquer outro erro para, para não marcar entregue algo
            # que não entrou.
            if "duplicate" in str(e).lower():
                enviados.append(c["id"])
                print(f"  = já existia: {c['frente'][:44]}")
            else:
                print(f"  ! falhou: {c['frente'][:40]} — {e}")

    if enviados:
        db.marcar_entregue(con, enviados, "ankiconnect")
    return len(enviados)


# ------------------------------------------------------------- estatística

def limpar_html(texto: str) -> str:
    """A frente do card vem com HTML do editor do Anki."""
    import html
    import re
    return html.unescape(re.sub(r"<[^>]+>", " ", texto)).strip()


def coletar_stats(con) -> dict:
    """Traz do Anki o que o bot não consegue saber sozinho: o que ela revisou
    e, principalmente, o que ela erra de novo e de novo.

    O número que muda decisão é `lapses`. Card com muito lapso é conceito que
    não gruda, e é o único sinal do Anki que diz o que estudar na semana
    seguinte. Acerto alto não muda nada.
    """
    decks = [d for d in anki("deckNames") if d.startswith(BARALHO_RAIZ)]
    if not decks:
        return {"decks": 0, "dificeis": 0, "revisados_hoje": 0}

    stats = anki("getDeckStats", decks=decks)
    revisados = anki("getNumCardsReviewedToday")

    linhas = []
    for info in stats.values():
        linhas.append({
            "deck": info.get("name", "?"),
            "novos": info.get("new_count", 0),
            "aprender": info.get("learn_count", 0),
            "revisar": info.get("review_count", 0),
            # revisados_hoje é da coleção toda, não por deck. Fica no primeiro
            # deck para a soma do período não multiplicar pelo nº de decks.
            "revisados_hoje": 0,
        })
    if linhas:
        linhas[0]["revisados_hoje"] = revisados
    db.gravar_snapshot_anki(con, linhas)

    ids = anki("findCards", query=f"deck:{BARALHO_RAIZ} prop:lapses>=2")
    dificeis = []
    if ids:
        for c in anki("cardsInfo", cards=ids):
            frente = next(iter(c.get("fields", {}).values()), {}).get("value", "")
            dificeis.append({
                "card_id": c["cardId"], "deck": c["deckName"],
                "frente": limpar_html(frente)[:180],
                "lapses": c["lapses"], "facilidade": c["factor"],
                "intervalo": c["interval"],
            })
        db.gravar_dificeis(con, dificeis)

    return {"decks": len(linhas), "dificeis": len(dificeis),
            "revisados_hoje": revisados}


# ------------------------------------------------------------------ .apkg

def exportar_apkg(con, pendentes) -> Path:
    import genanki

    modelo = genanki.Model(
        1607392319, "Básico (discord-estudos)",
        fields=[{"name": "Front"}, {"name": "Back"}],
        templates=[{"name": "Card 1",
                    "qfmt": "{{Front}}",
                    "afmt": "{{FrontSide}}<hr id=answer>{{Back}}"}])

    por_deck: dict[str, list] = {}
    for c in pendentes:
        por_deck.setdefault(deck_de(c["materia"]), []).append(c)

    decks = []
    for nome, cards in por_deck.items():
        d = genanki.Deck(abs(hash(nome)) % (10 ** 10), nome)
        for c in cards:
            d.add_note(genanki.Note(
                model=modelo, fields=[c["frente"], c["verso"]],
                tags=["discord", c["materia"]]))
        decks.append(d)
        print(f"  {nome}: {len(cards)} card(s)")

    saida = RAIZ / f"anki-{datetime.now():%Y-%m-%d-%H%M}.apkg"
    genanki.Package(decks).write_to_file(saida)
    db.marcar_entregue(con, [c["id"] for c in pendentes], f"apkg:{saida.name}")
    return saida


# ------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apkg", action="store_true", help="força exportar .apkg")
    ap.add_argument("--status", action="store_true", help="só mostra a fila")
    args = ap.parse_args()

    con = db.conectar()
    pendentes = db.cards_pendentes(con)

    # A coleta roda sempre que o Anki estiver aberto, mesmo sem card na fila:
    # é o que mantém o relatório com dado fresco quando o Anki fecha.
    if not args.apkg and anki_disponivel():
        s = coletar_stats(con)
        print(f"Anki lido: {s['decks']} deck(s) · {s['revisados_hoje']} revisão(ões) "
              f"hoje · {s['dificeis']} card(s) difícil(eis).")

    if args.status or not pendentes:
        print(f"\nFila: {len(pendentes)} card(s) pendente(s).")
        por_materia: dict[str, int] = {}
        for c in pendentes:
            por_materia[c["materia"]] = por_materia.get(c["materia"], 0) + 1
        for m, n in sorted(por_materia.items(), key=lambda x: -x[1]):
            print(f"  {m:<20} {n}")
        entregues = con.execute(
            "SELECT COUNT(*) n FROM cards WHERE entregue_em IS NOT NULL").fetchone()
        print(f"Já entregues: {entregues['n']}")
        if args.status or not pendentes:
            return

    print(f"\n{len(pendentes)} card(s) na fila.")

    if not args.apkg and anki_disponivel():
        print("AnkiConnect respondeu. Enviando direto para a coleção aberta.\n")
        n = enviar_por_ankiconnect(con, pendentes)
        print(f"\n{n} card(s) entregues.")
        return

    if not args.apkg:
        print("AnkiConnect não respondeu (Anki fechado ou add-on ausente).")
        print("Gerando .apkg para importar à mão.\n")

    saida = exportar_apkg(con, pendentes)
    print(f"\nArquivo: {saida}")
    print("Importe no Anki com Arquivo > Importar.")


if __name__ == "__main__":
    main()
