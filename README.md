# Instagram Followers Scraper — deploy no Railway

Extrai seguidores de um perfil público do Instagram, com filtro opcional por palavra-chave na bio.

## ⚠️ Avisos importantes

- **Use uma conta do Instagram separada** para login — nunca a sua principal. Risco real de bloqueio existe, mesmo em volumes baixos.
- **O Instagram muda o HTML do site com frequência.** Os seletores usados aqui (`app.py`) podem quebrar de tempos em tempos — é normal, não é bug do código, é o site mudando por baixo.
- Comece com `limit` baixo (ex: 30) e não rode várias vezes seguidas no mesmo dia.
- Esse projeto é só pra estudo/uso pessoal — não distribua nem cobre por isso, o Instagram proíbe scraping nos Termos de Uso.

## Deploy no Railway

1. Crie um repositório novo no GitHub com esses 4 arquivos (`Dockerfile`, `requirements.txt`, `app.py`, este `README.md`).
2. No Railway: **New Project → Deploy from GitHub repo** → selecione esse repositório.
3. O Railway vai detectar o `Dockerfile` automaticamente e buildar (demora um pouco mais que os deploys Node, por causa do Chrome).
4. Em **Variables**, adicione:
   - `IG_USERNAME` = usuário da conta separada
   - `IG_PASSWORD` = senha dela
   - `API_TOKEN` = uma senha sua, pra proteger o endpoint (ex: `scraper2024xyz`)
5. Em **Settings → Networking**, clique em **Generate Domain** pra pegar a URL pública.

## Como usar

### Só extrair (sem enviar nada)
```
POST https://SEU-APP.up.railway.app/scrape-followers
Headers: x-api-token: SEU_TOKEN
Body (JSON):
{
  "target_username": "perfil_alvo",
  "limit": 30,
  "keywords": ["contabilidade", "contador", "escritorio contabil"]
}
```

### Extrair, filtrar por bio E enviar DM pros que baterem
```
POST https://SEU-APP.up.railway.app/scrape-and-dm
Headers: x-api-token: SEU_TOKEN
Body (JSON):
{
  "target_username": "perfil_alvo",
  "limit": 30,
  "keywords": ["contabilidade", "contador"],
  "message": "Olá! Vi seu perfil e...",
  "delay_min": 20,
  "delay_max": 45
}
```
`delay_min`/`delay_max` são em segundos, entre um DM e outro. Não baixe muito esses valores —
é a principal proteção contra bloqueio de conta.

## Se o Instagram mudar o layout e parar de funcionar

Abra o `app.py` e ajuste os seletores dentro de `coletar_seguidores()` e `checar_bio()` —
são baseados na estrutura do site no momento em que foi escrito. Me manda o erro que aparecer
que ajudo a corrigir.
