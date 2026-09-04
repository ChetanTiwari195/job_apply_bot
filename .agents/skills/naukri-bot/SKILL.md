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
3. **Environment Variables**: An `.env` file must exist with `OPENROUTER_API_KEY`.
4. **Browser State**: The user MUST have a Chrome instance running with `--remote-debugging-port=9222` and be logged into Naukri.com. If they haven't started this, provide them with the command to run in a separate terminal:
   `& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome-debug"`
5. **Configuration**: Check that `job_parameters.md` has the desired role keywords, expected salary, and AI threshold.

## Execution
Run the bot as a background task using the `run_command` tool:
```powershell
.\venv\Scripts\python.exe naukri_bot.py
```
Monitor its progress by reading the background task logs or `bot.log`. 

## Troubleshooting
- **UnicodeEncodeError (charmap)**: If the bot crashes on Windows due to emojis in logs, ensure the script's Python `logging` configuration explicitly sets `encoding="utf-8"`.
- **Target Closed / Playwright Timeout**: If the bot fails to attach, the user's Chrome instance is likely not running with the correct remote debugging port, or the port is in use.
- **Chatbot Stuck**: If the bot fails to answer sidebar questions on Naukri, ensure the selector logic in `apply_to_job` (e.g., `press_sequentially()` or `.click()` + `keyboard.type()`) is correctly triggering React's `onInput` events on the `contenteditable` div. Do NOT use `.fill()` on the chatbot input, as it bypasses React state.
