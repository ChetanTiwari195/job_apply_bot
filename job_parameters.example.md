# ========================================
# JOB APPLICATION PARAMETERS
# Base config for Naukri Auto-Apply Bot
# ========================================

# ---------- CANDIDATE INFO ----------
name: [Your Name]
email: [Your Email]
phone: [Your Phone]
location_current: [Your Location]
linkedin: https://linkedin.com/in/[your-profile]
github: https://github.com/[your-profile]

# ---------- ROLE PREFERENCES ----------
# NOTE: Do NOT match these titles exactly.
# Let AI find semantically similar roles based on skills and context.
roles:
  - Software Development Engineer
  - Backend Engineer
  - Full Stack Developer

role_matching_mode: ai_semantic  # AI decides relevance, not exact title match

role_keywords:  # broad search terms for Naukri (intentionally wide)
  - Software Engineer
  - Backend Developer
  - Full Stack Developer

# ---------- EXPERIENCE ----------
total_experience: [e.g. 3+ years]
current_company: [Current Company or "None"]
current_role: [Current Role]
current_ctc: [e.g. 12 LPA]
expected_ctc: [e.g. 16 LPA or more]

# Experience filter for JD matching:
min_experience_years: 2   # apply if JD requires 2+ years
max_experience_years: null  # no upper cap (apply to senior roles too)
notice_period: 30 days    # used for answering chatbot questions

# ---------- LOCATION PREFERENCES ----------
preferred_locations:
  - Anywhere
  - Remote
  - Hybrid

# ---------- SALARY FILTER RULES ----------
# If salary NOT mentioned in JD  → apply anyway
# If salary IS mentioned in JD   → only apply if >= min_expected_lpa
min_expected_lpa: [e.g. 16]
apply_if_salary_not_mentioned: true

# ---------- TECHNICAL SKILLS ----------
languages:
  - Python
  - JavaScript

backend:
  - Django
  - Node.js

ai_ml:
  - Optional AI Skills

frontend:
  - React.js

databases_devops:
  - PostgreSQL
  - Docker

other_skills:
  - REST APIs
  - Git

# ---------- KEY HIGHLIGHTS (used by AI matcher) ----------
highlights:
  - [Highlight 1 e.g., Built 150+ APIs serving 1M+ requests]
  - [Highlight 2 e.g., Led migration that improved latency by 5x]
  - [Highlight 3]

# ---------- EDUCATION ----------
education:
  - degree: [Degree Name]
    institute: [University Name]
    year: [Year]



# ---------- JD KEYWORD FILTERS ----------
# Skip job if ANY of these appear as primary required skill:
blacklist_keywords:
  - PHP
  - Ruby
  - .NET
  - C#
  - Java
  - iOS
  - Salesforce

# Boost score if JD contains ANY of these:
preferred_keywords:
  - Python
  - AI
  - Backend

# ---------- RESUME PATHS ----------
# IMPORTANT: Put your resume in the resume/ folder and update this path!
resume_pdf: d:/trial/resume/[Your_Resume].pdf
resume_tex: d:/trial/resume/[Your_Resume].tex
