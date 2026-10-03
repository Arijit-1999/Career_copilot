# Career Copilot — LinkedIn Browser Integration Testing Guide

This directory contains standalone smoke scripts to test and verify the browser automation and LinkedIn job scraping subsystem.

---

## 🎯 Verification Levels

| Level | Type | Description | Script / Command |
|---|---|---|---|
| **Level 1** | Unit / Mock Tests | 100% offline, zero network or Playwright needed | `pytest backend/tests/unit/test_browser.py` |
| **Level 2** | Guest Smoke | Live Chromium, unauthenticated public job search | `python scripts/smoke_linkedin.py` |
| **Level 3** | Authenticated Smoke | Live Chromium with persistent LinkedIn session cookies | `python scripts/smoke_linkedin_authenticated.py` |
| **Level 4** | Automated Live Test | Pytest suite running against live web | `pytest -m browser` |

---

## 🚀 Step-by-Step Setup & Execution

### Step 1: Install Playwright & Chromium
In your project virtual environment (PowerShell on Windows):
```powershell
.\.venv\Scripts\python.exe -m pip install "playwright>=1.42.0"
.\.venv\Scripts\playwright.exe install chromium
```

---

### Step 2: Run Guest Mode Smoke Test (Level 2)
Tests public search and JD detail extraction without credentials:
```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe scripts/smoke_linkedin.py
```
> **What to expect**: A visible Chromium browser window opens, navigates to LinkedIn jobs, enters "Python Developer", scrapes the top 5 results, prints a formatted table to the terminal, and extracts full details for the first listing.

---

### Step 3: Run Authenticated Smoke Test (Level 3)
Allows you to log in once interactively, save session cookies to `.browser_sessions/`, and scrape with full member access:
```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe scripts/smoke_linkedin_authenticated.py
```
> **First Run**:
> 1. Browser opens to `https://www.linkedin.com/login`.
> 2. Log in manually in the browser window and complete any 2FA or CAPTCHA.
> 3. Once on your LinkedIn feed or jobs page, press **ENTER** in PowerShell.
> 4. Session cookies are securely saved to `.browser_sessions/linkedin_user_*.json`.
>
> **Subsequent Runs**: Automatically reuses the saved cookies without prompting for login until the session expires (12-hour default TTL).

---

### Step 4: Run Live Pytest Suite (Level 4)
To run the automated browser test in headless mode:
```powershell
.\.venv\Scripts\pytest.exe backend/tests/browser/ -m browser -v
```

To run all regular offline unit/integration tests (skipping live browser):
```powershell
.\.venv\Scripts\pytest.exe backend/tests/ -m "not browser" -v
```

---

## 🛡️ Anti-Detection & Rate-Limiting Notes

- **Stealth Headers**: [BrowserController](file:///backend/app/browser/controller.py) injects realistic User-Agents, masks `navigator.webdriver`, and sets matching locales and timezones.
- **Slow-Motion**: Default scripts use `slow_mo_ms=800` to mimic realistic human interaction delays and avoid rate-limiting triggers.
- **Bot Detection / Auth-Wall**: If LinkedIn presents a verification challenge or authwall, the adapter catches it gracefully without crashing and logs a warning or challenge event.
