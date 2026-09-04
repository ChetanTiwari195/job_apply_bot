---
name: naukri-bot
description: Orchestrates and runs the Naukri Auto-Apply Bot. Use this skill when the user asks to run the Naukri bot, apply for jobs, or troubleshoot the Naukri automation script.
---

# Naukri Auto-Apply Bot Skill

This skill enables the agent to understand, configure, and execute the `naukri_bot.py` automation script.

## Context
The Naukri bot automates job applications on Naukri.com. It relies on Playwright to drive a browser and OpenRouter AI to score job descriptions against a candidate's resume and answer screening chatbot questions.

## Prerequisites Check
Before running the bot, always verify:
1. **Virtual Environment**: Ensure `venv` is activated.
2. **Dependencies**: `pip install -r requirements.txt` and `playwright install chromium` must have been run.
3. **Environment Variables**: An `.env` file must exist with `OPENROUTER_API_KEY`, `AI_RELEVANCE_THRESHOLD`, `MAX_JOB_AGE_DAYS`, and `PRIORITY_AGE_DAYS`.
4. **Browser State**: The user MUST have a Chrome instance running with `--remote-debugging-port=9222` and be logged into Naukri.com. If they haven't started this, provide them with the command to run in a separate terminal:
   `& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome-debug"`
5. **Configuration**: Check that `job_parameters.md` has the desired role keywords and expected salary.

## Execution
Run the bot as a background task using the `run_command` tool:
```powershell
.\venv\Scripts\python.exe naukri_bot.py
```
Monitor its progress by reading the background task logs or `bot.log`. 

## Setup (New User)
If a user does not have a `job_parameters.md` file, you must create one for them:
1. Do not use `job_parameters.example.md` directly. Read it to understand the required YAML structure.
2. Ask the user for their Name, Resume (PDF/LaTeX path), current location, preferred roles/keywords, Experience, Current CTC, and Expected CTC. 
3. If they provide a resume, read it and extract the "Key Highlights", "Education", and "Skills" automatically.
4. Generate `job_parameters.md` ensuring the exact YAML structure from the example is maintained.

## Troubleshooting
- **UnicodeEncodeError (charmap)**: If the bot crashes on Windows due to emojis in logs, ensure the script's Python `logging` configuration explicitly sets `encoding="utf-8"`.
- **Target Closed / Playwright Timeout**: If the bot fails to attach, the user's Chrome instance is likely not running with the correct remote debugging port, or the port is in use.
- **Chatbot Stuck**: If the bot fails to answer sidebar questions on Naukri, ensure the selector logic in `apply_to_job` (e.g., `press_sequentially()` or `.click()` + `keyboard.type()`) is correctly triggering React's `onInput` events on the `contenteditable` div. Do NOT use `.fill()` on the chatbot input, as it bypasses React state.
