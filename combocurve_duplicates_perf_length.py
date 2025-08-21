from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import glob
import os
import pandas as pd

USERNAME = 'gtolly@tildencapitalllc.com'
PASSWORD = 'Tildencap2025'
LOGIN_URL = 'https://tilden.combocurve.com'

chrome_options = Options()
chrome_options.add_argument('--start-maximized')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-extensions')
chrome_options.add_argument('--disable-web-security')
chrome_options.add_argument('--allow-running-insecure-content')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

CHROMEDRIVER_PATH = 'chromedriver.exe'  # Assumes chromedriver.exe is in the current directory

try:
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    # Remove the "Chrome is being controlled by automated test software" banner
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    print("Chrome WebDriver initialized successfully")
except Exception as e:
    print(f"Failed to initialize Chrome WebDriver: {e}")
    print("Please check that chromedriver.exe is in the current directory and compatible with your Chrome version")
    raise

def login_to_combocurve_with_microsoft():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Login attempt {attempt + 1}/{max_retries}")
            driver.get(LOGIN_URL)
            
            # Wait for the email field to be visible
            email_input = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.NAME, 'loginfmt'))
            )
            email_input.clear()
            email_input.send_keys(USERNAME)
            
            next_btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, 'idSIButton9'))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            next_btn.click()

            # Wait for the password field to be visible
            password_input = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.NAME, 'passwd'))
            )
            password_input.clear()
            password_input.send_keys(PASSWORD)
            signin_btn = driver.find_element(By.ID, 'idSIButton9')
            signin_btn.click()

            # Optionally handle "Stay signed in?"
            try:
                yes_btn = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Yes'] | //button[normalize-space(text())='Yes']"))
                )
                yes_btn.click()
                print('Clicked the "Yes" button by text.')
            except Exception as e:
                print('Failed to click the "Yes" button by text:', e)

            # Wait for ComboCurve dashboard or main page to load
            WebDriverWait(driver, 15).until(lambda d: 'dashboard' in d.current_url or 'combocurve' in d.current_url)
            print('Login process completed successfully.')
            return
            
        except Exception as e:
            print(f"Login attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("All login attempts failed. Please check your credentials and internet connection.")
                raise

def navigate_to_project():
    # Click the hamburger menu using data-testid='drawer-button'
    hamburger = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='drawer-button']"))
    )
    hamburger.click()

    # Wait for the menu to appear and click 'Projects'
    projects_menu = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Projects')]"))
    )
    projects_menu.click()

    work_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//div[@title='02 - Eagleford Legacy']/ancestor::*[@role='row'][1]//button[contains(., 'Work')]"
        ))
    )
    work_button.click()

    project_wells_tab = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//a[contains(@href, '/manage-wells') and .//span[contains(text(), 'Project Wells')]]"
        ))
    )
    project_wells_tab.click()

def export_well_data():
    # First, make sure we're on the Project Wells tab
    project_wells_tab = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//a[contains(@href, '/manage-wells') and .//span[contains(text(), 'Project Wells')]]"
        ))
    )
    project_wells_tab.click()
    
    # Wait a moment for the page to load
    time.sleep(2)

    # Set your downloads folder and the file pattern
    download_folder = r"C:\Users\GraceTolly\Downloads"
    pattern = os.path.join(download_folder, "well_02___Eagleford_Legacy_*.csv")

    # Wait for the file to appear and be fully downloaded
    max_wait_time = 60  # Maximum wait time in seconds
    start_time = time.time()
    latest_file = None
    df = None

    while time.time() - start_time < max_wait_time:
        list_of_files = glob.glob(pattern)
        if list_of_files:
            current_latest = max(list_of_files, key=os.path.getctime)
            if current_latest != latest_file:
                latest_file = current_latest
                print(f"Found new file: {latest_file}")
                time.sleep(3)  # Wait a bit more to ensure file is fully written
                try:
                    df = pd.read_csv(latest_file)
                    print(f"Successfully loaded file with {len(df)} rows")
                    print(df.head())
                    break
                except Exception as e:
                    print(f"File not ready yet, retrying... Error: {e}")
                    time.sleep(2)
            else:
                time.sleep(1)
        else:
            print("No matching files found yet, waiting...")
            time.sleep(2)

    if df is None:
        print("No files found in the downloads folder after waiting.")
        raise Exception("Export file not found or could not be loaded")
    
    return df

def process_duplicates_by_perf_length(df):
    #process full well list for duplicates
    df = df[["Well Name", "API 14", "Production Method", "Perf Lateral Length"]]

    # Create API10 column (first 10 digits of API 14)
    df["API10"] = df["API 14"].astype(str).str[:10]

    # Find duplicates based on API10 (wells with same first 10 digits)
    duplicates = df[df.duplicated(subset=["API10"], keep=False)].sort_values(by="API10")

    # Step 1: Filter to only duplicated API10 rows (all occurrences)
    dups = df[df.duplicated(subset=["API10"], keep=False)].copy()

    # Step 2: For each set of duplicates, keep only the row with the highest "Perf Lateral Length"
    def keep_highest_perf_length(group):
        # Convert Perf Lateral Length to numeric, handling any non-numeric values
        group["Perf Lateral Length"] = pd.to_numeric(group["Perf Lateral Length"], errors='coerce')
        
        # Find the row with the highest Perf Lateral Length
        max_length = group["Perf Lateral Length"].max()
        
        # If all values are NaN, keep all rows (no preference)
        if pd.isna(max_length):
            return group
        
        # Keep only the row(s) with the highest Perf Lateral Length
        return group[group["Perf Lateral Length"] == max_length]

    # Apply to duplicates - keep only the highest Perf Lateral Length for each API10
    filtered_duplicates = dups.groupby("API10", group_keys=False).apply(keep_highest_perf_length).reset_index(drop=True)

    # Find all rows that should be removed (duplicates minus the ones we kept)
    all_duplicate_rows = dups.copy()
    kept_rows = filtered_duplicates.copy()

    # Create a composite key to identify which rows to remove
    all_duplicate_rows['composite_key'] = all_duplicate_rows['API10'] + '_' + all_duplicate_rows['API 14'].astype(str)
    kept_rows['composite_key'] = kept_rows['API10'] + '_' + kept_rows['API 14'].astype(str)

    # Remove the rows we want to keep from the list of rows to remove
    rows_to_remove = all_duplicate_rows[~all_duplicate_rows['composite_key'].isin(kept_rows['composite_key'])].copy()

    # Clean up the temporary column
    rows_to_remove = rows_to_remove.drop(columns=['composite_key', 'API10'])

    # Use rows_to_remove as our reversed_filtered
    reversed_filtered = rows_to_remove

    # Export to CSV
    reversed_filtered.to_csv('duplicate wells deleted perf length.csv', index=False)

    print(f"Found {len(reversed_filtered)} wells to remove based on Perf Lateral Length")
    
    return reversed_filtered

def remove_duplicates_from_ui(reversed_filtered):
    #remove duplicates from well list
    total_wells = len(reversed_filtered)
    print(f"Starting removal of {total_wells} duplicate wells...")
    
    for index, api in enumerate(reversed_filtered["API 14"], 1):
        print(f"Processing well {index}/{total_wells}: API 14 {api}")
        
        api_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[aria-label='API 14 Filter Input']"))
        )
        api_input.clear()
        api_input.send_keys(str(api))
        api_input.send_keys(Keys.ENTER)

        # Wait for the row with the correct API 14 to appear
        try:
            filtered_row = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//div[@role='row']//div[contains(text(), '{api}')]"))
            )
            # Click the parent row container
            row_container = filtered_row.find_element(By.XPATH, "./ancestor::div[@role='row'][1]")
            row_container.click()
        except Exception as e:
            print(f"  Could not click row for API 14 {api}: {e}")
            continue

        # 3. Click the "Remove Wells" button
        try:
            remove_wells_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Remove Wells')]"))
            )
            remove_wells_btn.click()
        except Exception as e:
            print(f"  Could not click Remove Wells for API 14 {api}: {e}")
            continue

        # 4. Click the confirmation "Remove" button in the modal/dialog
        try:
            confirm_remove_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[normalize-space(text())='Remove']"))
            )
            confirm_remove_btn.click()
            print(f"  ✓ Removed API 14: {api} ({index}/{total_wells})")
        except Exception as e:
            print(f"  Could not confirm removal for API 14 {api}: {e}")

        # After confirming removal
        try:
            WebDriverWait(driver, 10).until_not(
                EC.presence_of_element_located((By.XPATH, f"//div[@role='row']//div[contains(text(), '{api}')]"))
            )
        except Exception as e:
            print(f"  Row for API 14 {api} did not disappear as expected: {e}")

    print(f"✓ Completed! Successfully processed {total_wells} duplicate wells.")

def main():
    try:
        print("Starting ComboCurve duplicate well removal process...")
        
        # Login to ComboCurve
        print("Step 1: Logging into ComboCurve...")
        login_to_combocurve_with_microsoft()
        
        # Navigate to the project
        print("Step 2: Navigating to project...")
        navigate_to_project()
        
        # Export well data
        print("Step 3: Loading well data from file...")
        df = export_well_data()
        
        # Process duplicates using Perf Lateral Length
        print("Step 4: Processing duplicates...")
        reversed_filtered = process_duplicates_by_perf_length(df)
        
        # Remove duplicates from UI
        print("Step 5: Removing duplicates from UI...")
        remove_duplicates_from_ui(reversed_filtered)
        
        print("✓ All steps completed successfully!")
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        print("Stack trace:", e.__traceback__)
        
        # Try to take a screenshot for debugging
        try:
            if 'driver' in locals() and driver:
                screenshot_path = f"error_screenshot_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                print(f"Screenshot saved to: {screenshot_path}")
        except Exception as screenshot_error:
            print(f"Could not save screenshot: {screenshot_error}")
            
    finally:
        # Close the browser
        try:
            if 'driver' in locals() and driver:
                driver.quit()
                print("Browser closed successfully")
        except Exception as close_error:
            print(f"Error closing browser: {close_error}")

if __name__ == "__main__":
    main()
