# Testes

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check .
```

Roda sem token, sem Discord e sem Anki. Nenhum teste toca o `estudos.db` real: o
`conftest.py` aponta `DB_PATH` para um diretório temporário **antes** de importar
`db` e `sentinela`, porque os dois resolvem o caminho do banco no import.

O mesmo par de comandos roda na CI, em Python 3.12 e 3.13, a cada push em `main`
e `develop` e em todo pull request.

## O que os testes cobrem

| Arquivo | O que garante |
|---|---|
| `test_db.py` | esquema, migração, sessão de voz, streak, fila de cards, fechamento do dia |
| `test_agenda.py` | bloco certo para cada dia da semana e integridade das 14 semanas |
| `test_sentinela.py` | os embeds, o farol de prazos e a árvore de comandos |

Os testes existem principalmente para segurar as regras que já quebraram uma vez.
Cada um destes corresponde a um bug real:

- **dois erros sem `mensagem_id` contam os dois.** O `UNIQUE` da coluna aceita
  vários `NULL` mas só um `0`, e o zero engolia o segundo erro do dia.
- **órfã com teto de 4h.** Sessão aberta além disso é o bot que caiu, não gente
  estudando.
- **órfã de quem está em call fica aberta.** Sem isso cada restart picava uma
  sessão de 50 minutos em cinco de 10.
- **migração acrescenta coluna em banco que já existia.** `CREATE TABLE IF NOT
  EXISTS` não altera tabela antiga, e o `INSERT` quebrava em produção.
- **`fechar_dia` é idempotente.** Rodar de novo recalcula em vez de duplicar.
- **`agregar_dia` não grava nada.** É o que permite o `/hoje` mostrar o parcial
  sem sujar o log.
- **marco de fonte secundária não entra na contagem.** Contar dias para data que
  ninguém publicou é fabricar urgência.
- **a pior matéria vem primeiro no relatório.** É a linha que pauta a semana
  seguinte; se a ordem inverte, a leitura inverte junto.

## Escrever um teste novo

A fixture `con` entrega um banco limpo por teste, num arquivo temporário:

```python
def test_alguma_coisa(con):
    db.registrar_questoes(con, 1, "Alguém", "administrativo", 20, 13)
    assert db.agregar_dia(con, db.hoje())[0]["acertos"] == 13
```

Para testar embed que lê o banco, use `bot_com_banco`, que troca o `con` global
do `sentinela` pela conexão do teste.

Regra prática: teste que precisa de rede não entra. Se a função só faz sentido
falando com o Discord ou com o AnkiConnect, o que se testa é a função pura que
monta o dado, não a chamada.
