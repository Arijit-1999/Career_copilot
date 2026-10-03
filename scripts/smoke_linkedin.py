"""Guest (unauthenticated) smoke test for LinkedIn job search and extraction.

Level 2 verification:
  - Launches Chromium browser in non-headless mode with stealth headers.
  - Searches public LinkedIn jobs for 'Python Developer' in 'India'.
  - Prints search results and extracts full JD details for the first listing.
  - Catches and reports anti-bot / auth-wall challenges gracefully.

Usage (PowerShell):
  $env:PYTHONPATH = "backend"
  python scripts/smoke_linkedin.py
"""

import asyncio
import logging
import sys
from rich.console import Console
from rich.table import Table

# Ensure backend modules are importable
try:
    from app.browser.controller import BrowserController
    from app.browser.adapters.linkedin import LinkedInAdapter
    from app.browser.schemas import BrowserConfig, JobSearchQuery
except ImportError as exc:
    print(f"Error importing Career Copilot backend modules: {exc}")
    print("Make sure you set PYTHONPATH: $env:PYTHONPATH = 'backend'")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
console = Console()


async def run_guest_smoke() -> None:
    console.print("\n[bold cyan]==========================================================[/bold cyan]")
    console.print("[bold cyan]   Career Copilot — LinkedIn Guest Scraper Smoke Test    [/bold cyan]")
    console.print("[bold cyan]==========================================================[/bold cyan]\n")

    config = BrowserConfig(
        headless=False,
        slow_mo_ms=800,
        timeout_ms=30_000,
    )

    console.print("[yellow]Launching Chromium browser (visible window)...[/yellow]")

    try:
        async with await BrowserController.launch(config) as ctrl:
            adapter = LinkedInAdapter(ctrl)

            query = JobSearchQuery(
                keywords=["Python Developer"],
                location="India",
                remote_only=False,
                max_results=5,
            )

            console.print(f"[green]Executing LinkedIn search query:[/green] {query.keywords} in '{query.location}' (max: {query.max_results})...\n")
            search_result = await adapter.search(query)

            console.print(f"[bold]Search Complete:[/bold] Found [cyan]{len(search_result.listings)}[/cyan] listings (total reported: {search_result.total_found})")

            if search_result.errors:
                console.print(f"[yellow]Warnings/Errors during scrape:[/yellow] {search_result.errors}")

            if not search_result.listings:
                console.print("[red]No listings extracted. LinkedIn may have presented an auth-wall or captcha challenge.[/red]")
                return

            table = Table(title="Extracted Job Listings (Guest Mode)")
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

            # Test full JD extraction on the first result
            first_job = search_result.listings[0]
            console.print(f"\n[bold yellow]Testing Full JD Extraction for:[/bold yellow] [bold]{first_job.title}[/bold] ({first_job.application_url})")

            detail = await adapter.extract_detail(first_job.application_url)
            if detail:
                console.print(f"[bold green]✓ Detail Extraction Successful![/bold green]")
                console.print(f"[bold]Extracted Title:[/bold] {detail.title}")
                console.print(f"[bold]Extracted Company:[/bold] {detail.company}")
                console.print(f"[bold]Skills Detected:[/bold] {detail.required_skills or 'None tagged'}")
                desc_snippet = (detail.description_raw or "")[:300].strip()
                console.print(f"[bold]Description Snippet:[/bold]\n{desc_snippet}...\n")
            else:
                console.print("[yellow]Could not extract full JD (guest view may be gated by LinkedIn auth-wall).[/yellow]")

    except ImportError as e:
        console.print(f"[bold red]Playwright not installed:[/bold red] {e}")
        console.print("[yellow]Install with:[/yellow] pip install playwright && playwright install chromium")
    except Exception as exc:
        console.print(f"[bold red]Smoke test encountered error:[/bold red] {exc}")


if __name__ == "__main__":
    asyncio.run(run_guest_smoke())
