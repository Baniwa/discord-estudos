# Subir o bot numa VM

O bot precisa ficar de pé 24 horas. Enquanto ele roda no meu PC, o cronômetro
de call para quando eu desligo a máquina, e o briefing das 7h não sai.

## Onde

| Opção | Custo | Realidade |
|---|---|---|
| **Oracle Cloud Always Free** (ARM Ampere) | R$ 0 | 4 vCPU e 24 GB, grátis para sempre. Pede cartão só para validar identidade. A capacidade Ampere vive esgotada nas regiões populares, então pode levar dias tentando. |
| **Google Cloud** e2-micro | R$ 0 | 1 vCPU compartilhado, 1 GB, regiões dos EUA. Bem mais fácil de conseguir. Cabe o bot com folga. |
| **Hetzner** CX22 | ~R$ 22/mês | 2 vCPU, 4 GB. Sobe em 30 segundos. |

Tentar a Oracle primeiro e cair para o Google Cloud se der `out of host capacity`.
Os números do free tier mudam sem aviso, então conferir no site antes.

Distribuição: **Ubuntu 24.04 LTS**. É o que tem mais documentação e o Docker
instala em um comando.

## Passo a passo

### 1. Na VM, instalar o Docker

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Clonar o repositório

```bash
git clone https://github.com/Baniwa/discord-estudos.git
cd discord-estudos
```

O repositório é privado, então o `git` vai pedir credencial. Use um Personal
Access Token do GitHub, não a senha da conta.

### 3. Criar o `.env`

```bash
cp .env.example .env
nano .env
```

Preencher `DISCORD_BOT_TOKEN`. O `DISCORD_GUILD_ID` é opcional, mas na VM vale
preencher com `1074849674860703835` para não depender da descoberta automática.

**O `.env` não está no git e nunca deve entrar.** Digite o token direto na VM.

### 4. Parar o bot que roda no PC

Dois bots com o mesmo token respondem ao mesmo comando duas vezes e contam a
mesma sessão de call em dois bancos diferentes. Antes de subir na VM, feche o
processo aqui.

### 5. Subir

```bash
bash deploy.sh
```

### 6. Conferir

```bash
docker compose logs -f sentinela
```

Tem que aparecer `Sentinela no ar como Caipora#9758`.

## O dia a dia

```bash
docker compose logs -f sentinela   # acompanhar
docker compose restart sentinela   # reiniciar
docker compose down                # parar (NÃO apaga o banco)
bash deploy.sh                     # atualizar para a última versão da main
bash backup.sh                     # copiar o banco para fora do volume
```

O banco fica num volume Docker chamado `dados`. Recriar o container não apaga
o histórico de estudo. O `backup.sh` usa o `.backup` do sqlite, que é
consistente mesmo com o bot escrevendo.

## O problema do Anki, e ele é real

**O AnkiConnect só escuta em `127.0.0.1`.** Enquanto o bot roda no meu PC, os
dois se falam direto. Com o bot na VM isso deixa de funcionar:

- `/erro` continua enfileirando card no banco, sem perder nada;
- mas nada mais chega ao Anki sozinho;
- e o relatório para de receber "o que não gruda", porque ninguém lê a coleção.

O resto do bot (cronômetro de call, prazos, log diário, relatório, boas-vindas)
funciona igual.

### As saídas

**A. Rodar o `anki_sync.py` aqui, contra uma cópia do banco.** Não resolve: o
banco que interessa está na VM, e trazer cópia para cá desatualiza o original.

**B. Ponte HTTP.** O bot na VM expõe a fila de cards num endpoint autenticado, e
um agente pequeno no meu PC puxa, entrega ao Anki e devolve a estatística. É a
solução certa, e usa o `aiohttp` que já vem com o discord.py, sem dependência
nova. **Ainda não está implementada.**

**C. Deixar o Anki fora da VM.** O bot na VM cuida de call, prazos e log; o
`anki_sync.py` continua rodando aqui, mas apontado para um banco local separado.
Funciona, ao custo de dois bancos e de o relatório perder o bloco do Anki.

**D. Deixar o bot no PC e mandar só outros projetos para a VM.** Perde o 24/7,
que era o motivo da VM.

Recomendo a **B**, e é o que falta construir antes de mudar de máquina.

## O que mais colocar na mesma VM

Levantei o que existe em `D:\Projetos`:

**`dou.ia`** é o co-inquilino óbvio. Python com Docker e compose prontos, faz
scraping e resumo do Diário Oficial da União. Ele fecha um buraco do Sentinela:
hoje o bot se recusa a contar dias para BB, ANPD e BACEN porque não há edital
publicado, e a regra é não fabricar urgência a partir de infográfico. O `dou.ia`
monitora exatamente onde esses editais vão sair. Encaixe: ele detecta a
publicação, posta em `#editais-e-prazos`, e o marco vira `verificado: true`.

**`safepay-schedule-api`** tem Docker e compose e é projeto de portfólio.
Portfólio parado em `localhost` não vale nada em processo seletivo. Sobe junto e
vira link no currículo. É JVM, então só cabe se a VM tiver mais de 1 GB.

**`baniwa-portifolio`** vai para a **Vercel**, não para a VM. É Next.js: free
tier com CDN e deploy a cada push, e numa VM de 1 GB ficaria pior.

**Fora da lista:** `goes-psiquiatria-online` é sistema de clínica com dado de
paciente. Numa VM free tier dividindo máquina com um bot de Discord, é problema
de LGPD. Merece infra própria. E `callista` é do Senado, com Oracle Apex, não é
meu para hospedar.

### Dimensionamento

| VM | O que cabe |
|---|---|
| Oracle ARM, 24 GB | `sentinela` + `dou.ia` + `safepay`, com folga |
| Google e2-micro, 1 GB | `sentinela` + `dou.ia`, apertado. `safepay` não. |

## Segurança

- O `.env` fica só na VM, nunca no git.
- Se o token vazar, é só resetar no portal do Discord e refazer o `.env`.
- O container roda com usuário sem privilégio (uid 1000), não como root.
- O log tem limite de 30 MB no total. Sem isso ele enche o disco de uma VM
  pequena em algumas semanas e derruba tudo junto.
- Firewall: o bot só faz conexão de saída. Não precisa abrir porta nenhuma de
  entrada, a menos que a ponte do Anki seja implementada.
