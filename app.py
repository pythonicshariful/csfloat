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
def launch_profile(profile_index: int, account: dict, num_tabs: int, filters: dict = None):
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


            # ── Step 9: Click Steam OpenID confirmation button ──────
            # Steam shows a redirect/authorization page with a Sign In button
            # (#imageLogin) that MUST be clicked to finalize OpenID login.
            try:
                confirm_btn = WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "imageLogin"))
                )
                driver.execute_script("arguments[0].click();", confirm_btn)
                time.sleep(2)
            except Exception:
                pass  # Button absent if session was already authorized

            # ── Step 10 (inner): Wait for redirect back to CSFloat ───────
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

        # ── Step 11: Click Filter button to open sidebar ─────
        try:
            filter_btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "button[mat-raised-button][color='primary'] mat-icon[data-mat-icon-name='filter']"
                ))
            )
            driver.execute_script("arguments[0].closest('button').click();", filter_btn)
            # Wait for the filter sidebar drawer to open
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "mat-drawer.filter-drawer.mat-drawer-opened")
                )
            )
            time.sleep(1)

            # ── Step 11.5: Apply Filters if provided ─────
            if filters:
                try:
                    time.sleep(1) # Extra wait for sidebar animation
                    
                    # Helper function to JS-set value of Angular inputs
                    def set_ng_input(selector, value):
                        elem = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', { bubbles: true })); arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", elem, value)

                    # Min Float
                    min_float = filters.get("minFloat", "")
                    if min_float:
                        set_ng_input("input[formcontrolname='min']", min_float)
                        
                    # Max Float
                    max_float = filters.get("maxFloat", "")
                    if max_float:
                        set_ng_input("input[formcontrolname='max']", max_float)

                    # Paint Seed
                    paint_seed = filters.get("paintSeed", "")
                    if paint_seed:
                        set_ng_input("input.seed-input", paint_seed)
                        
                    # Min Age
                    min_age = filters.get("minAge", "")
                    if min_age:
                        set_ng_input("input[formcontrolname='minAge']", min_age)
                        
                    # Max Age
                    max_age = filters.get("maxAge", "")
                    if max_age:
                        set_ng_input("input[formcontrolname='maxAge']", max_age)
                        
                    # Special (Checkboxes)
                    if filters.get("statTrak", False):
                        cb = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'StatTrak')]/ancestor::mat-checkbox//input[@type='checkbox']"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", cb)
                        time.sleep(0.2)
                        driver.execute_script("if(!arguments[0].checked) arguments[0].click();", cb)
                        
                    if filters.get("souvenir", False):
                        cb = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Souvenir')]/ancestor::mat-checkbox//input[@type='checkbox']"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", cb)
                        time.sleep(0.2)
                        driver.execute_script("if(!arguments[0].checked) arguments[0].click();", cb)
                        
                    if filters.get("normal", False):
                        cb = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Normal')]/ancestor::mat-checkbox//input[@type='checkbox']"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", cb)
                        time.sleep(0.2)
                        driver.execute_script("if(!arguments[0].checked) arguments[0].click();", cb)

                    # SteamID 64
                    steam_id = filters.get("steamId", "")
                    if steam_id:
                        set_ng_input("input[formcontrolname='steamId']", steam_id)
                        
                    # Source (Only)
                    source_val = filters.get("source", "")
                    if source_val:
                        source_select = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "mat-select[formcontrolname='only']"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", source_select)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", source_select)
                        time.sleep(0.5)
                        
                        options = driver.find_elements(By.CSS_SELECTOR, "mat-option")
                        for opt in options:
                            if source_val in opt.text:
                                driver.execute_script("arguments[0].click();", opt)
                                break
                        time.sleep(0.5)
                        
                    # Stickers
                    stickers_str = filters.get("stickers", "")
                    if stickers_str:
                        sticker_names = [s.strip() for s in stickers_str.split(',') if s.strip()]
                        sticker_inputs = driver.find_elements(By.CSS_SELECTOR, "app-sticker-search input[matinput]")
                        for i, name in enumerate(sticker_names):
                            if i < len(sticker_inputs):
                                s_in = sticker_inputs[i]
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", s_in)
                                time.sleep(0.2)
                                s_in.send_keys(name)
                                time.sleep(0.5)
                                # Try to click the first autocomplete option
                                try:
                                    opts = WebDriverWait(driver, 2).until(
                                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option"))
                                    )
                                    if opts:
                                        driver.execute_script("arguments[0].click();", opts[0])
                                except Exception:
                                    pass
                                time.sleep(0.5)
                                
                    # Charms
                    charm_name = filters.get("charm", "")
                    if charm_name:
                        charm_input = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "app-keychain-search input[matinput]"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", charm_input)
                        time.sleep(0.2)
                        charm_input.send_keys(charm_name)
                        time.sleep(0.5)
                        try:
                            opts = WebDriverWait(driver, 2).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "mat-option"))
                            )
                            if opts:
                                driver.execute_script("arguments[0].click();", opts[0])
                        except Exception:
                            pass
                        time.sleep(0.5)


                        
                    # Sort By
                    sort_val = filters.get("sort", "")
                    if sort_val:
                        sort_map = {
                            "0": "Lowest Float",
                            "1": "Highest Float",
                            "2": "Lowest Price",
                            "3": "Highest Price",
                            "4": "Recent"
                        }
                        if sort_val in sort_map:
                            sort_select = WebDriverWait(driver, 3).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "mat-select[formcontrolname='order']"))
                            )
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", sort_select)
                            time.sleep(0.2)
                            driver.execute_script("arguments[0].click();", sort_select)
                            time.sleep(0.5)
                            
                            option_text = sort_map[sort_val]
                            options = driver.find_elements(By.CSS_SELECTOR, "mat-option")
                            for opt in options:
                                if option_text in opt.text:
                                    driver.execute_script("arguments[0].click();", opt)
                                    break
                            time.sleep(0.5)
                            
                    # Rarity
                    rarity_val = filters.get("rarity", "")
                    if rarity_val:
                        rarity_map = {
                            "1": "Consumer Grade",
                            "2": "Industrial Grade",
                            "3": "Mil-Spec Grade",
                            "4": "Restricted",
                            "5": "Classified",
                            "6": "Covert",
                            "7": "Contraband"
                        }
                        if rarity_val in rarity_map:
                            rarity_select = WebDriverWait(driver, 3).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "mat-select[formcontrolname='rarity']"))
                            )
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", rarity_select)
                            time.sleep(0.2)
                            driver.execute_script("arguments[0].click();", rarity_select)
                            time.sleep(0.5)
                            
                            option_text = rarity_map[rarity_val]
                            options = driver.find_elements(By.CSS_SELECTOR, "mat-option")
                            for opt in options:
                                if option_text in opt.text:
                                    driver.execute_script("arguments[0].click();", opt)
                                    break
                            time.sleep(0.5)
                            
                except Exception as e:
                    print(f"Error applying filters: {e}")

        except Exception:
            pass  # Filter button not found or sidebar did not open

        # ── Step 12: Open additional tabs ─────────────────────────────
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
    filters = {
        "sort": data.get("filterSort", ""),
        "rarity": data.get("filterRarity", ""),
        "minFloat": data.get("filterMinFloat", ""),
        "maxFloat": data.get("filterMaxFloat", ""),
        "paintSeed": data.get("filterPaintSeed", ""),
        "minAge": data.get("filterMinAge", ""),
        "maxAge": data.get("filterMaxAge", ""),
        "statTrak": data.get("filterStatTrak", False),
        "souvenir": data.get("filterSouvenir", False),
        "normal": data.get("filterNormal", False),
        "stickers": data.get("filterStickers", ""),
        "charm": data.get("filterCharm", ""),
        "source": data.get("filterSource", ""),
        "steamId": data.get("filterSteamId", "")
    }

    accounts = parse_accounts(raw_cookies)

    # Pad / truncate account list to match profile count
    while len(accounts) < num_profiles:
        accounts.append({})
    accounts = accounts[:num_profiles]

    results = []
    threads = []

    def worker(idx, acc):
        ok, err = launch_profile(idx, acc, num_tabs, filters)
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
