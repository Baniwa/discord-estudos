# Imagem enxuta de proposito: o bot e I/O, nao CPU. Numa VM free tier de 1 GB
# cada MB conta, e a diferenca entre a imagem completa e a slim aqui e ~700 MB.
FROM python:3.12-slim

# Fuso horario dentro do container. Sem isto o bot dispara o briefing das 7h
# em UTC, ou seja, as 4h da manha no horario dela.
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Log sai na hora, sem buffer, senao `docker logs` fica mudo por minutos.
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

# Requirements antes do codigo: muda pouco, entao a camada de dependencia
# fica em cache e o rebuild leva segundos em vez de minutos.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usuario sem privilegio. O banco fica num volume montado, entao precisa
# existir e pertencer a ele antes do drop.
RUN useradd -m -u 1000 sentinela \
    && mkdir -p /dados \
    && chown -R sentinela:sentinela /app /dados
USER sentinela

# O banco mora no volume, nao na imagem: recriar o container nao pode apagar
# o historico de estudo.
ENV DB_PATH=/dados/estudos.db

CMD ["python", "sentinela.py"]
