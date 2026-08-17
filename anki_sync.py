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


def enviar_por_ankiconnect(con, pendentes) -> int:
    for deck in {deck_de(c["materia"]) for c in pendentes}:
        anki("createDeck", deck=deck)

    enviados = []
    for c in pendentes:
        nota = {
            "deckName": deck_de(c["materia"]),
            "modelName": "Basic",
            "fields": {"Front": c["frente"], "Back": c["verso"]},
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
