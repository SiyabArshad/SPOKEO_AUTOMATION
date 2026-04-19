const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

let browserContext = null;

async function getBrowserContext() {
  if (browserContext) return browserContext;

  const profileDir = process.env.CHROME_PROFILE_DIR || 'Default';
  let userDataDir = process.env.CHROME_PROFILE_PATH;

  if (!userDataDir) {
    if (process.platform === 'win32') {
      userDataDir = path.join(process.env.LOCALAPPDATA || '', 'Google', 'Chrome', 'User Data');
    } else {
      userDataDir = path.join(process.env.HOME || '', 'Library/Application Support/Google/Chrome');
    }
  }

  if (process.platform === 'win32') {
      try {
          console.log("Attempting to kill background Chrome processes...");
          execSync('taskkill /F /IM chrome.exe /T', { stdio: 'ignore' });
      } catch (e) {
          // Ignore
      }
  }

  console.log(`Launching Chrome from user data dir: ${userDataDir}`);
  console.log(`Target Profile: ${profileDir}`);

  try {
    // We use Playwright's native persistent context but instruct it to use the local Chrome installation
    browserContext = await chromium.launchPersistentContext(userDataDir, {
      channel: 'chrome',     // Forces Playwright to use the system's Chrome installation
      headless: false,       // Headless mode causes profile locks, so we run visible
      args: [
        `--profile-directory=${profileDir}`,
        '--disable-blink-features=AutomationControlled'
      ]
    });
    console.log("Successfully launched and connected to Chrome!");
    return browserContext;
  } catch (err) {
    if (err.message.includes('has been closed') || err.message.includes('21')) {
      console.error(`
=============================================================================
⛔ FATAL ERROR: CHROME IS STILL RUNNING IN THE BACKGROUND
=============================================================================
Google Chrome locks your "User Data" directory while it is running. 
Even if you closed all Chrome windows, Chrome keeps running hidden in the 
background (in the System Tray) to receive notifications.

Because it's locked, Playwright cannot take control and crashes with Code 21.

HOW TO FIX:
1. Go to the bottom-right corner of your Windows screen (System Tray).
2. Click the tiny up-arrow to show hidden icons.
3. Find the Google Chrome icon.
4. RIGHT-CLICK the Chrome icon and select "Exit".
5. Run "npm start" again.
=============================================================================
`);
      throw new Error("Profile locked. Please Exit Chrome from the System Tray.");
    }
    throw err;
  }
}

module.exports = { getBrowserContext };
