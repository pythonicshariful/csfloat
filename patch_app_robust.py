import re

with open('app.py', 'r', encoding='utf-8') as f:
    py = f.read()

# I will replace the "Step 11.5: Apply Filters if provided" block with a more robust version using JS.

old_block = """            # ── Step 11.5: Apply Filters if provided ─────
            if filters:
                try:
                    # Min Float
                    min_float = filters.get("minFloat", "")
                    if min_float:
                        min_input = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[formcontrolname='min']"))
                        )
                        min_input.clear()
                        min_input.send_keys(min_float)
                        
                    # Max Float
                    max_float = filters.get("maxFloat", "")
                    if max_float:
                        max_input = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[formcontrolname='max']"))
                        )
                        max_input.clear()
                        max_input.send_keys(max_float)
                        
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
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-select[formcontrolname='order']"))
                            )
                            driver.execute_script("arguments[0].click();", sort_select)
                            time.sleep(0.5)
                            
                            # Find the mat-option in the CDK overlay
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
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-select[formcontrolname='rarity']"))
                            )
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
                    print(f"Error applying filters: {e}")"""

new_block = """            # ── Step 11.5: Apply Filters if provided ─────
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
                    print(f"Error applying filters: {e}")"""

if "Step 11.5: Apply Filters if provided" in py:
    py = py.replace(old_block, new_block)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(py)
    print("Patched app.py with robust JS filter logic")
