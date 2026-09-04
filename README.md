# Naukri Auto-Apply Bot 🤖

Automates job applications on Naukri.com using **Playwright** (browser automation) + **OpenRouter AI** (JD matching & Chatbot answering).

---

## Features
- **Smart JD Matching:** Evaluates the Job Description against your resume using AI to score relevance (0-100%).
- **Freshness Filter:** Automatically skips jobs older than 1 week (or custom limits) to save time and API credits.
- **Priority Sorting:** Processes jobs posted today/yesterday before looking at older postings.
- **Chatbot Questionnaire Handler:** Automatically answers Naukri recruiter screening questions (e.g. "Notice Period", "CTC", "Experience") using AI to maximize your selection rate.
- **External Apply Notifications:** Detects if a job requires applying on an external company site and sends the job link directly to your **Telegram**.
- **Auto-Apply:** Skips previously applied jobs and logs them to `applied_jobs.csv` with timestamps and auto-incrementing serial numbers.

---

## Setup (One Time)

### 1. Install Requirements
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Your Profile & API Key
- Get an OpenRouter API key from [OpenRouter](https://openrouter.ai/).
- Copy `.env.example` to `.env` (or create `.env`) and add:
  ```env
  OPENROUTER_API_KEY=your_key_here
  OPENROUTER_MODEL=deepseek/deepseek-chat-v3-0324:free
  ```
- **Optional**: To enable Telegram notifications for external job links, talk to `@BotFather` and `@userinfobot` on Telegram to get your bot token and chat ID, then add them to `job_parameters.md`.
- Copy `job_parameters.example.md` to `job_parameters.md` and edit it to configure your name, target roles, salary, and blacklist keywords. Alternatively, ask the AI to generate one for you!
- Place your resume (PDF or LaTeX) in the `resume/` directory and update the path in `job_parameters.md` if necessary (script auto-detects it).

---

## Running the Bot

### Step 1: Launch Chrome with Remote Debugging
Open a new terminal and run:
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome-debug"
```
> This opens a fresh Chrome instance that Playwright can attach to.

### Step 2: Log in to Naukri
- In that Chrome window, navigate to https://www.naukri.com and log in normally.

### Step 3: Run the Bot
In a separate terminal (with the virtual environment activated):
```powershell
cd path\to\repo
.\venv\Scripts\Activate.ps1
python naukri_bot.py
```

---

## How It Works

```text
Search Naukri for roles in job_parameters.md → For each keyword:
    1. Extract all job cards on the page.
    2. Filter out old jobs (> max_job_age_days) and sort by newest.
    3. Quick keyword filter (blacklist check + salary check).
    4. Fetch full Job Description.
    5. AI scores JD vs your resume (0-100%).
    6. If score >= threshold → Click Apply on JD page.
    7. If Naukri recruiter Chatbot pops up, AI automatically answers questions.
    8. If it redirects to a company site, bot sends a Telegram alert with the link.
    9. Log result to applied_jobs.csv.
```

## Files

| File | Purpose |
|------|---------|
| `naukri_bot.py` | Main automation script |
| `job_parameters.md` | Your profile, skills, preferences |
| `.env` | API key (keep private!) |
| `applied_jobs.csv` | Auto-generated log of all applications |
| `requirements.txt` | Python dependencies |

## Customization

Edit `.env` to configure automation behavior:
- `AI_RELEVANCE_THRESHOLD` — how strict the AI filter is (80 = 80%).
- `MAX_JOB_AGE_DAYS` — skip jobs older than this.

Edit `job_parameters.md` to change your profile:
- `role_keywords` — what to search on Naukri.
- `blacklist_keywords` — instantly skip these job types.
