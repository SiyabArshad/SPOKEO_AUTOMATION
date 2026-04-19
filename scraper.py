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
    # Use webdriver-manager to auto-download correct ChromeDriver for Chrome 147
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


def accept_any_popup(driver):
    """Dismiss cookie consent / terms popups if present."""
    selectors = [
        "button#onetrust-accept-btn-handler",
        "button[aria-label*='Accept']",
        "button[aria-label*='accept']",
        "[id*='cookie'] button",
        "[class*='cookie'] button",
    ]
    for sel in selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            btn.click()
            time.sleep(1)
            return
        except NoSuchElementException:
            pass


def perform_login(driver):
    """Fill and submit the Spokeo login form (works on the /login page)."""
    wait = WebDriverWait(driver, 15)

    print("Filling login form...")

    # Wait for email field
    email_field = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "input[type='email'], input[name='email'], #email, input[placeholder*='Email' i]")
    ))
    email_field.clear()
    email_field.send_keys(SPOKEO_EMAIL)

    # Password field
    password_field = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "input[type='password'], input[name='password'], #password")
    ))
    password_field.clear()
    password_field.send_keys(SPOKEO_PASSWORD)

    # Submit button
    submit = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
    ))
    submit.click()
    print("Login submitted — waiting for redirect...")
    time.sleep(5)


def scrape_spokeo(address, city, state):
    target_url = format_url(address, city, state)
    print(f"Target URL: {target_url}")

    driver = get_driver()
    try:
        driver.get(target_url)
        time.sleep(4)

        # Accept any cookie/terms popup
        accept_any_popup(driver)
        time.sleep(1)

        current = driver.current_url
        print(f"Current URL after navigation: {current}")

        # If redirected to login page, log in and then go back to target
        if "/login" in current:
            print("Redirected to login page — performing login...")
            perform_login(driver)

            # After login, Spokeo usually redirects back automatically.
            # If not, navigate manually to the target URL.
            if target_url not in driver.current_url:
                print(f"Navigating back to target: {target_url}")
                driver.get(target_url)
                time.sleep(5)

            accept_any_popup(driver)

        # Also handle inline login modal (blur overlay) on property page
        elif "login" in driver.page_source.lower() and "blur" in driver.page_source.lower():
            print("Login modal detected on property page — performing login...")
            perform_login(driver)
            time.sleep(3)

        # Final wait for dynamic content to fully render
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
