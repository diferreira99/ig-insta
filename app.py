"""
Servidor de scraping de seguidores do Instagram (Selenium + Chrome headless).

⚠️ AVISO IMPORTANTE:
- Use uma conta do Instagram SEPARADA, nunca a sua principal — risco real de bloqueio.
- O Instagram muda o HTML do site com frequência. Se os seletores abaixo pararem
  de funcionar, é sinal de que a estrutura da página mudou — normal, precisa ajustar.
- Comece com limit baixo (ex: 30) e não rode com frequência exagerada no mesmo dia.

Rotas:
  GET  /                      -> health check
  POST /scrape-followers      -> { target_username, limit, keywords (opcional) }
                                  headers: x-api-token
"""

import os
import time
import random
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

API_TOKEN = os.environ.get("API_TOKEN", "")
IG_USERNAME = os.environ.get("IG_USERNAME", "")
IG_PASSWORD = os.environ.get("IG_PASSWORD", "")

_driver = None  # sessão do Chrome fica viva entre requisições (evita logar toda vez)


def checar_token():
    if not API_TOKEN:
        return True  # sem token configurado = sem checagem (defina em produção!)
    return request.headers.get("x-api-token") == API_TOKEN


def get_driver():
    global _driver
    if _driver is not None:
        return _driver

    from selenium.webdriver.chrome.service import Service

    options = Options()
    options.binary_location = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1280,900")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )

    driver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    service = Service(executable_path=driver_path)

    _driver = webdriver.Chrome(service=service, options=options)
    return _driver


def login_instagram(driver):
    driver.get("https://www.instagram.com/accounts/login/")
    wait = WebDriverWait(driver, 20)

    user_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
    pass_field = driver.find_element(By.NAME, "password")

    user_field.clear()
    user_field.send_keys(IG_USERNAME)
    time.sleep(random.uniform(0.5, 1.2))
    pass_field.clear()
    pass_field.send_keys(IG_PASSWORD)
    time.sleep(random.uniform(0.5, 1.2))
    pass_field.submit()

    # Espera a home carregar (procura o ícone de busca ou o campo de pesquisa)
    time.sleep(6)

    # Fecha popups de "Salvar informações de login" / "Ativar notificações", se aparecerem
    try:
        botoes = driver.find_elements(By.XPATH, "//button[contains(text(),'Agora não') or contains(text(),'Not Now')]")
        for b in botoes:
            b.click()
            time.sleep(1)
    except Exception:
        pass


def coletar_seguidores(driver, target_username, limit):
    driver.get(f"https://www.instagram.com/{target_username}/")
    wait = WebDriverWait(driver, 20)

    # Clica no link de "seguidores" (o texto exato varia por idioma da conta)
    link_seguidores = wait.until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/followers')]"))
    )
    link_seguidores.click()
    time.sleep(3)

    # A lista de seguidores abre dentro de um <div role="dialog">
    dialog = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
    lista_scroll = dialog.find_element(By.XPATH, ".//div[contains(@style,'overflow')]")

    usernames = set()
    tentativas_sem_novidade = 0

    while len(usernames) < limit and tentativas_sem_novidade < 6:
        links = dialog.find_elements(By.XPATH, ".//a[contains(@href, '/') and @role='link']")
        antes = len(usernames)
        for l in links:
            href = l.get_attribute("href") or ""
            partes = href.rstrip("/").split("/")
            if partes and partes[-1] and "instagram.com" in href:
                usernames.add(partes[-1])
            if len(usernames) >= limit:
                break

        if len(usernames) == antes:
            tentativas_sem_novidade += 1
        else:
            tentativas_sem_novidade = 0

        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollTop + 400;", lista_scroll)
        time.sleep(random.uniform(1.2, 2.0))

    return list(usernames)[:limit]


def checar_bio(driver, username, keywords):
    try:
        driver.get(f"https://www.instagram.com/{username}/")
        time.sleep(random.uniform(2, 3.5))
        bio_els = driver.find_elements(By.XPATH, "//h1/following-sibling::span | //div[contains(@class,'bio')]")
        bio_texto = " ".join(el.text for el in bio_els).lower()
        if not keywords:
            return True, bio_texto
        return any(kw.lower() in bio_texto for kw in keywords), bio_texto
    except Exception:
        return False, ""


def enviar_dm(driver, username, mensagem):
    """Abre o perfil, clica em 'Mensagem', digita e envia. Assume que já está na página do perfil."""
    wait = WebDriverWait(driver, 15)
    try:
        botao_msg = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[contains(text(),'Message') or contains(text(),'Mensagem')]")
        ))
        botao_msg.click()
        time.sleep(random.uniform(2, 3))

        # Às vezes abre um popup perguntando se quer notificações — fecha se aparecer
        try:
            fechar = driver.find_element(By.XPATH, "//button[contains(text(),'Not Now') or contains(text(),'Agora não')]")
            fechar.click()
            time.sleep(1)
        except Exception:
            pass

        campo_msg = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//textarea[@placeholder] | //div[@role='textbox']")
        ))
        campo_msg.click()
        for parte in mensagem.split(" "):
            campo_msg.send_keys(parte + " ")
            time.sleep(random.uniform(0.05, 0.15))  # digitação com pequena variação
        time.sleep(random.uniform(1, 2))
        campo_msg.send_keys(u"\ue007")  # tecla Enter, envia a mensagem
        return True, ""
    except Exception as e:
        return False, str(e)


@app.route("/")
def health():
    return jsonify({"status": "ok", "message": "Servidor de scraping do Instagram rodando."})


@app.route("/scrape-and-dm", methods=["POST"])
def scrape_and_dm():
    if not checar_token():
        return jsonify({"error": "Token inválido"}), 401

    if not IG_USERNAME or not IG_PASSWORD:
        return jsonify({"error": "Configure IG_USERNAME e IG_PASSWORD nas variáveis de ambiente."}), 500

    data = request.get_json(force=True) or {}
    target_username = data.get("target_username", "").strip().lstrip("@")
    limit = int(data.get("limit", 30))
    keywords = data.get("keywords", [])
    mensagem = data.get("message", "").strip()
    delay_min = float(data.get("delay_min", 20))   # segundos entre cada DM
    delay_max = float(data.get("delay_max", 45))

    if not target_username:
        return jsonify({"error": "Envie 'target_username' no corpo da requisição."}), 400
    if not mensagem:
        return jsonify({"error": "Envie 'message' com o texto a ser enviado."}), 400

    try:
        driver = get_driver()
        login_instagram(driver)
        usernames = coletar_seguidores(driver, target_username, limit)

        resultados = []
        for u in usernames:
            bate, bio = checar_bio(driver, u, keywords)
            item = {"username": u, "bio": bio, "bate_filtro": bate, "dm_enviado": False, "erro": ""}

            if bate:
                ok, erro = enviar_dm(driver, u, mensagem)
                item["dm_enviado"] = ok
                item["erro"] = erro
                # Pausa entre um DM e outro — a parte mais importante pra não ser bloqueado
                time.sleep(random.uniform(delay_min, delay_max))
            else:
                time.sleep(random.uniform(1.5, 3))

            resultados.append(item)

        enviados = sum(1 for r in resultados if r["dm_enviado"])
        return jsonify({
            "target_username": target_username,
            "total_coletado": len(usernames),
            "total_dms_enviados": enviados,
            "resultados": resultados
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/scrape-followers", methods=["POST"])
def scrape_followers():
    if not checar_token():
        return jsonify({"error": "Token inválido"}), 401

    if not IG_USERNAME or not IG_PASSWORD:
        return jsonify({"error": "Configure IG_USERNAME e IG_PASSWORD nas variáveis de ambiente."}), 500

    data = request.get_json(force=True) or {}
    target_username = data.get("target_username", "").strip().lstrip("@")
    limit = int(data.get("limit", 30))
    keywords = data.get("keywords", [])  # ex: ["contabilidade", "contador"]

    if not target_username:
        return jsonify({"error": "Envie 'target_username' no corpo da requisição."}), 400

    try:
        driver = get_driver()
        login_instagram(driver)
        usernames = coletar_seguidores(driver, target_username, limit)

        resultados = []
        for u in usernames:
            bate, bio = checar_bio(driver, u, keywords)
            resultados.append({"username": u, "bio": bio, "bate_filtro": bate})
            time.sleep(random.uniform(1.5, 3))  # pausa entre perfis, evita rajada

        return jsonify({
            "target_username": target_username,
            "total_coletado": len(usernames),
            "resultados": resultados
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
