import re

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

if "Paint Seed" not in py:
    py = py.replace(
        '                    if max_float:\n                        set_ng_input("input[formcontrolname=\'max\']", max_float)',
        '                    if max_float:\n                        set_ng_input("input[formcontrolname=\'max\']", max_float)\n' + additional_selenium
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(py)
    print("Patched app.py selenium")
