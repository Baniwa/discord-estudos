#!/usr/bin/env bash
# Copia o banco para fora do volume. Roda com o bot no ar: usa o `.backup` do
# sqlite, que e consistente mesmo com escrita acontecendo. Copiar o arquivo na
# mao com WAL ligado pode gerar um banco truncado.
#
# Uso:
#     bash backup.sh
#     bash backup.sh /caminho/destino

set -euo pipefail

DESTINO="${1:-$(dirname "$0")/backups}"
mkdir -p "$DESTINO"

ARQUIVO="$DESTINO/estudos-$(date +%Y-%m-%d-%H%M).db"

docker compose exec -T sentinela \
  python -c "import sqlite3,sys; o=sqlite3.connect('/dados/estudos.db'); d=sqlite3.connect('/tmp/bkp.db'); o.backup(d); d.close(); o.close()"

docker compose cp sentinela:/tmp/bkp.db "$ARQUIVO"
docker compose exec -T sentinela rm -f /tmp/bkp.db

echo "Backup: $ARQUIVO ($(du -h "$ARQUIVO" | cut -f1))"

# Mantem os 14 mais recentes. Historico de estudo e pequeno, mas nao ha razao
# para acumular sem fim numa VM free tier.
ls -1t "$DESTINO"/estudos-*.db 2>/dev/null | tail -n +15 | xargs -r rm --
echo "Backups guardados: $(ls -1 "$DESTINO"/estudos-*.db 2>/dev/null | wc -l)"
