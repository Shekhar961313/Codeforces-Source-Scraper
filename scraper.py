import os
import time
import requests
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# --- CONFIGURATION ---
# These will be read from GitHub Secrets
CF_HANDLE = os.environ.get("CF_HANDLE")
CF_USERNAME = os.environ.get("CF_USERNAME")
CF_PASSWORD = os.environ.get("CF_PASSWORD")
LOGIN_URL = "https://codeforces.com/enter"
# --- END OF CONFIGURATION ---


def login(driver, username, password, handle):
    """Logs into Codeforces using an undetected chromedriver session."""
    print("Attempting to log in...")
    try:
        driver.get(LOGIN_URL)
        time.sleep(5) # Wait for any initial checks

        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "handleOrEmail")))
        handle_input = driver.find_element(By.ID, "handleOrEmail")
        password_input = driver.find_element(By.ID, "password")
        login_button = driver.find_element(By.CLASS_NAME, "submit")

        handle_input.send_keys(username)
        password_input.send_keys(password)
        login_button.click()

        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, f"//a[contains(@href, '/profile/{handle}')]")))
        print("Login successful!")
        return True
    except Exception as e:
        print(f"An error occurred during login: {e}")
        return False

def get_solved_problems(handle):
    """Fetches all 'OK' submissions from the Codeforces API."""
    print(f"Fetching solved problems for {handle}...")
    api_url = f"https://codeforces.com/api/user.status?handle={handle}"
    try:
        response = requests.get(api_url)
        data = response.json()
        if data['status'] != 'OK':
            print(f"API Error: {data.get('comment')}")
            return {}
        
        solved = {}
        for sub in data['result']:
            if sub.get('verdict') == 'OK' and 'contestId' in sub['problem']:
                problem_id = f"{sub['problem']['contestId']}{sub['problem']['index']}"
                if problem_id not in solved or sub['creationTimeSeconds'] > solved[problem_id]['creationTimeSeconds']:
                    solved[problem_id] = sub
        print(f"Found {len(solved)} unique solved problems.")
        return solved
    except Exception as e:
        print(f"An error occurred fetching API data: {e}")
        return {}

def scrape_source_code(driver, submission_url):
    """Navigates to a submission URL and scrapes the source code."""
    try:
        driver.get(submission_url)
        # The source code is inside a <pre> tag with the id 'program-source-text'
        code_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "program-source-text"))
        )
        return code_element.text
    except Exception as e:
        print(f"Could not scrape source code from {submission_url}. Error: {e}")
        return None

def main():
    if not all([CF_HANDLE, CF_USERNAME, CF_PASSWORD]):
        print("Error: Missing one or more required environment variables (CF_HANDLE, CF_USERNAME, CF_PASSWORD).")
        return

    # Use undetected_chromedriver in headless mode for the server
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = uc.Chrome(options=options)

    try:
        if not login(driver, CF_USERNAME, CF_PASSWORD, CF_HANDLE):
            return

        solved_submissions = get_solved_problems(CF_HANDLE)
        if not solved_submissions:
            print("No solved problems found.")
            return

        # Create a folder to store the code
        os.makedirs("solutions", exist_ok=True)

        for problem_id, sub in solved_submissions.items():
            problem = sub['problem']
            contest_id = problem['contestId']
            problem_index = problem['index']
            problem_name = "".join(c for c in problem['name'] if c.isalnum() or c in (' ', '_')).rstrip()
            submission_id = sub['id']
            
            file_name = f"{contest_id}{problem_index}-{problem_name}.cpp" # Assuming C++
            file_path = os.path.join("solutions", file_name)

            if not os.path.exists(file_path):
                print(f"Scraping new solution for: {problem_name} ({problem_id})")
                submission_url = f"https://codeforces.com/contest/{contest_id}/submission/{submission_id}"
                source_code = scrape_source_code(driver, submission_url)
                
                if source_code:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(source_code)
                    print(f"Successfully saved source code to {file_path}")
                else:
                    print(f"Failed to get source code for {problem_name}")
                time.sleep(2) # Be respectful to Codeforces servers

    finally:
        driver.quit()
        print("Scraping process complete.")

if __name__ == '__main__':
    main()