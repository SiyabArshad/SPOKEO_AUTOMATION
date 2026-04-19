import os
import re
import sys
import time
import subprocess

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def format_url(address, city, state):
    addr = re.sub(r'[^\w\s-]', '', address.strip())
    addr = re.sub(r'\s+', '-', addr)
    city_formatted = '-'.join([w.capitalize() for w in city.strip().lower().split()])
    state_formatted = state.strip().upper()
    return f"https://www.spokeo.com/{state_formatted}/{city_formatted}/{addr}"


def kill_chrome():
    """Force-kill all Chrome processes on Windows to release the profile lock."""
    if sys.platform == 'win32':
        try:
            subprocess.run(
                ['taskkill', '/F', '/IM', 'chrome.exe', '/T'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(3)
        except Exception:
            pass


def scrape_spokeo(address, city, state):
    url = format_url(address, city, state)

    # Resolve Chrome profile path
    user_data_dir = os.environ.get("CHROME_PROFILE_PATH")
    if not user_data_dir:
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            user_data_dir = os.path.join(localappdata, "Google", "Chrome", "User Data")
        else:
            user_data_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome")

    profile_dir = os.environ.get("CHROME_PROFILE_DIR", "Default")

    # Kill any existing Chrome to release the profile lock before launching
    kill_chrome()

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--restore-last-session=false")
    options.add_argument("--disable-session-crashed-bubble")

    driver = uc.Chrome(options=options, headless=False)

    try:
        driver.get(url)
        time.sleep(5)  # Wait for dynamic content to load

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "no records found" in page_text or "could not find a match" in page_text:
            driver.quit()
            return []

        # Extract contacts via JavaScript
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

                [...new Set(emails)].forEach(email => results.push({ name, type: 'email', value: email }));
                [...new Set(phones)].forEach(phone => results.push({ name, type: 'phone', value: phone }));
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
