const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

let browserContext = null;

/**
 * Initializes and returns a persistent browser context using the existing Chrome profile.
 */
async function getBrowserContext() {
  if (browserContext) {
    return browserContext;
  }

  // Use CHROME_PROFILE_PATH from env, or default based on the OS
  let defaultUserDataDir = '';
  if (process.platform === 'win32') {
    // Windows path: C:\Users\<Username>\AppData\Local\Google\Chrome\User Data
    defaultUserDataDir = path.join(process.env.LOCALAPPDATA || '', 'Google', 'Chrome', 'User Data');
  } else {
    // Mac path
    defaultUserDataDir = path.join(process.env.HOME || '', 'Library/Application Support/Google/Chrome');
  }

  const userDataDir = process.env.CHROME_PROFILE_PATH || defaultUserDataDir;

  if (!fs.existsSync(userDataDir)) {
    console.warn(`WARNING: Chrome profile path does not exist: ${userDataDir}`);
    console.warn("Please set CHROME_PROFILE_PATH to your actual Chrome User Data directory.");
  }

  // The profile directory name (e.g. "Default", "Profile 1", "Profile 2")
  // User specifies they want "Learn2" profile. The actual folder name might be "Profile 1".
  const profileDir = process.env.CHROME_PROFILE_DIR || 'Default';

  console.log(`Launching persistent browser context from: ${userDataDir}`);
  console.log(`Using profile directory: ${profileDir}`);

  // Auto-detect local Chrome executable to avoid needing "npx playwright install" 
  // and to avoid version mismatch with the user's profile
  let executablePath = process.env.CHROME_EXECUTABLE_PATH || '';
  if (!executablePath) {
    if (process.platform === 'win32') {
      const winPaths = [
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
        'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
      ];
      executablePath = winPaths.find(p => fs.existsSync(p)) || '';
    } else if (process.platform === 'darwin') {
      const macPath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
      if (fs.existsSync(macPath)) executablePath = macPath;
    }
  }

  const launchOptions = {
    // Default to headless: false because reusing a normal Chrome profile in headless mode 
    // often causes Chrome to crash or exit immediately (exit code 21) on Windows.
    headless: process.env.HEADLESS === 'true', 
    args: [
      `--profile-directory=${profileDir}`,
      '--disable-blink-features=AutomationControlled',
      '--no-sandbox',
      '--disable-setuid-sandbox'
    ],
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  };

  if (executablePath) {
    launchOptions.channel = 'chrome'; // Using local chrome
    launchOptions.executablePath = executablePath;
    console.log(`Using local Chrome executable at: ${executablePath}`);
  } else {
    console.log('No local Chrome found, relying on Playwright bundled browser...');
  }

  // Launch persistent context
  browserContext = await chromium.launchPersistentContext(userDataDir, launchOptions);

  return browserContext;
}

module.exports = { getBrowserContext };
