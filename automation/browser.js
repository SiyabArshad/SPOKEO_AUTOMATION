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

  // Launch persistent context
  // Headless mode can sometimes interfere with logged-in sessions or trigger captchas.
  // Using headless: "new" or false depending on the environment. We'll use headless: true by default, 
  // but it can be overridden.
  browserContext = await chromium.launchPersistentContext(userDataDir, {
    headless: process.env.HEADLESS !== 'false', 
    args: [
      `--profile-directory=${profileDir}`,
      '--disable-blink-features=AutomationControlled',
      '--no-sandbox',
      '--disable-setuid-sandbox'
    ],
    // Helps bypass basic automation detection
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });

  return browserContext;
}

module.exports = { getBrowserContext };
