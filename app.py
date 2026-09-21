import json
import os
import time
import threading
import hmac
import hashlib
import struct
import base64
from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# Track active drivers so we can close them later
active_drivers = []
driver_lock = threading.Lock()

TARGET_URL = "https://csfloat.com/db"

# ------------------------------------------------------------------
# Steam Guard 2FA code generator (no external library needed)
# ------------------------------------------------------------------
STEAM_GUARD_CHARS = "23456789BCDFGHJKMNPQRTVWXY"

def generate_steam_guard_code(shared_secret: str) -> str:
    """Generate a Steam Guard TOTP code from a shared_secret (Base64 string)."""
    try:
        secret = base64.b64decode(shared_secret)
        timestamp = int(time.time()) // 30
        msg = struct.pack(">Q", timestamp)
        mac = hmac.new(secret, msg, hashlib.sha1).digest()
        start = mac[19] & 0x0F
        value = struct.unpack(">I", mac[start:start + 4])[0] & 0x7FFFFFFF
        code = ""
        for _ in range(5):
            code += STEAM_GUARD_CHARS[value % len(STEAM_GUARD_CHARS)]
            value //= len(STEAM_GUARD_CHARS)
        return code
    except Exception as e:
        return ""


# ------------------------------------------------------------------
# Cookie / account parsing
# format: login:pass:::sharedsecret:::identitysecret
# ------------------------------------------------------------------
def parse_accounts(raw: str):
    accounts = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(":::")
        login_pass = parts[0].split(":", 1)
        accounts.append({
            "username":        login_pass[0] if len(login_pass) > 0 else "",
            "password":        login_pass[1] if len(login_pass) > 1 else "",
            "shared_secret":   parts[1]       if len(parts) > 1     else "",
            "identity_secret": parts[2]       if len(parts) > 2     else "",
        })
    return accounts


# ------------------------------------------------------------------
# Main launch function - full login automation
# ------------------------------------------------------------------
def launch_profile(profile_index: int, account: dict, num_tabs: int):
    """Open Chrome profile, log in to CSFloat via Steam, open extra tabs."""
    profile_path = os.path.join(os.getcwd(), "chrome_profiles", f"profile_{profile_index}")
    os.makedirs(profile_path, exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )
        wait = WebDriverWait(driver, 20)

        # ── Step 1: Open CSFloat ──────────────────────────────────────
        driver.get(TARGET_URL)
        time.sleep(3)

        # ── Step 2: Check if already logged in ───────────────────────
        already_logged_in = False
        try:
            # If the Sign In button is NOT present, we're already logged in
            driver.find_element(By.CSS_SELECTOR, "button.login")
        except Exception:
            already_logged_in = True

        if not already_logged_in and account.get("username"):
            # ── Step 3: Click the CSFloat "Sign in" button ────────────
            try:
                sign_in_btn = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.login"))
                )
                driver.execute_script("arguments[0].click();", sign_in_btn)
            except Exception:
                # Try clicking via JS selector fallback
                driver.execute_script(
                    "document.querySelector('button.login').click();"
                )

            # ── Step 4: Wait for Steam OpenID redirect ─────────────────
            wait.until(lambda d: "steamcommunity.com" in d.current_url)
            time.sleep(2)

            # ── Step 5: Fill in Steam username ────────────────────────
            username_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[name='username'], #input_username"))
            )
            username_field.clear()
            username_field.send_keys(account["username"])
            time.sleep(0.3)

            # ── Step 6: Fill in Steam password ────────────────────────
            password_field = driver.find_element(
                By.CSS_SELECTOR, "input[type='password'], input[name='password'], #input_password"
            )
            password_field.clear()
            password_field.send_keys(account["password"])
            time.sleep(0.3)

            # ── Step 7: Click Steam Sign in button ────────────────────
            steam_submit = driver.find_element(
                By.CSS_SELECTOR, "button[type='submit'], .DjSvCZoKKfoNSmarsEcTS"
            )
            driver.execute_script("arguments[0].click();", steam_submit)
            time.sleep(3)

            # ── Step 8: Handle Steam Guard 2FA ────────────────────────
            if account.get("shared_secret"):
                try:
                    from selenium.webdriver.common.keys import Keys

                    steam_code = generate_steam_guard_code(account["shared_secret"])

                    # Steam uses 5 individual maxlength="1" input boxes
                    # Wait for the first one to appear
                    wait.until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR,
                            "input._3xcXqLVteTNHmk-gh9W65d, "
                            "._1gzkmmy_XA39rp9MtxJfZJ input[maxlength='1'], "
                            "input[maxlength='1'][type='text']"
                        ))
                    )
                    time.sleep(0.5)

                    # Grab all 5 boxes
                    boxes = driver.find_elements(
                        By.CSS_SELECTOR,
                        "input._3xcXqLVteTNHmk-gh9W65d, "
                        "._1gzkmmy_XA39rp9MtxJfZJ input[maxlength='1'], "
                        "input[maxlength='1'][type='text']"
                    )

                    if steam_code and boxes:
                        for i, char in enumerate(steam_code):
                            if i < len(boxes):
                                boxes[i].click()
                                time.sleep(0.1)
                                boxes[i].send_keys(char)
                                time.sleep(0.15)

                        # Press Enter on the last box to submit
                        boxes[min(4, len(boxes) - 1)].send_keys(Keys.RETURN)
                        time.sleep(4)

                except Exception:
                    pass  # 2FA might not be needed if session is already active


            # ── Step 9: Wait for redirect back to CSFloat ─────────────
            try:
                wait.until(lambda d: "csfloat.com" in d.current_url)
                time.sleep(2)
            except Exception:
                pass

        # ── Step 10: Always navigate to the exact target URL ──────────
        # After Steam redirects back, CSFloat might land on /  or /login
        # so we always force-navigate to the correct page.
        driver.get(TARGET_URL)
        time.sleep(3)   # give the Angular app time to fully load

        # ── Step 11: Open additional tabs ─────────────────────────────
        for _ in range(1, num_tabs):
            driver.execute_script(f"window.open('{TARGET_URL}', '_blank');")
            time.sleep(0.5)


        with driver_lock:
            active_drivers.append(driver)

        return True, None

    except Exception as e:
        return False, str(e)


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/launch", methods=["POST"])
def launch():
    data = request.get_json(force=True)
    num_profiles = int(data.get("profiles", 1))
    num_tabs     = int(data.get("tabs",     1))
    raw_cookies  = data.get("cookies",      "")

    accounts = parse_accounts(raw_cookies)

    # Pad / truncate account list to match profile count
    while len(accounts) < num_profiles:
        accounts.append({})
    accounts = accounts[:num_profiles]

    results = []
    threads = []

    def worker(idx, acc):
        ok, err = launch_profile(idx, acc, num_tabs)
        results.append({"profile": idx + 1, "ok": ok, "error": err})

    for i, acc in enumerate(accounts):
        t = threading.Thread(target=worker, args=(i, acc), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    success = sum(1 for r in results if r["ok"])
    return jsonify({"results": results, "launched": success, "total": num_profiles})


@app.route("/close_all", methods=["POST"])
def close_all():
    with driver_lock:
        for d in active_drivers:
            try:
                d.quit()
            except Exception:
                pass
        active_drivers.clear()
    return jsonify({"status": "closed"})


@app.route("/get_codes", methods=["POST"])
def get_codes():
    """Generate live Steam Guard codes for all pasted accounts."""
    data        = request.get_json(force=True)
    raw_cookies = data.get("cookies", "")
    accounts    = parse_accounts(raw_cookies)

    results = []
    for acc in accounts:
        code = ""
        error = ""
        if acc.get("shared_secret"):
            try:
                code = generate_steam_guard_code(acc["shared_secret"])
            except Exception as e:
                error = str(e)
        results.append({
            "username": acc.get("username", "?"),
            "code":     code  if code  else "—",
            "error":    error if error else None,
        })

    return jsonify({"codes": results})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
