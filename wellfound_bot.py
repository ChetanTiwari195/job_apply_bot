import asyncio
import os
import csv
from datetime import datetime
from pathlib import Path
import logging
from playwright.async_api import async_playwright

from naukri_bot import load_params, load_resume_text, AIJobMatcher

BASE_DIR = Path(__file__).parent
LOG_CSV = BASE_DIR / "wellfound_applied_jobs.csv"

logging.basicConfig(
    force=True,
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "wellfound_bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

def record_application(job_url, title, score, reason):
    """Save applied jobs to CSV"""
    write_header = not LOG_CSV.exists()
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "job_url", "title", "score", "reason"])
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "job_url": job_url,
            "title": title,
            "score": score,
            "reason": reason,
        })

def get_applied_urls():
    """Get a set of already applied job URLs from CSV."""
    urls = set()
    if LOG_CSV.exists():
        with open(LOG_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "job_url" in row:
                    urls.add(row["job_url"])
    return urls

async def main():
    params = load_params()
    resume_text = load_resume_text(params)
    matcher = AIJobMatcher(resume_text, params)
    applied_urls = get_applied_urls()
    
    # ponytail: connect to existing Chrome, rely on Wellfound's native logged-in feed instead of custom search logic
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = await context.new_page()
            log.info("Connected to Chrome via CDP")
        except Exception as e:
            log.error("Run Chrome with: chrome.exe --remote-debugging-port=9222")
            return

        applied_count = 0

        log.info("Loading Wellfound personalized jobs feed...")
        await page.goto("https://wellfound.com/jobs")
        await page.wait_for_timeout(5000)
        
        # ponytail: scroll once to load a decent batch of jobs natively
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await page.wait_for_timeout(3000)

        # Extract all job links
        job_links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a'))
                .map(a => a.href)
                .filter(h => h.includes('wellfound.com/jobs/') && /\/jobs\/\d+-/.test(h));
        }''')
        
        # Remove duplicates
        job_links = list(dict.fromkeys(job_links))
        log.info(f"Found {len(job_links)} jobs on feed")

        for href in job_links:
            if href in applied_urls:
                log.info(f"Skipping already applied job: {href}")
                continue
                
            await page.goto(href)
            await page.wait_for_timeout(3000)
            
            try:
                title_locator = page.locator("h1").first
                if not await title_locator.is_visible():
                    continue
                title = await title_locator.inner_text()
                
                # Get mostly just the text content for the AI to read
                jd = await page.locator("body").inner_text()
                
                should_apply, score, reason = matcher.should_apply(title, jd)
                log.info(f"[{score}] {title} -> {reason}")
                
                if should_apply:
                    # Look for "Apply" or "Apply now" button
                    apply_btn = page.locator('button:has-text("Apply")').first
                    if await apply_btn.is_visible():
                        await apply_btn.click()
                        applied_count += 1
                        log.info(f"    -> Applied to {title} (Total: {applied_count})")
                        record_application(href, title, score, reason)
                        await page.wait_for_timeout(2000)
                        
                        if applied_count >= 100:
                            log.info("Reached maximum application limit of 100. Stopping.")
                            await page.close()
                            return
            except Exception as e:
                log.warning(f"Error processing job {href}: {e}")

        await page.close()

if __name__ == "__main__":
    asyncio.run(main())
