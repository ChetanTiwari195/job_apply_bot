"""
Naukri Auto-Apply Bot
=====================
Uses Playwright (browser automation) + openrouter AI (JD matching).
Reads config from job_parameters.md (YAML sections).

Usage:
    python naukri_bot.py

Requirements:
    - Naukri.com must be open and logged-in in the default Chrome profile
      (the script attaches to your existing browser session via CDP)
    - Set GEMINI_API_KEY in .env or as environment variable
"""

import os
import re
import csv
import time
import yaml
import asyncio
import logging
from pathlib import Path
from datetime import datetime

import PyPDF2
from openai import OpenAI
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from dotenv import load_dotenv

# ─────────────────────────────────────────────
# CONFIG & LOGGING
# ─────────────────────────────────────────────
load_dotenv()
BASE_DIR = Path(__file__).parent
PARAMS_FILE = BASE_DIR / "job_parameters.md"
LOG_CSV = BASE_DIR / "applied_jobs.csv"

# Force stdout to UTF-8 on Windows (fixes cp1252 emoji crash)
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# LOAD PARAMETERS
# ─────────────────────────────────────────────
def load_params() -> dict:
    """Parse YAML blocks from job_parameters.md"""
    raw = PARAMS_FILE.read_text(encoding="utf-8")
    # Strip comment lines that start with # (top-level, not indented)
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        lines.append(line)
    content = "\n".join(lines)
    return yaml.safe_load(content)


# ─────────────────────────────────────────────
# RESUME LOADER
# ─────────────────────────────────────────────
def load_resume_text(params: dict) -> str:
    pdf_path = Path(params.get("resume_pdf", ""))
    tex_path = Path(params.get("resume_tex", ""))

    if pdf_path.exists():
        log.info(f"Loading resume from PDF: {pdf_path}")
        text = []
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text() or "")
        return "\n".join(text)

    if tex_path.exists():
        log.info(f"Loading resume from LaTeX: {tex_path}")
        raw = tex_path.read_text(encoding="utf-8")
        # Strip LaTeX commands
        raw = re.sub(r"\\[a-zA-Z]+\*?\{[^}]*\}", lambda m: m.group(0).split("{")[-1].rstrip("}"), raw)
        raw = re.sub(r"\\[a-zA-Z]+\*?", " ", raw)
        raw = re.sub(r"[{}]", "", raw)
        return raw

    raise FileNotFoundError("No resume found. Check resume_pdf / resume_tex in job_parameters.md")


# ─────────────────────────────────────────────
# OPENROUTER AI MATCHER
# ─────────────────────────────────────────────
class AIJobMatcher:
    def __init__(self, resume_text: str, params: dict):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set in .env")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        # Model to use — change to any OpenRouter model slug you prefer
        # Free options: deepseek/deepseek-chat-v3-0324:free, meta-llama/llama-3.1-8b-instruct:free
        self.model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")
        self.resume = resume_text
        self.params = params
        self.threshold = int(params.get("ai_relevance_threshold", 80))
        self.preferred = params.get("preferred_keywords", [])
        self.blacklist = params.get("blacklist_keywords", [])
        self.min_salary = int(params.get("min_expected_lpa", 16))

    def quick_filter(self, title: str, jd: str) -> tuple[bool, str]:
        """Fast keyword-based pre-filter before calling AI."""
        combined = (title + " " + jd).lower()

        # Blacklist check
        for kw in self.blacklist:
            if kw.lower() in combined:
                return False, f"Blacklisted keyword: {kw}"

        # Salary check if mentioned
        salary_match = re.findall(r"(\d+)\s*(?:lpa|l\.?p\.?a|lakhs?)", combined)
        if salary_match:
            max_salary = max(int(s) for s in salary_match)
            if max_salary < self.min_salary:
                return False, f"Salary {max_salary} LPA below minimum {self.min_salary} LPA"

        return True, "Passed quick filter"

    def score_job(self, title: str, jd: str) -> tuple[int, str]:
        """Ask OpenRouter to score JD relevance against resume. Returns (score, reason)."""
        prompt = f"""
You are an expert technical recruiter evaluating whether a candidate should apply to a job.

IMPORTANT RULES:
- Do NOT penalize for job title mismatch. Focus on SKILLS and DOMAIN fit.
- A "Data Engineer" or "Platform Engineer" role is still relevant if it needs Python/FastAPI/backend skills.
- Candidate has 3+ years experience. Accept any role requiring 2+ years (no upper cap).
- Score based on: skill overlap, domain fit, tech stack alignment, and growth potential.
- If 60%+ of required skills match, score should be >= 70.

CANDIDATE RESUME:
{self.resume[:3000]}

JOB TITLE: {title}

JOB DESCRIPTION:
{jd[:2000]}

SCORING GUIDE:
90-100: Near-perfect match (80%+ skills align, same domain)
75-89:  Strong match (60%+ skills align, closely related domain)
60-74:  Decent match (40%+ skills align, transferable experience)
40-59:  Weak match (some relevant skills, different domain)
0-39:   Poor match (fundamentally different stack/domain)

Return ONLY a JSON object:
{{"score": <integer 0-100>, "reason": "<one-line explanation, max 20 words>"}}

No extra text, just the JSON.
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=100,
            )
            text = response.choices[0].message.content.strip()
            # Extract JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                import json
                data = json.loads(json_match.group())
                return int(data.get("score", 0)), data.get("reason", "")
        except Exception as e:
            log.error(f"AI scoring error: {e}")
        return 0, "AI scoring failed"

    def should_apply(self, title: str, jd: str) -> tuple[bool, int, str]:
        """Returns (apply: bool, score: int, reason: str)"""
        passed, reason = self.quick_filter(title, jd)
        if not passed:
            return False, 0, reason

        score, reason = self.score_job(title, jd)
        if score >= self.threshold:
            return True, score, reason
        return False, score, f"Score {score} below threshold {self.threshold}: {reason}"

    def answer_chatbot_question(self, question: str) -> str:
        """Use OpenRouter to answer a Naukri chatbot screening question."""
        prompt = f"""
You are an AI assistant applying for a job on behalf of Chetan Tiwari.
You must answer a recruiter's screening question.
Provide ONLY the exact text to type into the chat box. Be concise and professional.
DO NOT include any quotation marks around your answer. Keep it under 15 words.

CANDIDATE INFO:
Name: {self.params.get("name", "Chetan Tiwari")}
Location: {self.params.get("location_current", "Bengaluru")}
Current CTC / Expected CTC: Answer based on market standard for 3 years experience (e.g. 15-20 LPA) if asked.
Notice Period: 30 days.
Experience: 3+ Years.

RESUME HIGHLIGHTS:
{self.resume[:1500]}

QUESTION TO ANSWER:
{question}
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=50,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            log.error(f"AI answering error: {e}")
            return "Yes"



# ─────────────────────────────────────────────
# APPLIED JOBS LOG
# ─────────────────────────────────────────────
class ApplicationLog:
    def __init__(self):
        self.applied: set[str] = set()
        self._load()

    def _load(self):
        if LOG_CSV.exists():
            with open(LOG_CSV, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.applied.add(row.get("job_id", ""))

    def already_applied(self, job_id: str) -> bool:
        return job_id in self.applied

    def record(self, job_id: str, title: str, company: str, posted_age: str, score: int, reason: str):
        self.applied.add(job_id)
        write_header = not LOG_CSV.exists()
        with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["timestamp", "job_id", "title", "company", "posted_age", "score", "reason"]
            )
            if write_header:
                writer.writeheader()
            writer.writerow({
                "timestamp": datetime.now().isoformat(),
                "job_id": job_id,
                "title": title,
                "company": company,
                "posted_age": posted_age,
                "score": score,
                "reason": reason,
            })
        log.info(f"[APPLIED] [{score}%] {title} @ {company} (posted: {posted_age})")


# ─────────────────────────────────────────────
# NAUKRI BOT
# ─────────────────────────────────────────────
class NaukriBot:
    NAUKRI_BASE = "https://www.naukri.com"
    SEARCH_URL = "https://www.naukri.com/jobs-in-india?keyword={keyword}&experience={exp}&nignoreIndexp=false"

    def __init__(self, params: dict, matcher: AIJobMatcher, app_log: ApplicationLog):
        self.params = params
        self.matcher = matcher
        self.app_log = app_log
        self.max_jobs = int(params.get("max_jobs_per_run", 50))
        self.keywords = params.get("role_keywords", ["Software Engineer"])
        self.experience = "3"  # years
        self.max_age_days = int(params.get("max_job_age_days", 7))       # skip jobs older than this
        self.priority_age_days = int(params.get("priority_age_days", 1)) # process these first
        self.applied_count = 0
        self.page = None

    async def attach_browser(self, playwright):
        """Attach to existing Chrome session with Naukri already logged in."""
        log.info("Connecting to existing Chrome browser (CDP)...")
        # Try to connect via CDP (Chrome DevTools Protocol)
        # User must launch Chrome with: --remote-debugging-port=9222
        try:
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            # Find Naukri tab or create one
            naukri_page = None
            for p in context.pages:
                if "naukri.com" in p.url:
                    naukri_page = p
                    break
            if not naukri_page:
                naukri_page = await context.new_page()
            self.page = naukri_page
            log.info(f"Attached to browser. Current page: {self.page.url}")
            return browser
        except Exception as e:
            log.error(f"Failed to connect to Chrome CDP: {e}")
            log.error("Make sure Chrome is running with --remote-debugging-port=9222")
            log.error("Run: chrome.exe --remote-debugging-port=9222 --user-data-dir=C:/temp/chrome-debug")
            raise

    async def search_jobs(self, keyword: str):
        """Navigate to Naukri job search results."""
        # Use Naukri's standard search URL format
        encoded = keyword.replace(' ', '-').lower()
        url = f"{self.NAUKRI_BASE}/{encoded}-jobs?k={keyword.replace(' ', '+')}&experience=3"
        log.info(f"Searching: {keyword} -> {url}")
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await self.page.wait_for_timeout(3000)  # wait for dynamic content

    async def get_job_cards(self) -> list:
        """Extract job cards from search results page."""
        # Naukri 2026 uses div.srp-jobtuple-wrapper with data-job-id
        await self.page.wait_for_selector("div.srp-jobtuple-wrapper", timeout=10000)
        return await self.page.query_selector_all("div.srp-jobtuple-wrapper")

    @staticmethod
    def parse_age_days(age_text: str) -> int:
        """
        Parse Naukri's posted-age strings into integer days.
        Examples: 'Just now', 'Today', '1 Day Ago', '3 Days Ago', '2 Weeks Ago'
        Returns 999 if unparseable (treated as too old).
        """
        if not age_text:
            return 999
        t = age_text.strip().lower()
        if any(x in t for x in ("just now", "today", "few hours", "hour")):
            return 0
        m = re.search(r"(\d+)\s*day", t)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d+)\s*week", t)
        if m:
            return int(m.group(1)) * 7
        m = re.search(r"(\d+)\s*month", t)
        if m:
            return int(m.group(1)) * 30
        return 999

    async def extract_job_details(self, card) -> dict:
        """Extract title, company, job_id, posted age from a Naukri job card."""
        try:
            # Job ID from data attribute
            job_id = await card.get_attribute("data-job-id") or ""

            # Title: <a class="title"> inside <h2>
            title_el = await card.query_selector("a.title")
            title = (await title_el.inner_text()).strip() if title_el else "Unknown"
            href = await title_el.get_attribute("href") if title_el else ""

            # Company: <a class="comp-name ...">
            company_el = await card.query_selector("a.comp-name")
            if not company_el:
                company_el = await card.query_selector("a[class*='comp-name']")
            company = (await company_el.inner_text()).strip() if company_el else "Unknown"

            # Posted age: <span class="job-post-day">
            age_el = await card.query_selector("span.job-post-day")
            if not age_el:
                age_el = await card.query_selector("span[class*='job-post-day']")
            age_text = (await age_el.inner_text()).strip() if age_el else ""
            age_days = self.parse_age_days(age_text)

            return {
                "title": title,
                "company": company,
                "job_id": job_id,
                "href": href,
                "age_text": age_text or "unknown",
                "age_days": age_days,
            }
        except Exception as e:
            log.debug(f"Error extracting card: {e}")
            return {}

    async def get_jd_text(self, href: str) -> str:
        """Open job page in a new tab and scrape the job description text."""
        try:
            jd_page = await self.page.context.new_page()
            await jd_page.goto(href, wait_until="domcontentloaded", timeout=20000)
            await jd_page.wait_for_timeout(2000)

            # Try multiple JD selectors (Naukri uses different ones)
            for selector in [
                "div.styles_JDC__dang-inner-html__h0K4t",
                "div[class*='dang-inner-html']",
                "section.job-desc",
                "div.job-desc",
                "div[class*='job-desc']",
                "div[class*='jobDescriptionContent']",
            ]:
                jd_el = await jd_page.query_selector(selector)
                if jd_el:
                    jd_text = await jd_el.inner_text()
                    if jd_text and len(jd_text.strip()) > 50:
                        await jd_page.close()
                        return jd_text.strip()

            # Fallback: grab all text from the main content area
            main_el = await jd_page.query_selector("main, div[class*='jd-container'], div[class*='content']")
            jd_text = await main_el.inner_text() if main_el else ""
            await jd_page.close()
            return jd_text.strip()
        except Exception as e:
            log.debug(f"JD fetch error: {e}")
            return ""

    async def apply_to_job(self, job: dict, score: int, reason: str):
        """Open JD page, click Apply, handle popups, then close."""
        href = job.get("href", "")
        if not href:
            log.warning(f"No URL for: {job['title']}")
            return

        jd_page = None
        try:
            jd_page = await self.page.context.new_page()
            await jd_page.goto(href, wait_until="domcontentloaded", timeout=20000)
            await jd_page.wait_for_timeout(2000)

            # Find the Apply button on the JD page
            apply_btn = None
            for selector in [
                "button#apply-button",
                "button[class*='apply']",
                "button:has-text('Apply')",
                "a:has-text('Apply on company site')",
                "button:has-text('Apply on company site')",
                "div[class*='apply'] button",
            ]:
                apply_btn = await jd_page.query_selector(selector)
                if apply_btn:
                    break

            if not apply_btn:
                log.warning(f"No apply button on JD page for: {job['title']}")
                return

            # Check if already applied (button might say "Already Applied")
            btn_text = (await apply_btn.inner_text()).strip().lower()
            if "applied" in btn_text:
                log.info(f"    Already applied on Naukri: {job['title']}")
                return

            await apply_btn.scroll_into_view_if_needed()
            await apply_btn.click()
            await jd_page.wait_for_timeout(2500)

            # Handle chatbot / "Apply with your Naukri profile" popup
            for confirm_sel in [
                "button:has-text('Apply')",
                "button:has-text('Submit')",
                "button[class*='chatbot_apply']",
                "button[class*='submit']",
            ]:
                confirm_btn = await jd_page.query_selector(confirm_sel)
                if confirm_btn and confirm_btn != apply_btn:
                    try:
                        await confirm_btn.click()
                        await jd_page.wait_for_timeout(1500)
                    except Exception:
                        pass
                    break

            # Handle Chatbot Questionnaire
            try:
                chatbot_input_sel = "div[class*='chatbot_InputContainer'] div.textArea"
                for _ in range(8):  # max 8 questions
                    # Wait briefly for input box to appear
                    try:
                        chatbot_input = await jd_page.wait_for_selector(chatbot_input_sel, timeout=3000)
                    except:
                        chatbot_input = None

                    if not chatbot_input:
                        break # no more questions
                    
                    if not await chatbot_input.is_visible():
                        break

                    # Get the last question asked by bot
                    msgs = await jd_page.query_selector_all("li.botItem .botMsg span")
                    if not msgs:
                        break
                    question = (await msgs[-1].inner_text()).strip()
                    log.info(f"    [Chatbot] Q: {question}")
                    
                    # Generate AI answer
                    answer = self.matcher.answer_chatbot_question(question)
                    if not answer:
                        answer = "Yes"
                    log.info(f"    [Chatbot] A: {answer}")
                    
                    # Type answer like a human to trigger React events on contenteditable
                    await chatbot_input.click()
                    await jd_page.keyboard.type(answer, delay=10)
                    await jd_page.wait_for_timeout(1000)
                    
                    # Click send
                    send_btn = await jd_page.query_selector("div.sendMsg")
                    if send_btn:
                        await send_btn.click()
                        await jd_page.wait_for_timeout(2500)
                    else:
                        break
            except Exception as e:
                log.warning(f"    [Chatbot] Error handling questionnaire: {e}")

            self.app_log.record(
                job["job_id"], job["title"], job["company"],
                job.get("age_text", "unknown"), score, reason
            )
            self.applied_count += 1

        except PWTimeout:
            log.warning(f"Timeout applying to {job['title']}")
        except Exception as e:
            log.error(f"Apply error for {job['title']}: {e}")
        finally:
            if jd_page:
                try:
                    await jd_page.close()
                except Exception:
                    pass

    async def run_keyword(self, keyword: str):
        """Process all jobs for a single search keyword."""
        await self.search_jobs(keyword)

        try:
            cards = await self.get_job_cards()
        except PWTimeout:
            log.warning(f"No job cards found for keyword: {keyword}")
            return

        log.info(f"Found {len(cards)} job cards for '{keyword}'")

        # ── Extract all cards with their age first ──────────────────────────
        all_jobs = []
        for card in cards:
            job = await self.extract_job_details(card)
            if job and job.get("job_id"):
                all_jobs.append(job)

        # ── Filter: skip jobs older than max_age_days ───────────────────────
        fresh_jobs = [j for j in all_jobs if j["age_days"] <= self.max_age_days]
        skipped_old = len(all_jobs) - len(fresh_jobs)
        if skipped_old:
            log.info(f"  [FILTER] Skipped {skipped_old} jobs older than {self.max_age_days} days")

        # ── Sort: priority jobs (<= priority_age_days) go first ────────────
        fresh_jobs.sort(key=lambda j: j["age_days"])
        priority = [j for j in fresh_jobs if j["age_days"] <= self.priority_age_days]
        rest     = [j for j in fresh_jobs if j["age_days"] >  self.priority_age_days]
        if priority:
            log.info(f"  [PRIORITY] {len(priority)} jobs posted within {self.priority_age_days} day(s) → processing first")
        ordered_jobs = priority + rest

        # ── Process ─────────────────────────────────────────────────────────
        for i, job in enumerate(ordered_jobs):
            if self.applied_count >= self.max_jobs:
                log.info(f"Reached max jobs limit ({self.max_jobs}). Stopping.")
                return

            # Skip already applied
            if self.app_log.already_applied(job["job_id"]):
                log.info(f"[{i+1}] Already applied: {job['title']} @ {job['company']}")
                continue

            age_label = f"{job['age_days']}d ago" if job['age_days'] > 0 else "today"
            log.info(f"[{i+1}] Evaluating ({age_label}): {job['title']} @ {job['company']}")

            # Fetch JD
            jd_text = await self.get_jd_text(job["href"]) if job.get("href") else ""

            # AI Evaluation
            should_apply, score, reason = self.matcher.should_apply(job["title"], jd_text)

            if should_apply:
                log.info(f"    → Applying [score={score}%]: {reason}")
                await self.apply_to_job(job, score, reason)
                await self.page.wait_for_timeout(1000)
            else:
                log.info(f"    → Skipping [score={score}%]: {reason}")

    async def run(self):
        async with async_playwright() as playwright:
            browser = await self.attach_browser(playwright)
            try:
                for keyword in self.keywords:
                    if self.applied_count >= self.max_jobs:
                        break
                    await self.run_keyword(keyword)
                    await self.page.wait_for_timeout(2000)  # polite delay between searches
            finally:
                log.info(f"\n[DONE] Session complete. Applied to {self.applied_count} jobs.")
                log.info(f"[LOG]  Saved to: {LOG_CSV}")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
async def main():
    log.info("=" * 60)
    log.info("Naukri Auto-Apply Bot Starting")
    log.info("=" * 60)

    params = load_params()
    log.info(f"Loaded parameters for: {params.get('name')}")

    resume_text = load_resume_text(params)
    log.info(f"Resume loaded ({len(resume_text)} chars)")

    matcher = AIJobMatcher(resume_text, params)
    app_log = ApplicationLog()

    bot = NaukriBot(params, matcher, app_log)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
