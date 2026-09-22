import re

# 1. Update index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

additional_filters = """
        <div style="display: flex; gap: 16px; margin-top: 12px;">
          <div style="flex: 1;">
            <label style="display:block; font-size:.75rem; color:var(--text-3); margin-bottom:4px;">Stickers (comma separated, max 4)</label>
            <input type="text" class="url-input" id="filterStickers" placeholder="e.g. Titan | Katowice 2014" style="margin-bottom:0;" />
          </div>
          <div style="flex: 1;">
            <label style="display:block; font-size:.75rem; color:var(--text-3); margin-bottom:4px;">Charm</label>
            <input type="text" class="url-input" id="filterCharm" placeholder="e.g. Lil' SAS" style="margin-bottom:0;" />
          </div>
        </div>
        <div style="display: flex; gap: 16px; margin-top: 12px;">
          <div style="flex: 1;">
            <label style="display:block; font-size:.75rem; color:var(--text-3); margin-bottom:4px;">Source (Only)</label>
            <select class="url-input" id="filterSource" style="margin-bottom:0; cursor:pointer;">
              <option value="">Any</option>
              <option value="Market">Market</option>
              <option value="Public Inventories">Public Inventories</option>
              <option value="Trade Up">Trade Up</option>
            </select>
          </div>
          <div style="flex: 1;">
            <label style="display:block; font-size:.75rem; color:var(--text-3); margin-bottom:4px;">Owner SteamID 64</label>
            <input type="text" class="url-input" id="filterSteamId" placeholder="SteamID 64" style="margin-bottom:0;" />
          </div>
        </div>
"""

if "filterStickers" not in html:
    html = html.replace(
        '<input type="checkbox" id="filterNormal" /> Normal\n          </label>\n        </div>',
        '<input type="checkbox" id="filterNormal" /> Normal\n          </label>\n        </div>\n' + additional_filters
    )
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Patched index.html")

# 2. Update main.js
with open('static/js/main.js', 'r', encoding='utf-8') as f:
    js = f.read()

if "filterStickers" not in js:
    # Add variable reads
    js = js.replace(
        "const filterNormal = document.getElementById('filterNormal').checked;",
        "const filterNormal = document.getElementById('filterNormal').checked;\n"
        "  const filterStickers = document.getElementById('filterStickers').value;\n"
        "  const filterCharm = document.getElementById('filterCharm').value;\n"
        "  const filterSource = document.getElementById('filterSource').value;\n"
        "  const filterSteamId = document.getElementById('filterSteamId').value;"
    )
    
    # Add payload args
    js = js.replace(
        "        filterStatTrak,\n        filterSouvenir,\n        filterNormal\n      }),",
        "        filterStatTrak,\n        filterSouvenir,\n        filterNormal,\n"
        "        filterStickers,\n        filterCharm,\n        filterSource,\n        filterSteamId\n      }),"
    )
    with open('static/js/main.js', 'w', encoding='utf-8') as f:
        f.write(js)
    print("Patched main.js")

# 3. Update app.py payload parser
with open('app.py', 'r', encoding='utf-8') as f:
    py = f.read()

if "filterStickers" not in py:
    py = py.replace(
        '        "normal": data.get("filterNormal", False)\n    }',
        '        "normal": data.get("filterNormal", False),\n'
        '        "stickers": data.get("filterStickers", ""),\n'
        '        "charm": data.get("filterCharm", ""),\n'
        '        "source": data.get("filterSource", ""),\n'
        '        "steamId": data.get("filterSteamId", "")\n    }'
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(py)
    print("Patched app.py parser")

# 4. Update app.py Selenium logic
with open('app.py', 'r', encoding='utf-8') as f:
    py = f.read()

additional_selenium = """
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
"""

if "steamId" not in py:
    py = py.replace(
        '                    if filters.get("normal", False):\n                        cb = WebDriverWait(driver, 3).until(\n                            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), \'Normal\')]/ancestor::mat-checkbox//input[@type=\'checkbox\']"))\n                        )\n                        driver.execute_script("arguments[0].scrollIntoView({behavior: \'smooth\', block: \'center\'});", cb)\n                        time.sleep(0.2)\n                        driver.execute_script("if(!arguments[0].checked) arguments[0].click();", cb)',
        '                    if filters.get("normal", False):\n                        cb = WebDriverWait(driver, 3).until(\n                            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), \'Normal\')]/ancestor::mat-checkbox//input[@type=\'checkbox\']"))\n                        )\n                        driver.execute_script("arguments[0].scrollIntoView({behavior: \'smooth\', block: \'center\'});", cb)\n                        time.sleep(0.2)\n                        driver.execute_script("if(!arguments[0].checked) arguments[0].click();", cb)\n' + additional_selenium
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(py)
    print("Patched app.py selenium")
