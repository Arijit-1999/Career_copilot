"""Authenticated smoke test for LinkedIn job search and extraction with session persistence.

Level 3 verification:
  - Loads saved cookies from `.browser_sessions/` if present and unexpired.
  - If not authenticated or session invalid: opens an interactive browser window to
    LinkedIn login, allowing the user to log in manually (and solve 2FA/CAPTCHA).
  - Persists authenticated session cookies securely to disk.
  - Runs search and full JD extraction under the authenticated profile.

Usage (PowerShell):
  $env:PYTHONPATH = "backend"
  python scripts/smoke_linkedin_authenticated.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

# Ensure backend modules are importable
try:
    from app.browser.controller import BrowserController
    from app.browser.adapters.linkedin import LinkedInAdapter
    from app.browser.session import SessionManager
    from app.browser.enums import PlatformName, SessionState
    from app.browser.schemas import BrowserConfig, JobSearchQuery
except ImportError as exc:
    print(f"Error importing Career Copilot backend modules: {exc}")
    print("Make sure you set PYTHONPATH: $env:PYTHONPATH = 'backend'")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
console = Console()

SESSION_USERNAME = "user_linkedin"
SESSIONS_DIR = Path(".browser_sessions")


async def run_authenticated_smoke() -> None:
    console.print("\n[bold cyan]==========================================================[/bold cyan]")
    console.print("[bold cyan] Career Copilot — Authenticated LinkedIn Integration Test [/bold cyan]")
    console.print("[bold cyan]==========================================================[/bold cyan]\n")

    session_mgr = SessionManager(sessions_dir=SESSIONS_DIR)
    load_res = session_mgr.load_session(PlatformName.LINKEDIN, username=SESSION_USERNAME)

    config = BrowserConfig(
        headless=False,
        slow_mo_ms=600,
        timeout_ms=30_000,
    )

    try:
        async with await BrowserController.launch(config) as ctrl:
            page = await ctrl.new_page()
            adapter = LinkedInAdapter(ctrl)

            has_valid_session = False
            if load_res.found and load_res.session_state == SessionState.AUTHENTICATED:
                console.print(f"[bold green]✓ Found existing session profile in '{SESSIONS_DIR}'. Restoring cookies...[/bold green]")
                restored = await session_mgr.restore_to_browser(ctrl, PlatformName.LINKEDIN, SESSION_USERNAME)
                if restored:
                    await ctrl.navigate(page, "https://www.linkedin.com/feed/")
                    await asyncio.sleep(2)
                    is_authed = await adapter.is_logged_in(page=page)
                    if is_authed:
                        console.print("[bold green]✓ Session verified: Logged in via saved cookies![/bold green]")
                        has_valid_session = True
                    else:
                        console.print("[yellow]Saved session cookies expired or invalid. Re-authenticating...[/yellow]")

            if not has_valid_session:
                console.print("\n[bold yellow]Starting Interactive Login Session...[/bold yellow]")
                console.print("[dim]Navigating to LinkedIn login page in the browser...[/dim]")
                await ctrl.navigate(page, "https://www.linkedin.com/login")

                console.print("\n[bold green]👉 ACTION REQUIRED:[/bold green]")
                console.print("1. Enter your LinkedIn credentials in the opened browser window.")
                console.print("2. Complete any 2FA or CAPTCHA challenge.")
                console.print("3. Wait until you see your LinkedIn Feed/Homepage.")
                input("\n>>> Once logged in and on the homepage/feed, press [ENTER] here to save cookies... ")

                profile = await session_mgr.capture_from_browser(ctrl, PlatformName.LINKEDIN, SESSION_USERNAME)
                has_li_at = any(c.get("name") == "li_at" for c in profile.cookies)
                console.print(f"[bold green]✓ Session captured ({len(profile.cookies)} cookies saved, li_at_present={has_li_at}).[/bold green]\n")

            # Execute authenticated search
            query = JobSearchQuery(
                keywords=["Python Developer"],
                location="India",
                remote_only=False,
                max_results=5,
            )

            console.print(f"[green]Searching LinkedIn Jobs:[/green] {query.keywords} in '{query.location}'...")
            search_result = await adapter.search(query)

            console.print(f"[bold]Search Complete:[/bold] Extracted [cyan]{len(search_result.listings)}[/cyan] listings (Total reported: {search_result.total_found}).")

            if search_result.errors:
                console.print(f"[yellow]Warnings/Errors during scrape:[/yellow] {search_result.errors}")

            if not search_result.listings:
                console.print("[red]No listings returned. LinkedIn may have presented a challenge or changed DOM layout.[/red]")
                console.print("Keeping browser open for 10 seconds so you can inspect...")
                await asyncio.sleep(10)
                return

            table = Table(title="Extracted Job Listings (Authenticated)")
            table.add_column("#", style="dim", width=4)
            table.add_column("Title", style="bold green", min_width=25)
            table.add_column("Company", style="cyan", min_width=20)
            table.add_column("Location", style="yellow", min_width=15)
            table.add_column("Job ID", style="magenta", width=12)

            for idx, job in enumerate(search_result.listings, start=1):
                table.add_row(
                    str(idx),
                    job.title,
                    job.company,
                    job.location or "N/A",
                    job.source_job_id,
                )

            console.print(table)

            # Test detailed JD extraction
            target_job = search_result.listings[0]
            console.print(f"\n[bold yellow]Extracting Full JD for:[/bold yellow] [bold]{target_job.title}[/bold] ({target_job.application_url})")
            detail = await adapter.extract_detail(target_job.application_url, page=page)

            if detail:
                console.print(f"[bold green]✓ Full Detail Extraction Successful![/bold green]")
                console.print(f"[bold]Title:[/bold] {detail.title}")
                console.print(f"[bold]Company:[/bold] {detail.company}")
                console.print(f"[bold]Location:[/bold] {detail.location}")
                console.print(f"[bold]Skills Tagged:[/bold] {detail.required_skills or 'None tagged'}")
                desc_snippet = (detail.description_raw or "")[:400].strip()
                console.print(f"[bold]Full Description Preview:[/bold]\n{desc_snippet}...\n")
            else:
                console.print("[yellow]Could not extract JD detail for listing.[/yellow]")

            console.print("[dim]Pausing 5 seconds before closing browser...[/dim]")
            await asyncio.sleep(5)

    except ImportError as e:
        console.print(f"[bold red]Playwright not installed:[/bold red] {e}")
        console.print("[yellow]Install with:[/yellow] pip install playwright && playwright install chromium")
    except Exception as exc:
        console.print(f"[bold red]Authenticated test encountered error:[/bold red] {exc}")


if __name__ == "__main__":
    try:
        asyncio.run(run_authenticated_smoke())
    except KeyboardInterrupt:
        print("\nTest cancelled by user.")
