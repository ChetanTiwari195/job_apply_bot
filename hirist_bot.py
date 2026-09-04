import asyncio
import os
import csv
from datetime import datetime
from pathlib import Path
import logging
from playwright.async_api import async_playwright

# Reuse existing logic to stay DRY (Don't Repeat Yourself)
from naukri_bot import load_params, load_resume_text, AIJobMatcher

BASE_DIR = Path(__file__).parent
LOG_CSV = BASE_DIR / "hirist_applied_jobs.csv"

logging.basicConfig(
    force=True,
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "hirist_bot.log", encoding="utf-8"),
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
    
    # ponytail: connect to existing Chrome instead of managing logins/captchas
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

        for keyword in params.get("role_keywords", []):
            log.info(f"Searching Hirist for: {keyword}")
            
            try:
                # ponytail: Hirist ignores URL query params, must drive the UI search box
                await page.goto("https://www.hirist.tech/search/jobs")
                await page.wait_for_timeout(3000)
                
                search_input = page.get_by_placeholder("Jobs")
                if await search_input.count() > 0:
                    await search_input.first.fill(keyword)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(3000)
                    
                    # Apply Experience Filter
                    try:
                        min_exp = int(params.get("min_experience_years", 0))
                        if min_exp <= 1:
                            exp_text = "0 - 1 yrs"
                        elif min_exp <= 3:
                            exp_text = "2 - 3 yrs"
                        elif min_exp <= 6:
                            exp_text = "4 - 6 yrs"
                        elif min_exp <= 10:
                            exp_text = "7 - 10 yrs"
                        else:
                            exp_text = "11 - 15 yrs"
                            
                        await page.locator('#lotus-select-experience').click()
                        await page.wait_for_timeout(1000)
                        
                        exp_option = page.locator('[role="option"]', has_text=exp_text).first
                        if await exp_option.is_visible():
                            await exp_option.click()
                            log.info(f"Applied filter: {exp_text}")
                            await page.wait_for_timeout(2000)
                            
                        # Apply Freshness Filter natively via UI based on .env MAX_JOB_AGE_DAYS
                        max_days = int(os.environ.get("MAX_JOB_AGE_DAYS", 7))
                        if max_days <= 3:
                            date_text = "< 3 Days"
                        elif max_days <= 7:
                            date_text = "Last 1 Week"
                        elif max_days <= 14:
                            date_text = "Last 2 Weeks"
                        elif max_days <= 30:
                            date_text = "Last 1 Month"
                        elif max_days <= 90:
                            date_text = "Last 3 Months"
                        else:
                            date_text = "All Postings"
                            
                        await page.locator('#lotus-select-posting').click()
                        await page.wait_for_timeout(1000)
                        date_option = page.locator('[role="option"]', has_text=date_text).first
                        if await date_option.is_visible():
                            await date_option.click()
                            log.info(f"Applied filter: {date_text}")
                            await page.wait_for_timeout(3000)
                            
                    except Exception as e:
                        log.warning(f"Could not set experience filter: {e}")
                        
                else:
                    log.error(f"Search input not found for {keyword}")
                    continue
                
                # Extract all job links
                job_links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => a.href)
                        .filter(h => h.includes('hirist.tech/j/'));
                }''')
                
                # Remove duplicates
                job_links = list(dict.fromkeys(job_links))
                log.info(f"Found {len(job_links)} jobs for '{keyword}'")

                for href in job_links:
                    if href in applied_urls:
                        log.info(f"Skipping already applied job: {href}")
                        continue
                        
                    await page.goto(href)
                    await page.wait_for_timeout(2500)
                    
                    try:
                        title = await page.locator("h1").first.inner_text()
                        # Get mostly just the text content for the AI to read
                        jd = await page.locator("body").inner_text()
                        
                        should_apply, score, reason = matcher.should_apply(title, jd)
                        log.info(f"[{score}] {title} -> {reason}")
                        
                        if should_apply:
                            # The apply button is usually an exact "Apply" text button
                            apply_btn = page.locator('button', has_text="Apply").first
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
            
            except Exception as e:
                log.error(f"Error processing keyword {keyword}: {e}")

        await page.close()

if __name__ == "__main__":
    asyncio.run(main())
