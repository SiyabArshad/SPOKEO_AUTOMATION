const { chromium } = require('playwright');
const { execSync, spawn } = require('child_process');
const fs = require('fs');
const http = require('http');

let browserContext = null;

// Helper to check if the port is responding
function checkDebuggingPort(url) {
  return new Promise((resolve) => {
    http.get(`${url}/json/version`, (res) => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => resolve(true));
    }).on('error', (err) => {
      console.log(`Port check failed: ${err.message}`);
      resolve(false);
    });
  });
}

async function getBrowserContext() {
  if (browserContext) {
    return browserContext;
  }

  const debuggingPort = 9222;
  const endpointUrl = `http://localhost:${debuggingPort}`; // Using localhost instead of 127.0.0.1

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
        // Ignore errors
      }

      const winPaths = [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
      ];
      const chromePath = winPaths.find(p => fs.existsSync(p));

      if (!chromePath) throw new Error("Could not find Google Chrome installation.");

      const profileDir = process.env.CHROME_PROFILE_DIR || 'Default';
      const userDataDir = process.env.CHROME_PROFILE_PATH || `${process.env.LOCALAPPDATA}\\Google\\Chrome\\User Data`;

      console.log(`Launching Chrome from: ${chromePath}`);
      // Launch without shell:true for safer argument passing
      const chromeProc = spawn(chromePath, [
        `--remote-debugging-port=${debuggingPort}`,
        `--profile-directory=${profileDir}`,
        `--user-data-dir=${userDataDir}`,
        '--no-first-run',
        '--no-default-browser-check'
      ], {
        detached: true,
        stdio: 'ignore'
      });
      chromeProc.unref();

      console.log(`Waiting 5 seconds for Chrome to initialize...`);
      await new Promise(resolve => setTimeout(resolve, 5000));

      const isUp = await checkDebuggingPort(endpointUrl);
      if (!isUp) {
        throw new Error("Chrome launched, but the debugging port 9222 did not open. It might be blocked by a firewall or another process is locking the profile.");
      }

      try {
        const browser = await chromium.connectOverCDP(endpointUrl);
        browserContext = browser.contexts()[0];
        if (!browserContext) browserContext = await browser.newContext();
        console.log("Successfully connected to newly launched Chrome session!");
        return browserContext;
      } catch (finalErr) {
        throw new Error("Port is open, but Playwright failed to connect: " + finalErr.message);
      }
    } else {
      throw new Error(`Please launch Chrome manually with --remote-debugging-port=${debuggingPort}`);
    }
  }
}

module.exports = { getBrowserContext };
