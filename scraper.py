import os
import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Credentials
SPOKEO_EMAIL = os.environ.get("SPOKEO_EMAIL", "admin@sanjeevanidesifoodhub.com")
SPOKEO_PASSWORD = os.environ.get("SPOKEO_PASSWORD", "Developer@3690")

# Dedicated session folder inside the project
PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spokeo_profile")


def format_url(address, city, state):
    addr = re.sub(r'[^\w\s-]', '', address.strip())
    addr = re.sub(r'\s+', '-', addr)
    city_formatted = '-'.join([w.capitalize() for w in city.strip().lower().split()])
    state_formatted = state.strip().upper()
    return f"https://www.spokeo.com/{state_formatted}/{city_formatted}/{addr}"


def get_driver():
    """Launch Chrome with a dedicated local profile (session persists between runs)."""
    options = Options()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


def accept_cookie_popup(driver):
    """Dismiss any cookie consent or terms popup if present."""
    cookie_selectors = [
        "button#onetrust-accept-btn-handler",
        "button[aria-label*='Accept']",
        "button[aria-label*='accept']",
        "[id*='cookie'] button",
        "[class*='cookie'] button",
        "button[data-testid*='accept']",
    ]
    for selector in cookie_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, selector)
            btn.click()
            print(f"Accepted cookie popup via: {selector}")
            time.sleep(1)
            return
        except NoSuchElementException:
            pass


def handle_login_modal(driver):
    """
    If a login modal/popup is visible on the page, fill in credentials and submit.
    Returns True if login was performed, False if not needed.
    """
    time.sleep(3)
    
    # Common login modal selectors on Spokeo
    login_modal_selectors = [
        "input[type='email']",
        "input[name='email']",
        "#email",
        "input[placeholder*='email' i]",
        "input[placeholder*='Email' i]",
    ]

    email_field = None
    for selector in login_modal_selectors:
        try:
            email_field = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
            )
            break
        except TimeoutException:
            pass

    if email_field is None:
        print("No login form found — already logged in.")
        return False

    print("Login form detected — filling in credentials...")

    # Fill email
    email_field.clear()
    email_field.send_keys(SPOKEO_EMAIL)

    # Fill password
    password_selectors = [
        "input[type='password']",
        "input[name='password']",
        "#password",
        "input[placeholder*='password' i]",
    ]
    password_field = None
    for selector in password_selectors:
        try:
            password_field = driver.find_element(By.CSS_SELECTOR, selector)
            break
        except NoSuchElementException:
            pass

    if password_field:
        password_field.clear()
        password_field.send_keys(SPOKEO_PASSWORD)

    # Submit
    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button[class*='login' i]",
        "button[class*='sign' i]",
        "button[data-testid*='login']",
        "button[data-testid*='submit']",
    ]
    for selector in submit_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, selector)
            btn.click()
            print("Login submitted.")
            time.sleep(5)
            return True
        except NoSuchElementException:
            pass

    print("Warning: Could not find submit button.")
    return False


def scrape_spokeo(address, city, state):
    url = format_url(address, city, state)
    print(f"Navigating to: {url}")

    driver = get_driver()
    try:
        # Go directly to the property page
        driver.get(url)
        time.sleep(4)

        # Accept any cookie popup first
        accept_cookie_popup(driver)

        # Check for and handle any login modal/popup
        handle_login_modal(driver)

        # After login, we may still be on the page or redirected back — re-navigate if needed
        if driver.current_url != url:
            print(f"Redirected after login. Navigating back to: {url}")
            driver.get(url)
            time.sleep(5)
            accept_cookie_popup(driver)

        # Wait for the main body content
        time.sleep(3)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "no records found" in page_text or "could not find a match" in page_text:
            driver.quit()
            return []

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

        # Global dedup
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
