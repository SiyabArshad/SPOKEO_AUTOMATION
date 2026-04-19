# SPOKEO_AUTOMATION (Python/Streamlit Version)

A Python-based visual application that automates the retrieval of property owner contact data from Spokeo using a pre-authenticated Chrome profile via Playwright.

## Prerequisites

- Python 3.9+ installed
- Google Chrome installed and logged into Spokeo under the desired profile

## Setup

1. **Install Dependencies:**
   Open your Windows Command Prompt or PowerShell and run:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure Environment Variables (Optional):**
   The application automatically attempts to find your default Windows Chrome profile. If you need a specific profile, you can set it before running:
   
   ```cmd
   set CHROME_PROFILE_DIR=Profile 2
   ```

## Running the App

1. **CRITICAL STEP:** You must completely close all Google Chrome windows. Additionally, you must exit Chrome from the Windows System Tray (bottom right corner, next to the clock) because Chrome runs in the background and locks your profile.
2. **Start Streamlit:**
   ```bash
   streamlit run app.py
   ```
3. A browser window will open automatically showing the user interface.

## Features

- **Single Address:** Test one address at a time. No pause.
- **Bulk JSON:** Paste a JSON array of requests. Automatically pauses 3 seconds between requests to respect rate limits.
- **Data Export:** View data in a copyable table, or download directly to **Excel (.xlsx)** or **JSON**.
- **Database IDs:** Send a custom `id` with your request and it will be attached to every extracted contact so you can map it back to your database!
