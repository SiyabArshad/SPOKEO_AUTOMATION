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

        # Extract contacts from specific sections only (Property Owners and Current Residents)
        results = driver.execute_script("""
            const results = [];
            
            // Find all section-like containers
            const containers = document.querySelectorAll('section, [class*="section"], [class*="Section"]');
            
            containers.forEach(container => {
                const header = container.querySelector('h1, h2, h3, h4, .title, [class*="title"]');
                if (!header) return;
                
                const headerText = header.innerText.toLowerCase();
                // Only process Property Owners and Current Residents
                if (headerText.includes('property owner') || headerText.includes('current resident')) {
                    if (headerText.includes('past')) return; // Skip past owners/residents if needed

                    const cards = container.querySelectorAll('article, [class*="card"], [class*="Card"], [class*="profile"]');
                    cards.forEach(card => {
                        const nameEl = card.querySelector('h2, h3, h4, .name, [class*="name"], [class*="Name"]');
                        if (!nameEl) return;

                        let name = nameEl.innerText.split('\\n')[0].split(',')[0].replace(/Highest Quality/g, '').trim();
                        if (!name || name.length < 3 || name.toLowerCase().includes('owner') || name.toLowerCase().includes('resident')) return;

                        const cardText = card.innerText || '';
                        
                        // Emails
                        const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.(com|net|org|edu|gov|us|info|biz|co)/gi;
                        const emails = cardText.match(emailRegex) || [];

                        // Phones with strict digit boundary check
                        const phoneCandidateRegex = /(?:\\+?1[-.\\s]?)?\\(?[2-9]\\d{2}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}/g;
                        const matches = cardText.matchAll(phoneCandidateRegex);
                        const phones = [];
                        for (const match of matches) {
                            const start = match.index;
                            const end = start + match[0].length;
                            const isPrecededByDigit = start > 0 && /\\d/.test(cardText[start - 1]);
                            const isFollowedByDigit = end < cardText.length && /\\d/.test(cardText[end]);
                            if (!isPrecededByDigit && !isFollowedByDigit) {
                                phones.push(match[0]);
                            }
                        }

                        [...new Set(emails)].forEach(e => results.push({ name, type: 'email', value: e }));
                        [...new Set(phones)].forEach(p => results.push({ name, type: 'phone', value: p }));
                    });
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
