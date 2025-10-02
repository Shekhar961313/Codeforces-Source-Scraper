import os
import time
import requests
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
CF_HANDLE = os.environ.get("CF_HANDLE")
CF_CLEARANCE = os.environ.get("CF_CLEARANCE")
SESSION_ID = os.environ.get("SESSION_ID")

PROBLEM_LEVEL_FOLDERS = ["A", "B", "C", "D", "E", "F", "G", "H"]
OTHER_FOLDER = "Other_Problems"
# --- END OF CONFIGURATION ---


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

def scrape_source_code(session, submission_url):
    """Scrapes the source code from a submission URL using a logged-in session."""
    try:
        response = session.get(submission_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        code_element = soup.find("pre", id="program-source-text")
        if not code_element:
            print(f"Could not find source code element on {submission_url}")
            return None
        return code_element.text
    except Exception as e:
        print(f"Could not scrape source code from {submission_url}. Error: {e}")
        return None

def get_folder_for_level(problem_index):
    """Determines folder based on problem index (A, B, C...)."""
    if problem_index and problem_index[0].isalpha():
        return problem_index[0].upper()
    return OTHER_FOLDER

def main():
    if not all([CF_HANDLE, CF_CLEARANCE, SESSION_ID]):
        print("Error: Missing required secrets (CF_HANDLE, CF_CLEARANCE, SESSION_ID).")
        return

    # Create a session and set the cookies to bypass security
    session = requests.Session()
    session.cookies.set('cf_clearance', CF_CLEARANCE)
    session.cookies.set('JSESSIONID', SESSION_ID)
    session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    
    solved_submissions = get_solved_problems(CF_HANDLE)
    if not solved_submissions:
        print("No solved problems found.")
        return

    for folder in PROBLEM_LEVEL_FOLDERS + [OTHER_FOLDER]:
        os.makedirs(folder, exist_ok=True)

    for problem_id, sub in solved_submissions.items():
        problem = sub['problem']
        problem_index = problem['index']
        
        folder_name = get_folder_for_level(problem_index)
        problem_name = "".join(c for c in problem['name'] if c.isalnum() or c in (' ', '_')).rstrip()
        file_name = f"{problem['contestId']}{problem_index}-{problem_name}.cpp" # Assuming C++
        file_path = os.path.join(folder_name, file_name)

        if not os.path.exists(file_path):
            print(f"Scraping new solution for: {problem_name} ({problem_id})")
            submission_url = f"https://codeforces.com/contest/{problem['contestId']}/submission/{sub['id']}"
            source_code = scrape_source_code(session, submission_url)
            
            if source_code:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(source_code)
                print(f"Successfully saved source code to {file_path}")
            else:
                print(f"Failed to get source code for {problem_name}")
            time.sleep(2) # Be respectful to servers

    print("Scraping process complete.")

if __name__ == '__main__':
    main()