# SPOKEO_AUTOMATION

A backend service that automates the retrieval of property owner contact data from Spokeo using a pre-authenticated Chrome profile via Playwright.

## Prerequisites

- Node.js installed
- Google Chrome installed and logged into Spokeo under the desired profile (e.g., "Learn2")
- The Chrome user data directory path

## Setup & Run

1. **Install Dependencies:**
   ```bash
   npm install
   ```

2. **Configure Environment Variables:**
   The application attempts to use your system's default Chrome directory automatically, but you should explicitly set the path to your existing Chrome profile if needed.
   
   **How to find your Profile Path (Windows & Mac):**
   1. Open Google Chrome and switch to the profile you want to use (e.g., "Learn2").
   2. Type `chrome://version` in the URL bar and press Enter.
   3. Look for the **Profile Path** field. 
      - *Windows Example:* `C:\Users\<YourUsername>\AppData\Local\Google\Chrome\User Data\Profile 2`
      - *Mac Example:* `/Users/<YourUsername>/Library/Application Support/Google/Chrome/Profile 2`
   
   The `CHROME_PROFILE_PATH` is everything **before** the last folder.
   The `CHROME_PROFILE_DIR` is the **last folder** (e.g., `Profile 2` or `Default`).

   Set the following environment variables when running the server:
   
   **For Windows (Command Prompt):**
   ```cmd
   set CHROME_PROFILE_PATH=C:\Users\<YourUsername>\AppData\Local\Google\Chrome\User Data
   set CHROME_PROFILE_DIR=Profile 2
   ```

   **For Windows (PowerShell):**
   ```powershell
   $env:CHROME_PROFILE_PATH="C:\Users\<YourUsername>\AppData\Local\Google\Chrome\User Data"
   $env:CHROME_PROFILE_DIR="Profile 2"
   ```

   **For Mac/Linux:**
   ```bash
   export CHROME_PROFILE_PATH="/Users/<YOUR_USERNAME>/Library/Application Support/Google/Chrome"
   export CHROME_PROFILE_DIR="Profile 2"
   ```

   *Optional:* Set `HEADLESS=false` to see the browser visibly.
   ```bash
   export HEADLESS=false
   ```

3. **Start the Server:**
   ```bash
   npm start
   ```

## API Specification

**Endpoint:** `POST /lookup-address`

### Request Example

```json
{
  "address": "1255 WESTSHORE DR",
  "city": "CUMMING",
  "state": "GA"
}
```

### Response Example (Success)

```json
[
  {
    "name": "John Doe",
    "type": "phone",
    "value": "1234567890"
  },
  {
    "name": "John Doe",
    "type": "email",
    "value": "example@email.com"
  }
]
```

### Response Example (No Data / Error)

```json
{
  "error": "No data found"
}
```

## How It Works

- The service listens for requests and formats the address to match Spokeo's URL pattern.
- A Playwright persistent context connects to your existing Chrome profile, bypassing the need for a login flow.
- A scraper algorithm parses the generated HTML locally to find people and their associated contact information (emails, phones, socials), applying deduplication.
- A random delay (2–5 seconds) is automatically added between consecutive requests to handle basic rate limiting.

## Note on Selectors

Spokeo's DOM is highly dynamic. The scraper uses generalized heuristics to locate owner names and parse text contents for emails/phones. If Spokeo fundamentally changes their UI, the scraping logic inside `automation/scraper.js` may need to be adjusted.
