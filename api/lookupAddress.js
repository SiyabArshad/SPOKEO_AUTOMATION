const { formatUrlParams } = require('../utils/formatAddress');
const { scrapePropertyOwners } = require('../automation/scraper');

// Keep track of the last request time for rate limiting
let lastRequestTime = 0;

// Helper to delay execution
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function lookupAddressHandler(req, res) {
  try {
    const { address, city, state } = req.body;

    if (!address || !city || !state) {
      return res.status(400).json({ error: "Missing required fields: address, city, state" });
    }

    // Rate Handling: add delay between 2-5 seconds for multiple requests
    const now = Date.now();
    if (lastRequestTime > 0) {
        // We delay if a previous request was processed recently (e.g., within the last 10 seconds)
        // Or simply delay all consecutive requests
        const delayMs = Math.floor(Math.random() * 3000) + 2000; // 2000 to 5000 ms
        console.log(`Delaying request for ${delayMs}ms to respect rate limit...`);
        await sleep(delayMs);
    }
    lastRequestTime = Date.now();

    // 1. Format URL parameters
    const { formattedState, formattedCity, formattedAddress } = formatUrlParams(address, city, state);
    const url = `https://www.spokeo.com/${formattedState}/${formattedCity}/${formattedAddress}`;

    console.log(`Looking up: ${url}`);

    // 2. Extract Data
    const data = await scrapePropertyOwners(url);

    // 3. Respond
    if (!data || data.length === 0) {
      return res.status(404).json({ error: "No data found" });
    }

    return res.status(200).json(data);

  } catch (error) {
    console.error('Error in lookupAddressHandler:', error);
    return res.status(500).json({ error: "Page load failure or scraping error" });
  }
}

module.exports = { lookupAddressHandler };
