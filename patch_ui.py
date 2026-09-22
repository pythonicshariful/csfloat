import re

# 1. Patch index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

filters_html = """
      <!-- ===== FILTERS ROW ===== -->
      <div class="card" style="margin-top: 16px;">
        <div class="card-header">
          <div class="card-icon icon-blue">
            <svg viewBox="0 0 24 24" fill="none"><path d="M4 6h16M7 12h10M10 18h4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </div>
          <div>
            <div class="card-title">Search Filters</div>
            <div class="card-desc">Applied automatically to CSFloat</div>
          </div>
        </div>
        
        <div style="display: flex; gap: 16px; margin-bottom: 12px;">
          <div style="flex: 1;">
            <label style="display:block; font-size:.75rem; color:var(--text-3); margin-bottom:4px;">Sort By</label>
            <select class="url-input" id="filterSort" style="margin-bottom:0; cursor:pointer;">
              <option value="">(Default)</option>
              <option value="0">Lowest Float</option>
              <option value="1">Highest Float</option>
              <option value="2">Lowest Price</option>
              <option value="3">Highest Price</option>
              <option value="4">Recent</option>
            </select>
          </div>
          <div style="flex: 1;">
            <label style="display:block; font-size:.75rem; color:var(--text-3); margin-bottom:4px;">Rarity</label>
            <select class="url-input" id="filterRarity" style="margin-bottom:0; cursor:pointer;">
              <option value="">Any</option>
              <option value="1">Consumer Grade</option>
              <option value="2">Industrial Grade</option>
              <option value="3">Mil-Spec Grade</option>
              <option value="4">Restricted</option>
              <option value="5">Classified</option>
              <option value="6">Covert</option>
              <option value="7">Contraband</option>
            </select>
          </div>
        </div>

        <div style="display: flex; gap: 16px;">
          <div style="flex: 1;">
            <label style="display:block; font-size:.75rem; color:var(--text-3); margin-bottom:4px;">Min Float</label>
            <input type="number" class="url-input" id="filterMinFloat" placeholder="e.g. 0.01" step="0.001" min="0" max="1" style="margin-bottom:0;" />
          </div>
          <div style="flex: 1;">
            <label style="display:block; font-size:.75rem; color:var(--text-3); margin-bottom:4px;">Max Float</label>
            <input type="number" class="url-input" id="filterMaxFloat" placeholder="e.g. 0.05" step="0.001" min="0" max="1" style="margin-bottom:0;" />
          </div>
        </div>
      </div>
"""

if "<!-- ===== FILTERS ROW ===== -->" not in html:
    html = html.replace("      </div><!-- /cards-row -->", "      </div><!-- /cards-row -->\n" + filters_html)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Patched index.html")

# 2. Patch main.js
with open('static/js/main.js', 'r', encoding='utf-8') as f:
    js = f.read()

if "filterSort" not in js:
    # Find launch()
    js = js.replace(
        "const url     = document.getElementById('targetUrl').value.trim() || 'https://csfloat.com/db';",
        "const url     = document.getElementById('targetUrl').value.trim() || 'https://csfloat.com/db';\n"
        "  const filterSort = document.getElementById('filterSort').value;\n"
        "  const filterRarity = document.getElementById('filterRarity').value;\n"
        "  const filterMinFloat = document.getElementById('filterMinFloat').value;\n"
        "  const filterMaxFloat = document.getElementById('filterMaxFloat').value;\n"
    )
    
    # Find the payload body
    js = js.replace(
        "        url:      url,\n      }),",
        "        url:      url,\n"
        "        filterSort,\n"
        "        filterRarity,\n"
        "        filterMinFloat,\n"
        "        filterMaxFloat\n"
        "      }),"
    )
    with open('static/js/main.js', 'w', encoding='utf-8') as f:
        f.write(js)
    print("Patched main.js")

# 3. Patch app.py (adding filter values to payload and launch_profile args)
with open('app.py', 'r', encoding='utf-8') as f:
    py = f.read()

if "filterSort" not in py:
    # Update launch_profile signature
    py = py.replace(
        "def launch_profile(profile_index: int, account: dict, num_tabs: int):",
        "def launch_profile(profile_index: int, account: dict, num_tabs: int, filters: dict = None):"
    )
    
    # Update launch() route
    py = py.replace(
        'raw_cookies  = data.get("cookies",      "")',
        'raw_cookies  = data.get("cookies",      "")\n'
        '    filters = {\n'
        '        "sort": data.get("filterSort", ""),\n'
        '        "rarity": data.get("filterRarity", ""),\n'
        '        "minFloat": data.get("filterMinFloat", ""),\n'
        '        "maxFloat": data.get("filterMaxFloat", "")\n'
        '    }'
    )
    
    py = py.replace(
        "ok, err = launch_profile(idx, acc, num_tabs)",
        "ok, err = launch_profile(idx, acc, num_tabs, filters)"
    )
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(py)
    print("Patched app.py (Part 1)")
