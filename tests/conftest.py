import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# Definido antes de qualquer import de db ou sentinela: os dois resolvem o
# caminho do banco no import, e sem isto o teste escreveria no estudos.db real.
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "teste.db")
os.environ.setdefault("DISCORD_TOKEN", "token-de-teste")

import pytest  # noqa: E402

import db  # noqa: E402


@pytest.fixture
def con(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "ARQUIVO", tmp_path / "estudos.db")
    conexao = db.conectar()
    yield conexao
    conexao.close()
