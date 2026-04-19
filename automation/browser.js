const { chromium } = require('playwright');

let browserContext = null;

/**
 * Connects to an already running Chrome instance over CDP.
 * This completely prevents the Windows "Exit Code 21" profile locking error.
 */
async function getBrowserContext() {
  if (browserContext) {
    return browserContext;
  }

  const debuggingPort = 9222;
  const endpointUrl = `http://127.0.0.1:${debuggingPort}`;

  console.log(`Connecting to running Chrome on ${endpointUrl}...`);

  try {
    // Connect to the already running Chrome window
    const browser = await chromium.connectOverCDP(endpointUrl);
    
    // Grab the existing context (your normal browsing session)
    browserContext = browser.contexts()[0];
    
    if (!browserContext) {
        browserContext = await browser.newContext();
    }

    console.log("Successfully connected to your running Chrome session!");
    return browserContext;

  } catch (error) {
    console.error(`\n================================================================`);
    console.error(`ERROR: Could not connect to Chrome.`);
    console.error(`\nTo fix "Exit Code 21" and profile locking, you must start Chrome manually with a debugging port.`);
    console.error(`\nPlease follow these exact steps:`);
    console.error(`1. Completely close ALL normal Google Chrome windows.`);
    console.error(`2. Open Windows Command Prompt (cmd) and run this exact command:`);
    console.error(`   "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222`);
    console.error(`3. Chrome will open. Leave it open!`);
    console.error(`4. Finally, start this Node server again (npm start)`);
    console.error(`================================================================\n`);
    throw new Error("Chrome is not running with --remote-debugging-port=9222");
  }
}

module.exports = { getBrowserContext };
