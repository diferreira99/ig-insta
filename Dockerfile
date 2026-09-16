FROM python:3.11-slim

# Instala o Chromium (navegador) e o Chromedriver correspondente via apt —
# isso garante que as versões dos dois sejam sempre compatíveis entre si,
# evitando o crash comum de "Chrome baixado manualmente vs driver desatualizado".
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=3000
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
EXPOSE 3000

CMD ["python", "app.py"]
