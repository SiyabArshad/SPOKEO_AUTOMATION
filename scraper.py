import os
import re
import sys
import asyncio
from playwright.async_api import async_playwright


def format_url(address, city, state):
    addr = re.sub(r'[^\w\s-]', '', address.strip())
    addr = re.sub(r'\s+', '-', addr)
    city_formatted = '-'.join([word.capitalize() for word in city.strip().lower().split(' ')])
    state_formatted = state.strip().upper()
    return f"https://www.spokeo.com/{state_formatted}/{city_formatted}/{addr}"


async def _scrape_async(address, city, state):
    url = format_url(address, city, state)

    user_data_dir = os.environ.get("CHROME_PROFILE_PATH")
    if not user_data_dir:
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            user_data_dir = os.path.join(localappdata, "Google", "Chrome", "User Data")
        else:
            user_data_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome")

    profile_dir = os.environ.get("CHROME_PROFILE_DIR", "Default")

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=False,
            args=[
                f"--profile-directory={profile_dir}",
                "--disable-blink-features=AutomationControlled",
                "--restore-last-session=false",       # Suppress "Restore pages?" popup
                "--disable-session-crashed-bubble",   # Suppress crash recovery bubble
                "--no-first-run",
                "--no-default-browser-check",
            ]
        )

        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)

            page_text = await page.evaluate("document.body.innerText.toLowerCase()")
            if "no records found" in page_text or "could not find a match" in page_text:
                await browser.close()
                return []

            results = await page.evaluate("""() => {
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
            }""")

            await browser.close()

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
            await browser.close()
            raise e


def scrape_spokeo(address, city, state):
    """Sync wrapper using ProactorEventLoop for Python 3.14 Windows compatibility."""
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_scrape_async(address, city, state))
    finally:
        loop.close()
