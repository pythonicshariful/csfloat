import re

with open('app.py', 'r', encoding='utf-8') as f:
    py = f.read()

# Add the filter logic after the sidebar is opened
filter_logic = """
            # ── Step 11.5: Apply Filters if provided ─────
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
                    print(f"Error applying filters: {e}")
"""

if "Step 11.5: Apply Filters if provided" not in py:
    py = py.replace(
        "            time.sleep(1)\n        except Exception:\n            pass  # Filter button not found or sidebar did not open",
        "            time.sleep(1)\n" + filter_logic + "\n        except Exception:\n            pass  # Filter button not found or sidebar did not open"
    )

    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(py)
    print("Patched app.py with filter logic")
