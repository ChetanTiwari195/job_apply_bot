# ========================================
# JOB APPLICATION PARAMETERS
# Base config for Naukri Auto-Apply Bot
# ========================================

# ---------- CANDIDATE INFO ----------
name: Chetan Tiwari
email: tiwarichetan212@gmail.com
phone: 7007113884
location_current: Bengaluru
linkedin: https://linkedin.com/in/chetan56tiwari
github: https://github.com/ChetanTiwari195

# ---------- ROLE PREFERENCES ----------
# NOTE: Do NOT match these titles exactly.
# Let AI find semantically similar roles based on skills and context.
roles:
  - Software Development Engineer
  - Backend Engineer
  - Full Stack Developer
  - Python Developer
  - Software Engineer
  - SDE-2
  - Backend Developer
  - AI/ML Engineer
  - API Developer
  - Platform Engineer
  - Data Engineer
  - MLOps Engineer
  - GenAI Engineer

role_matching_mode: ai_semantic  # AI decides relevance, not exact title match

role_keywords:  # broad search terms for Naukri (intentionally wide)
  - Python Developer
  - Backend Developer
  - Full Stack Developer
  - Software Engineer
  - API Developer
  - AI Engineer
  - LLM Engineer
  - FastAPI Developer
  - GenAI Developer
  - Platform Engineer

# ---------- EXPERIENCE ----------
total_experience: 3+ years   # May 2024 - Present
current_company: FinBox
current_role: Software Engineer
current_ctc: 12 LPA
expected_ctc: 16 LPA or more

# Experience filter for JD matching:
min_experience_years: 2   # apply if JD requires 2+ years
max_experience_years: null  # no upper cap (apply to senior roles too)

# Experience breakdown:
#   FinBox            (Sep 2025 - Present)    : Software Engineer
#   Cronbay Technologies (May 2024 - Sep 2025): Full Stack Developer

# ---------- LOCATION PREFERENCES ----------
preferred_locations:
  - Anywhere
  - Remote
  - Hybrid
  - Bengaluru
  - Work from home

# ---------- SALARY FILTER RULES ----------
# If salary NOT mentioned in JD  → apply anyway
# If salary IS mentioned in JD   → only apply if >= 16 LPA
min_expected_lpa: 16
apply_if_salary_not_mentioned: true

# ---------- TECHNICAL SKILLS ----------
languages:
  - Python
  - TypeScript
  - Go (Golang)

backend:
  - FastAPI
  - Django
  - GraphQL
  - Kafka
  - Temporal

ai_ml:
  - LLM Integration (OpenAI, Claude)
  - RAG
  - MCP
  - LangChain

frontend:
  - React.js
  - Next.js
  - Tailwind CSS

databases_devops:
  - PostgreSQL
  - Redis
  - Docker
  - CI/CD
  - AWS (EC2, S3, Lambda, Bedrock)

other_skills:
  - JWT Authentication
  - OAuth2
  - RBAC
  - Microservices
  - REST APIs
  - Webhook integrations
  - n8n automation

# ---------- KEY HIGHLIGHTS (used by AI matcher) ----------
highlights:
  - Built 150+ APIs and 12+ microservices serving 1M+ API requests
  - Owned 4 lender loan journeys (Axis Finance, Hero FinCorp, L&T Finance, Aditya Birla Finance)
  - Built Seedhe Mock - internal API virtualization platform adopted by 10-20 engineers
  - Delivered 4 production-grade web apps end-to-end
  - Migrated PHP/Laravel to FastAPI → 7-10x latency improvement
  - Built AI Resume Optimizer Chrome Extension (published on Chrome Web Store)
  - LLM-powered lead generation automation → 73% increase in outreach
  - 50% user retention increase via Next.js migration

# ---------- EDUCATION ----------
education:
  - degree: Executive Diploma in Machine Learning & Artificial Intelligence
    institute: IIIT Bangalore
    year: 2026 - Present
  - degree: B.Tech, Computer Science and Engineering
    institute: HKBK College of Engineering
    year: 2020 - 2024

# ---------- AUTOMATION SETTINGS ----------
naukri_login: user_will_provide_active_window
apply_mode: fully_automated
ai_relevance_threshold: 80      # only apply if AI match score >= 80%
max_jobs_per_run: 50            # safety cap per session
skip_already_applied: true
log_applications: true
log_file: applied_jobs.csv

# ---------- JOB FRESHNESS FILTER ----------
max_job_age_days: 7     # skip any job posted more than 7 days ago
priority_age_days: 1    # jobs posted within 1 day are processed first

# ---------- JD KEYWORD FILTERS ----------
# Skip job if ANY of these appear as primary required skill:
blacklist_keywords:
  - PHP
  - Ruby
  - .NET
  - C#
  - Java
  - Android
  - iOS
  - Mobile Developer
  - Salesforce

# Boost score if JD contains ANY of these:
preferred_keywords:
  - Python
  - FastAPI
  - Backend
  - AI
  - LLM
  - API
  - Microservices
  - React
  - Full Stack
  - TypeScript
  - Go
  - Golang

# ---------- RESUME PATHS ----------
resume_pdf: d:/trial/resume/Chetan_Tiwari.pdf
resume_tex: d:/trial/resume/Chetan_Tiwari.tex
