const { chromium } = require('playwright');
const { execSync, spawn } = require('child_process');
const fs = require('fs');

let browserContext = null;

async function getBrowserContext() {
  if (browserContext) {
    return browserContext;
  }

  const debuggingPort = 9222;
  const endpointUrl = `http://127.0.0.1:${debuggingPort}`;

  try {
    console.log(`Trying to connect to already running Chrome on ${endpointUrl}...`);
    const browser = await chromium.connectOverCDP(endpointUrl);
    browserContext = browser.contexts()[0];
    if (!browserContext) browserContext = await browser.newContext();
    console.log("Successfully connected to running Chrome session!");
    return browserContext;
  } catch (error) {
    console.log("Chrome debugging port is not open. Attempting to automatically start it...");

    if (process.platform === 'win32') {
      try {
        console.log("Killing any background Chrome processes to release the profile lock...");
        execSync('taskkill /F /IM chrome.exe /T', { stdio: 'ignore' });
      } catch (e) {
        // Ignore errors if Chrome is already closed
      }

      const winPaths = [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
      ];
      const chromePath = winPaths.find(p => fs.existsSync(p));

      if (!chromePath) {
          throw new Error("Could not find Google Chrome installation.");
      }

      console.log(`Launching Chrome from: ${chromePath}`);
      const chromeProc = spawn(`"${chromePath}"`, ['--remote-debugging-port=9222'], {
        detached: true,
        shell: true,
        stdio: 'ignore'
      });
      chromeProc.unref();

      console.log("Waiting 3 seconds for Chrome to initialize...");
      await new Promise(resolve => setTimeout(resolve, 3000));

      try {
        const browser = await chromium.connectOverCDP(endpointUrl);
        browserContext = browser.contexts()[0];
        if (!browserContext) browserContext = await browser.newContext();
        console.log("Successfully connected to newly launched Chrome session!");
        return browserContext;
      } catch (finalErr) {
        throw new Error("Still could not connect to Chrome after launching it automatically.");
      }
    } else {
      throw new Error("Please launch Chrome manually with --remote-debugging-port=9222");
    }
  }
}

module.exports = { getBrowserContext };
