import json
import os
import time
import threading
import hmac
import hashlib
import struct
import base64
import platform
import subprocess
import winreg
from flask import Flask, render_template, request, jsonify
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Track active drivers so we can close them later
active_drivers = []
driver_lock = threading.Lock()

TARGET_URL = "https://csfloat.com/db"

def get_chrome_major_version():
    """Auto-detect the major version of Chrome installed on Windows."""
    if platform.system() == "Windows":
        try:
            # Check current user registry
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
            version, _ = winreg.QueryValueEx(key, "version")
            return int(version.split('.')[0])
        except Exception:
            pass
        try:
            # Check local machine registry
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Google Chrome")
            version, _ = winreg.QueryValueEx(key, "version")
            return int(version.split('.')[0])
        except Exception:
            pass
    return None

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
    if not raw or not isinstance(raw, str):
        return accounts
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
def launch_profile(profile_index: int, account: dict, num_tabs: int, scraper_config: dict = None):
    """Open Chrome profile, log in to CSFloat via Steam, open extra tabs."""
    profile_path = os.path.join(os.getcwd(), "chrome_profiles", f"profile_{profile_index}")
    os.makedirs(profile_path, exist_ok=True)

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--profile-directory=Default")
    
    # Load the custom price injector extension
    extension_path = os.path.join(os.getcwd(), "extension")
    options.add_argument(f"--load-extension={extension_path}")
    
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    try:
        chrome_v = get_chrome_major_version()
        kwargs = {
            "options": options,
            "user_data_dir": profile_path,
            "use_subprocess": True
        }
        if chrome_v:
            kwargs["version_main"] = chrome_v
            
        driver = uc.Chrome(**kwargs)
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

        # ── Step 10: Run the Scraper on each Link ──────────────────────
        if not scraper_config:
            scraper_config = {"db_links": ["https://csfloat.com/db"], "min_price": 300.0}

        min_price = scraper_config.get("min_price", 300.0)
        db_links  = scraper_config.get("db_links",  ["https://csfloat.com/db"])

        print(f"Starting scraper for {len(db_links)} links, min ${min_price}")

        # ── JS helpers ──────────────────────────────────────────────────
        # Detect if the page is showing a turnstile / error state
        turnstile_check_js = """
            const err = document.querySelector('.container .header span, .error-text, [class*="error"] span');
            return err ? err.innerText : null;
        """

        # Extract items from Angular mat-table rows
        extract_js = """
            const minPrice = arguments[0];
            const results  = [];
            const rows = document.querySelectorAll('mat-row');
            rows.forEach(row => {
                const cells = row.querySelectorAll('mat-cell');
                // price cell usually contains $ sign
                let price = 0, priceText = '';
                let rowText = row.innerText || '';
                // Find $ amount
                const priceMatch = rowText.match(/\\$([\\d,]+\\.?\\d*)/);
                if (priceMatch) {
                    price = parseFloat(priceMatch[1].replace(/,/g, ''));
                }
                if (price >= minPrice) {
                    results.push({
                        name:  rowText.replace(/\\n/g, ' ').substring(0, 120).trim(),
                        price: price
                    });
                }
            });
            return results;
        """

        found_items = []
        found_set   = set()

        def wait_for_rows(max_wait=15):
            """Wait until mat-row elements appear on the page."""
            for _ in range(max_wait):
                count = driver.execute_script("return document.querySelectorAll('mat-row').length;")
                if count and count > 0:
                    return True
                time.sleep(1)
            return False

        def check_turnstile():
            """Returns error text if turnstile / error is showing."""
            try:
                return driver.execute_script(turnstile_check_js)
            except Exception:
                return None

        for link in db_links:
            print(f"  → Navigating to {link}")
            driver.get(link)
            time.sleep(8)  # wait longer for Angular to render

            page_num = 1
            retry_count = 0

            while page_num <= 20:  # max 20 pages per link (~2000 items)

                # ── Check turnstile ──────────────────────────────────
                err_text = check_turnstile()
                if err_text and ("turnstile" in err_text.lower() or "failed" in err_text.lower() or "error" in err_text.lower()):
                    print(f"  ⚠ Turnstile/error detected on page {page_num}: '{err_text}'. Waiting 8s and retrying...")
                    time.sleep(8)
                    driver.refresh()
                    time.sleep(5)
                    retry_count += 1
                    if retry_count >= 3:
                        print(f"  ✘ Skipping {link} after 3 failed retries")
                        break
                    continue

                retry_count = 0  # reset on success

                # ── Wait for rows ─────────────────────────────────────
                rows_loaded = wait_for_rows(max_wait=12)
                if not rows_loaded:
                    print(f"  ⚠ No rows found on page {page_num}, stopping this link.")
                    break

                # ── Scroll to load all rows ───────────────────────────
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)

                # ── Extract items ─────────────────────────────────────
                items = driver.execute_script(extract_js, min_price)
                new_count = 0
                if items:
                    for it in items:
                        key = f"{it['name']}|{it['price']}"
                        if key not in found_set:
                            found_set.add(key)
                            item_str = f"[{link}] Found: {it['name']} (Price: ${it['price']})"
                            found_items.append(item_str)
                            print(item_str)
                            new_count += 1

                print(f"  Page {page_num}: {new_count} new items above ${min_price}")

                # ── Next page ─────────────────────────────────────────
                try:
                    next_btn = driver.find_element(
                        By.CSS_SELECTOR,
                        "button.mat-mdc-paginator-navigation-next, "
                        "button.mat-paginator-navigation-next"
                    )
                    classes = next_btn.get_attribute("class") or ""
                    disabled = not next_btn.is_enabled() or "disabled" in classes
                    if disabled:
                        print(f"  ✓ Last page reached for {link}")
                        break
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(3.5)  # human-like delay
                    page_num += 1
                except Exception:
                    print(f"  ✓ No paginator found — done with {link}")
                    break

        # ── Write results ─────────────────────────────────────────────
        if found_items:
            with open("found_expensive_items.txt", "a", encoding="utf-8") as f:
                for item in found_items:
                    f.write(item + "\\n")
            print(f"✔ Saved {len(found_items)} items to found_expensive_items.txt")
        else:
            print("ℹ No items above threshold found.")



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


@app.route("/results")
def results():
    return render_template("results.html")


@app.route("/api/results")
def api_results():
    """Parse found_expensive_items.txt and return structured JSON."""
    items = []
    filepath = os.path.join(os.getcwd(), "found_expensive_items.txt")
    if not os.path.exists(filepath):
        return jsonify({"items": [], "total": 0})

    seen = set()
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split on literal \n entries (each item ends with \\n in file)
    raw_lines = [l.strip() for l in content.replace("\\n", "\n").splitlines() if l.strip()]

    import re
    for line in raw_lines:
        # Parse: [URL] Found: NAME (Price: $PRICE)
        m = re.match(r'\[(.+?)\] Found: (.+?) \(Price: \$([0-9.]+)\)', line)
        if not m:
            continue
        url   = m.group(1)
        name  = m.group(2).strip()
        price = float(m.group(3))

        # Dedup by name+price
        key = f"{name}|{price}"
        if key in seen:
            continue
        seen.add(key)

        # Extract float value from name string
        float_match = re.search(r'(\d+\.\d+)\s+FN', name)
        float_val = float_match.group(1) if float_match else ""

        # Clean up name — remove float, rank, seed etc
        clean_name = re.sub(r'#\d+\s+', '', name)         # remove #rank
        clean_name = re.sub(r'\d+\.\d{10,}\s+FN', '', clean_name)  # remove float
        clean_name = re.sub(r'\s+\d+\s+', ' ', clean_name)         # remove seed
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()

        items.append({
            "rank":      re.search(r'#(\d+)', name).group(1) if re.search(r'#(\d+)', name) else "",
            "name":      clean_name,
            "float":     float_val,
            "price":     price,
            "source_url": url,
        })

    # Sort by price descending
    items.sort(key=lambda x: x["price"], reverse=True)
    return jsonify({"items": items, "total": len(items)})




@app.route("/launch", methods=["POST"])
def launch():
    data = request.get_json(force=True)
    num_profiles = int(data.get("profiles", 1))
    num_tabs     = int(data.get("tabs",     1))
    raw_cookies  = data.get("cookies",      "")
    min_price_str = data.get("minPrice", "300")
    try:
        min_price = float(min_price_str)
    except ValueError:
        min_price = 300.0

    raw_links = data.get("dbLinks", "")
    db_links = [l.strip() for l in raw_links.splitlines() if l.strip()]
    if not db_links:
        db_links = ["https://csfloat.com/db"]

    scraper_config = {
        "min_price": min_price,
        "db_links": db_links
    }

    accounts = parse_accounts(raw_cookies)

    # Pad / truncate account list to match profile count
    while len(accounts) < num_profiles:
        accounts.append({})
    accounts = accounts[:num_profiles]

    results = []
    threads = []

    def worker(idx, acc):
        ok, err = launch_profile(idx, acc, num_tabs, scraper_config)
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
