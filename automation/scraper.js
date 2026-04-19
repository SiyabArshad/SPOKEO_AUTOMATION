const { getBrowserContext } = require('./browser');

/**
 * Scrapes property owner contact data from the given Spokeo URL.
 */
async function scrapePropertyOwners(url) {
  const context = await getBrowserContext();
  const page = await context.newPage();

  try {
    console.log(`Navigating to ${url}...`);
    // Navigate and wait for content to load
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    
    // Give time for dynamic content and hydration to complete
    await page.waitForTimeout(4000);

    // If there's a captcha, or the page indicates "No record found", we handle it gracefully below
    // (though no CAPTCHA solving is to be implemented, we simply parse whatever is available)
    const pageText = await page.evaluate(() => document.body.innerText.toLowerCase());
    if (pageText.includes('no records found') || pageText.includes('could not find a match')) {
       await page.close();
       return null; // Signals no data
    }

    // Evaluate the DOM to extract contacts
    const extractedData = await page.evaluate(() => {
      const results = [];
      
      // Look for sections containing people
      // Spokeo DOM varies, but generally we look for names within headers or specific classes
      const nameElements = document.querySelectorAll('h2, h3, .name, [class*="Name"], [class*="Title"]');
      
      nameElements.forEach(nameEl => {
        const name = nameEl.textContent.trim();
        // Skip if it doesn't look like a valid name (too long or too many words)
        if (!name || name.length > 50 || name.split(' ').length > 6) return;
        
        // Find the closest container that likely holds the person's info
        // (usually an article, a div with "card" in the class, or a parent wrapper)
        let card = nameEl.closest('article') || nameEl.closest('[class*="card"]');
        if (!card && nameEl.parentElement && nameEl.parentElement.parentElement) {
            card = nameEl.parentElement.parentElement;
        }
        if (!card) return;

        const cardText = card.textContent || '';
        
        // Extract Emails
        const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
        const emails = cardText.match(emailRegex) || [];
        
        // Extract Phones (basic US formats)
        const phoneRegex = /(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g;
        const phones = cardText.match(phoneRegex) || [];
        
        // Extract Socials from links
        const links = card.querySelectorAll('a');
        const socials = [];
        links.forEach(link => {
            const href = link.href.toLowerCase();
            if (href.includes('facebook.com')) socials.push({ type: 'facebook', value: href });
            if (href.includes('instagram.com')) socials.push({ type: 'instagram', value: href });
        });

        // Deduplicate values within the person's card
        const uniqueEmails = [...new Set(emails)];
        const uniquePhones = [...new Set(phones)];

        uniqueEmails.forEach(email => {
            results.push({ name, type: 'email', value: email });
        });

        uniquePhones.forEach(phone => {
            results.push({ name, type: 'phone', value: phone });
        });

        socials.forEach(social => {
            // Check if the social link belongs to this person (heuristically)
            results.push({ name, type: social.type, value: social.value });
        });
      });

      return results;
    });

    await page.close();

    // Deduplicate globally to return a clean flattened array
    const uniqueResults = [];
    const seen = new Set();
    for (const item of extractedData) {
        // Normalize phone number removing spaces and hyphens for better deduplication
        let normalizedValue = item.value;
        if (item.type === 'phone') {
            normalizedValue = normalizedValue.replace(/[-.\s()]/g, '');
        }

        const key = `${item.name}-${item.type}-${normalizedValue}`;
        if (!seen.has(key)) {
            seen.add(key);
            uniqueResults.push(item);
        }
    }

    return uniqueResults.length > 0 ? uniqueResults : null;

  } catch (error) {
    if (!page.isClosed()) {
      await page.close();
    }
    console.error(`Scraping error for ${url}:`, error.message);
    throw error;
  }
}

module.exports = { scrapePropertyOwners };
