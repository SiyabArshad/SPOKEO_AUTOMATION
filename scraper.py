import os
import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Credentials
SPOKEO_EMAIL = os.environ.get("SPOKEO_EMAIL", "admin@sanjeevanidesifoodhub.com")
SPOKEO_PASSWORD = os.environ.get("SPOKEO_PASSWORD", "Developer@3690")

LOGIN_URL = "https://www.spokeo.com/login?url=%2F"
PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spokeo_profile")


def format_url(address, city, state, zipcode=""):
    addr_slug = re.sub(r'[^\w\s-]', '', address.strip())
    addr_slug = re.sub(r'\s+', '-', addr_slug)
    
    city_trimmed = city.strip()
    state_trimmed = state.strip().upper()
    
    if city_trimmed:
        city_formatted = '-'.join([w.capitalize() for w in city_trimmed.lower().split()])
        return f"https://www.spokeo.com/{state_trimmed}/{city_formatted}/{addr_slug}"
    else:
        # Fallback to search if city is missing to avoid double slashes and land on the right page via search
        query = f"{address.strip()} {state_trimmed} {zipcode.strip()}".strip().replace(' ', '+')
        return f"https://www.spokeo.com/search?q={query}"


def get_driver():
    """Launch Chrome with a dedicated local profile."""
    options = Options()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


def ensure_logged_in(driver):
    """
    Always navigate to the login page.
    - If the login form appears → fill credentials and submit.
    - If already logged in → Spokeo redirects us away from /login automatically.
    """
    print("Navigating to Spokeo login page...")
    driver.get(LOGIN_URL)
    time.sleep(4)

    # Check if we are still on the login page by looking for the email input
    try:
        email_field = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], #email"))
        )
        # Login form is visible — we are NOT logged in
        print("Login form found — filling credentials...")
        email_field.clear()
        email_field.send_keys(SPOKEO_EMAIL)
        time.sleep(0.5)

        from selenium.webdriver.common.keys import Keys
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password'], #password")
        password_field.clear()
        password_field.send_keys(SPOKEO_PASSWORD)
        time.sleep(0.5)

        # Hit ENTER on the password field to submit the form reliably
        password_field.send_keys(Keys.RETURN)
        print("Login submitted via ENTER key. Waiting for redirect...")
        time.sleep(6)
        print(f"Landed on: {driver.current_url}")

    except TimeoutException:
        # Email input not found — we are already logged in and were redirected
        print(f"Already logged in (redirected to: {driver.current_url})")


def scrape_spokeo(address, city, state, zipcode=""):
    target_url = format_url(address, city, state, zipcode)
    print(f"Target URL: {target_url}")

    driver = get_driver()
    try:
        # Always check login via the login page
        ensure_logged_in(driver)

        # Navigate to the property page
        print(f"Navigating to property: {target_url}")
        driver.get(target_url)
        time.sleep(6)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "no records found" in page_text or "could not find a match" in page_text:
            driver.quit()
            return []

        # Extract contacts using "Contact Info" as an anchor point
        results = driver.execute_script("""
            const results = [];
            const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.(com|net|org|edu|gov|us|info|biz|co)/gi;
            const phoneCandidateRegex = /(?:\\+?1[-.\\s]?)?\\(?[2-9]\\d{2}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}/g;

            // 1. Find all elements that serve as a "Contact Info" header
            const anchors = Array.from(document.querySelectorAll('*')).filter(el => {
                const t = (el.innerText || '').trim().toLowerCase();
                return (t === 'contact info' || t === 'contact information') && el.children.length === 0;
            });

            anchors.forEach(anchor => {
                // 2. Traverse up from the anchor to find the container for this person
                let container = anchor.parentElement;
                // Go up to 6 levels to find a block containing a name and owner/resident label
                for (let i = 0; i < 6; i++) {
                    if (!container || container.tagName === 'BODY') break;
                    
                    const text = container.innerText || '';
                    const lowerText = text.toLowerCase();
                    
                    // We only want Current Owners/Residents (skip Past ones)
                    if ((lowerText.includes('owner') || lowerText.includes('resident')) && !lowerText.includes('past')) {
                        
                        // 3. Extract the person's name
                        let name = '';
                        // Strategy A: Look for a header element inside the container
                        const nameEl = container.querySelector('h1, h2, h3, h4, .name, [class*="name"], [class*="Name"], strong');
                        if (nameEl && nameEl.innerText.length > 2) {
                            name = nameEl.innerText.split('\\n')[0].split(',')[0].replace(/Highest Quality/g, '').trim();
                        }
                        
                        // Strategy B: If Strategy A failed or returned a role (like "Current Owner"), 
                        // parse the text lines for the actual name
                        if (!name || name.length < 3 || name.toLowerCase().includes('owner') || name.toLowerCase().includes('resident')) {
                            const lines = text.split('\\n').map(l => l.trim()).filter(l => l);
                            for (let j = 0; j < lines.length; j++) {
                                const l = lines[j].toLowerCase();
                                if (l.includes('owner') || l.includes('resident')) {
                                    if (j + 1 < lines.length && lines[j+1].length > 2) {
                                        name = lines[j+1].split(',')[0].replace(/Highest Quality/g, '').trim();
                                        break;
                                    }
                                }
                            }
                        }

                        // 4. If we have a valid name, extract the contact data from this block
                        if (name && name.length > 2 && !name.toLowerCase().includes('owner') && !name.toLowerCase().includes('resident')) {
                            const emails = text.match(emailRegex) || [];
                            const matches = text.matchAll(phoneCandidateRegex);
                            const phones = [];
                            for (const match of matches) {
                                const start = match.index;
                                const end = start + match[0].length;
                                // Digit boundary check to avoid pids/internal IDs
                                const isPrecededByDigit = start > 0 && /\\d/.test(text[start - 1]);
                                const isFollowedByDigit = end < text.length && /\\d/.test(text[end]);
                                if (!isPrecededByDigit && !isFollowedByDigit) {
                                    phones.push(match[0]);
                                }
                            }
                            
                            [...new Set(emails)].forEach(e => results.push({ name, type: 'email', value: e }));
                            [...new Set(phones)].forEach(p => results.push({ name, type: 'phone', value: p }));
                            
                            // If we found data, we can stop traversing up for this anchor
                            if (emails.length > 0 || phones.length > 0) return;
                        }
                    }
                    container = container.parentElement;
                }
            });
            return results;
        """)

        driver.quit()

        # Dedup
        unique_results = []
        seen = set()
        for item in results:
            val = re.sub(r'[-.\s()]', '', item['value']) if item['type'] == 'phone' else item['value']
            key = f"{item['name']}-{item['type']}-{val}"
            if key not in seen:
                seen.add(key)
                unique_results.append(item)

        return unique_results

    except Exception as e:
        try:
            driver.quit()
        except Exception:
            pass
        raise e
