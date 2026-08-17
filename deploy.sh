#!/usr/bin/env bash
# Sobe ou atualiza o bot na VM. Idempotente: rodar de novo so aplica a
# diferenca.
#
# Uso, de dentro da pasta do projeto na VM:
#     bash deploy.sh
#
# Primeira vez, ver DEPLOY.md.

set -euo pipefail

cd "$(dirname "$0")"

echo "==> Conferindo pre-requisitos"
command -v docker >/dev/null || { echo "docker nao encontrado. Ver DEPLOY.md"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "docker compose v2 nao encontrado"; exit 1; }

if [ ! -f .env ]; then
  echo "ERRO: .env nao existe. Copie o .env.example e preencha o token."
  exit 1
fi

# O token nunca aparece na saida; so confirmamos que existe.
if ! grep -q '^DISCORD_BOT_TOKEN=.\+' .env; then
  echo "ERRO: DISCORD_BOT_TOKEN vazio no .env."
  exit 1
fi

echo "==> Trazendo a versao mais recente"
if [ -d .git ]; then
  git fetch --quiet origin
  git checkout --quiet main
  git pull --quiet --ff-only origin main
  echo "    $(git log -1 --format='%h %s')"
fi

echo "==> Construindo a imagem"
docker compose build

echo "==> Subindo"
docker compose up -d

echo "==> Aguardando o bot conectar"
sleep 8
docker compose logs --tail 20 sentinela

echo
echo "==> Estado"
docker compose ps

cat <<'FIM'

Pronto.

  Acompanhar em tempo real : docker compose logs -f sentinela
  Reiniciar                : docker compose restart sentinela
  Parar                    : docker compose down
  Backup do banco          : bash backup.sh

O banco fica num volume Docker, entao `down` NAO apaga o historico.
FIM
