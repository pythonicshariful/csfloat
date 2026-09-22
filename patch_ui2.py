import re

# 1. Update index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

additional_filters = """
        <div style="display: flex; gap: 16px; margin-top: 12px;">
          <div style="flex: 1;">
            <label style="display:block; font-size:.75rem; color:var(--text-3); margin-bottom:4px;">Paint Seed</label>
            <input type="number" class="url-input" id="filterPaintSeed" placeholder="e.g. 412" style="margin-bottom:0;" />
          </div>
          <div style="flex: 1;">
            <label style="display:block; font-size:.75rem; color:var(--text-3); margin-bottom:4px;">Min Age (days)</label>
            <input type="number" class="url-input" id="filterMinAge" placeholder="Min Age" style="margin-bottom:0;" />
          </div>
          <div style="flex: 1;">
            <label style="display:block; font-size:.75rem; color:var(--text-3); margin-bottom:4px;">Max Age (days)</label>
            <input type="number" class="url-input" id="filterMaxAge" placeholder="Max Age" style="margin-bottom:0;" />
          </div>
        </div>
        
        <div style="display: flex; gap: 16px; margin-top: 12px; align-items: center;">
          <div style="font-size:.85rem; color:var(--text-3);">Special:</div>
          <label style="display:flex; align-items:center; gap:6px; font-size:.85rem; cursor:pointer;">
            <input type="checkbox" id="filterStatTrak" /> StatTrak
          </label>
          <label style="display:flex; align-items:center; gap:6px; font-size:.85rem; cursor:pointer;">
            <input type="checkbox" id="filterSouvenir" /> Souvenir
          </label>
          <label style="display:flex; align-items:center; gap:6px; font-size:.85rem; cursor:pointer;">
            <input type="checkbox" id="filterNormal" /> Normal
          </label>
        </div>
"""

# Insert right before the closing div of the filters card
if "filterPaintSeed" not in html:
    html = html.replace(
        'id="filterMaxFloat" placeholder="e.g. 0.05" step="0.001" min="0" max="1" style="margin-bottom:0;" />\n          </div>\n        </div>\n      </div>',
        'id="filterMaxFloat" placeholder="e.g. 0.05" step="0.001" min="0" max="1" style="margin-bottom:0;" />\n          </div>\n        </div>\n' + additional_filters + '\n      </div>'
    )
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Patched index.html")

# 2. Update main.js
with open('static/js/main.js', 'r', encoding='utf-8') as f:
    js = f.read()

if "filterPaintSeed" not in js:
    # Add variable reads
    js = js.replace(
        "const filterMaxFloat = document.getElementById('filterMaxFloat').value;",
        "const filterMaxFloat = document.getElementById('filterMaxFloat').value;\n"
        "  const filterPaintSeed = document.getElementById('filterPaintSeed').value;\n"
        "  const filterMinAge = document.getElementById('filterMinAge').value;\n"
        "  const filterMaxAge = document.getElementById('filterMaxAge').value;\n"
        "  const filterStatTrak = document.getElementById('filterStatTrak').checked;\n"
        "  const filterSouvenir = document.getElementById('filterSouvenir').checked;\n"
        "  const filterNormal = document.getElementById('filterNormal').checked;"
    )
    
    # Add payload args
    js = js.replace(
        "        filterMinFloat,\n        filterMaxFloat\n      }),",
        "        filterMinFloat,\n        filterMaxFloat,\n"
        "        filterPaintSeed,\n        filterMinAge,\n        filterMaxAge,\n"
        "        filterStatTrak,\n        filterSouvenir,\n        filterNormal\n      }),"
    )
    with open('static/js/main.js', 'w', encoding='utf-8') as f:
        f.write(js)
    print("Patched main.js")

# 3. Update app.py payload parser
with open('app.py', 'r', encoding='utf-8') as f:
    py = f.read()

if "filterPaintSeed" not in py:
    py = py.replace(
        '        "maxFloat": data.get("filterMaxFloat", "")\n    }',
        '        "maxFloat": data.get("filterMaxFloat", ""),\n'
        '        "paintSeed": data.get("filterPaintSeed", ""),\n'
        '        "minAge": data.get("filterMinAge", ""),\n'
        '        "maxAge": data.get("filterMaxAge", ""),\n'
        '        "statTrak": data.get("filterStatTrak", False),\n'
        '        "souvenir": data.get("filterSouvenir", False),\n'
        '        "normal": data.get("filterNormal", False)\n    }'
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(py)
    print("Patched app.py parser")

# 4. Update app.py Selenium logic
with open('app.py', 'r', encoding='utf-8') as f:
    py = f.read()

additional_selenium = """
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
                    # Get checkbox input elements for the labels
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
"""

if "paintSeed" not in py:
    py = py.replace(
        '                    if max_float:\n                        set_ng_input("input[formcontrolname=\'max\']", max_float)',
        '                    if max_float:\n                        set_ng_input("input[formcontrolname=\'max\']", max_float)\n' + additional_selenium
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(py)
    print("Patched app.py selenium")
