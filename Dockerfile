FROM python:3.11-slim

# Instala o Chromium (navegador), o Chromedriver correspondente, e o tini
# (um "init" mínimo que evita processos zumbis do Chrome quando rodando
# como PID 1 dentro do container — causa clássica de crash nesse cenário)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=3000
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
EXPOSE 3000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "app.py"]
