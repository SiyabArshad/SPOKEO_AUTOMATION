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


def format_url(address, city, state):
    addr = re.sub(r'[^\w\s-]', '', address.strip())
    addr = re.sub(r'\s+', '-', addr)
    city_formatted = '-'.join([w.capitalize() for w in city.strip().lower().split()])
    state_formatted = state.strip().upper()
    return f"https://www.spokeo.com/{state_formatted}/{city_formatted}/{addr}"


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


def scrape_spokeo(address, city, state):
    target_url = format_url(address, city, state)
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

        # Extract contacts
        results = driver.execute_script("""
            const results = [];
            const nameElements = document.querySelectorAll('h2, h3, .name, [class*="Name"], [class*="Title"]');
            nameElements.forEach(nameEl => {
                const name = nameEl.textContent.trim();
                if (!name || name.length > 50 || name.split(' ').length > 6) return;

                let card = nameEl.closest('article') || nameEl.closest('[class*="card"]');
                if (!card && nameEl.parentElement && nameEl.parentElement.parentElement) {
                    card = nameEl.parentElement.parentElement;
                }
                if (!card) return;

                const cardText = card.textContent || '';
                const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
                const emails = cardText.match(emailRegex) || [];

                const phoneRegex = /(?:\\+?1[-.\\s]?)?\\(?[2-9]\\d{2}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}/g;
                const phones = cardText.match(phoneRegex) || [];

                const links = card.querySelectorAll('a');
                const socials = [];
                links.forEach(link => {
                    const href = link.href.toLowerCase();
                    if (href.includes('facebook.com')) socials.push({ type: 'facebook', value: href });
                    if (href.includes('instagram.com')) socials.push({ type: 'instagram', value: href });
                });

                [...new Set(emails)].forEach(e => results.push({ name, type: 'email', value: e }));
                [...new Set(phones)].forEach(p => results.push({ name, type: 'phone', value: p }));
                socials.forEach(s => results.push({ name, type: s.type, value: s.value }));
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
