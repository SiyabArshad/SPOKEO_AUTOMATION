import os
import re
from playwright.sync_api import sync_playwright

def format_url(address, city, state):
    # Replace spaces with hyphens, remove special characters
    addr = re.sub(r'[^\w\s-]', '', address.strip())
    addr = re.sub(r'\s+', '-', addr)
    city_formatted = '-'.join([word.capitalize() for word in city.strip().lower().split(' ')])
    state_formatted = state.strip().upper()
    return f"https://www.spokeo.com/{state_formatted}/{city_formatted}/{addr}"

def scrape_spokeo(address, city, state):
    url = format_url(address, city, state)
    
    user_data_dir = os.environ.get("CHROME_PROFILE_PATH")
    if not user_data_dir:
        # Default Windows path
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            user_data_dir = os.path.join(localappdata, "Google", "Chrome", "User Data")
        else:
            # Fallback for Mac just in case
            user_data_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome")

    profile_dir = os.environ.get("CHROME_PROFILE_DIR", "Default")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                args=[
                    f"--profile-directory={profile_dir}",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
        except Exception as e:
            if "has been closed" in str(e).lower() or "21" in str(e):
                raise Exception("⛔ PROFILE LOCKED: Chrome is still running in the background! Please completely exit Chrome from the Windows System Tray (bottom right corner) before running.")
            raise e

        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000) # Give time for React hydration

            page_text = page.evaluate("document.body.innerText.toLowerCase()")
            if "no records found" in page_text or "could not find a match" in page_text:
                browser.close()
                return []

            # Execute Javascript in browser to parse DOM robustly
            results = page.evaluate("""() => {
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
                    
                    const uniqueEmails = [...new Set(emails)];
                    const uniquePhones = [...new Set(phones)];

                    uniqueEmails.forEach(email => results.push({ name, type: 'email', value: email }));
                    uniquePhones.forEach(phone => results.push({ name, type: 'phone', value: phone }));
                });
                return results;
            }""")
            
            browser.close()
            
            # Global deduplication
            unique_results = []
            seen = set()
            for item in results:
                val = item['value']
                if item['type'] == 'phone':
                    val = re.sub(r'[-.\s()]', '', val)
                
                key = f"{item['name']}-{item['type']}-{val}"
                if key not in seen:
                    seen.add(key)
                    unique_results.append(item)
            
            return unique_results
            
        except Exception as e:
            browser.close()
            raise e
