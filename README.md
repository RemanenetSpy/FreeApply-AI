# 🚀 FreeApply-AI

> **100% Free, Open-Source Cold Outreach & AI Personalization Engine for Job Seekers**  
> Bypass the "Easy Apply" black hole. Automate tailored recruiter outreach with Gmail and Google Gemini—with zero monthly subscriptions.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![AI: Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini%202.5-orange.svg)](https://aistudio.google.com/)

---

## 💡 The Problem

Millions of talented job seekers face two crippling roadblocks:

1. **The "Easy Apply" Black Hole:** Applying through LinkedIn or job boards puts your resume into an ATS queue alongside 1,000+ applicants. Less than 2% of standard applications ever get viewed by a human.
2. **Expensive SaaS Tools:** Sales outreach platforms like Apollo, Lemlist, or Hunter charge **\$40 to \$100/month**—an unreasonable burden for anyone between jobs or transitioning careers.

**FreeApply-AI** gives every job seeker an enterprise-grade, privacy-respecting outreach engine that runs locally on your machine at **$0 cost**.

---

## ✨ Features

* 📱 **Mobile & Desktop Web UI (`app.py`):** Clean, zero-terminal interface accessible on any Android or iOS device or desktop browser.
* 🤖 **AI-Powered Personalization (`personalize.py`):** Uses Google Gemini 2.5 Flash to read your resume PDF and craft authentic, company-specific 1–2 sentence opening hooks for every lead.
* 🛡️ **Anti-Spam & Inbox Reputation Guard:** Hardcoded randomized 30–60s delays between sends, duplicate email detection, and a default 35 emails/day safety cap to protect your Gmail reputation.
* 👁️ **Dry-Run Mode by Default:** Preview exactly what every recruiter will receive before a single email is dispatched.
* 📎 **Seamless Resume Attachment:** Automatically attaches your PDF resume with proper MIME encoding.
* 🔁 **Automated Follow-Up Pipeline:** Seamlessly follow up on unresponded applications with custom follow-up templates and automatic subject threading (`Re: ...`).
* 📊 **Persistent Knowledge Graph:** Export your candidate $\rightarrow$ company touch graph (`log.md`) directly to your phone or laptop.
* 🔒 **Local & 100% Private:** Your leads, sent history, credentials, and resume never leave your local session.

---

## 📁 Repository Structure

```
FreeApply-AI/
├── .gitignore               # Strict ignore rules for .env, PDFs, and personal CSVs
├── .env.example             # Clean configuration template
├── LICENSE                  # Permissive MIT License
├── requirements.txt         # Dependencies (streamlit, google-genai, pymupdf, python-dotenv)
├── README.md                # Project documentation
├── app.py                   # Mobile & desktop Streamlit Web App
├── send_outreach.py         # Core email automation engine (SMTP, throttling, dry-run)
├── personalize.py           # Gemini AI hook generator CLI
├── leads.example.csv        # Starter spreadsheet format for your leads
├── followups.example.csv    # Starter format for follow-ups
└── templates/               # Modular email templates
    ├── operations_outreach.txt
    ├── engineering_outreach.txt
    ├── general_outreach.txt
    └── followup.txt
```

---

## ⚡ 5-Minute Quickstart

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/RemanenetSpy/FreeApply-AI.git
cd FreeApply-AI
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Open `.env` and fill in your details:
* **`SMTP_EMAIL`**: Your Gmail address.
* **`SMTP_APP_PASSWORD`**: A 16-character Gmail App Password ([How to generate](https://myaccount.google.com/apppasswords): enable 2-Step Verification on your Google Account, search for "App Passwords", generate one labeled `FreeApply-AI`).
* **`SENDER_NAME`**: Your full name.
* **`RESUME_PATH`**: Path to your resume PDF (e.g. `resume.pdf`).
* **`GEMINI_API_KEY`**: (Optional) Free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 3. Add Target Leads

Copy the example CSV:
```bash
cp leads.example.csv leads.csv
```

Edit `leads.csv` with your target companies:
```csv
name,email,company,role,custom_hook
Jane Doe,jane.doe@examplecorp.com,ExampleCorp,Operations Lead,
Alex Smith,alex.smith@techinnovators.io,TechInnovators,Backend Engineer,
```

---

## 🌐 Launch the Web Interface (Zero Terminal / Mobile Friendly)

Run the local Streamlit web application:
```bash
streamlit run app.py
```
This opens an intuitive, mobile-responsive dashboard in your browser where you can:
* **Upload Resume & Credentials**: Enter your Gmail App Password and upload your resume PDF through clean forms.
* **Edit Leads in Real-Time**: View and edit your leads in an interactive data table.
* **1-Tap AI Personalization**: Tap **"🤖 Generate AI Hooks"** to let Gemini 2.5 Flash research and craft opening hooks.
* **Live Email Preview & Dispatch**: Inspect rendered emails and dispatch with safe 30–45s randomized delays.
* **Export Knowledge Graph**: Download your updated touch history (`log.md`) and delivery logs (`sent_history.csv`) directly to your phone or PC.

### 📱 Free Cloud Deployment for Android & iOS (No Computer Needed)
Anyone can access their own private outreach app from an iPhone or Android phone without installing anything:
1. Fork or push this repository to GitHub.
2. Go to **[share.streamlit.io](https://share.streamlit.io/)** (100% free) and sign in with GitHub.
3. Click **"New App"**, select `FreeApply-AI`, and set the file path to `app.py`.
4. Click **Deploy**!
5. Open your app link on your phone's browser, bookmark it or tap **"Add to Home Screen"**, and run your job hunt from anywhere.

---

## 🛠️ Usage Guide (CLI Option)

### Step 1: AI Personalization (Optional)

Automatically generate personalized opening hooks for each company using your resume:

```bash
python personalize.py --resume resume.pdf --csv leads.csv
```

Gemini reads your resume, researches the company/role context, and populates the `custom_hook` column in `leads.csv`.

---

### Step 2: Test SMTP Connection

Send a test email to your own inbox to verify that SMTP delivery and resume attachments work:

```bash
python send_outreach.py --test-me
```

Check your inbox to confirm arrival.

---

### Step 3: Preview Emails (Dry Run)

Always run a dry run first to inspect the rendered templates:

```bash
python send_outreach.py --dry-run
```

This renders the subject line and email body for the first 3 leads without sending anything.

---

### Step 4: Dispatch Outreach

Once you are satisfied with the preview, send live applications:

```bash
python send_outreach.py --send
```

* Each email is sent with a randomized 30–60 second delay to protect inbox deliverability.
* All successful sends are logged to `sent_history.csv` to ensure no person is ever contacted twice.
* Halts automatically if the daily limit (default: 35) is reached.

---

### Step 5: Follow-Ups

To send polite follow-ups 3–5 business days later:

```bash
# Preview followups
python send_outreach.py --followup --dry-run

# Send followups
python send_outreach.py --followup --send
```

Or process both follow-ups and new outreach sequentially:
```bash
python send_outreach.py --all --send
```

---

## 🎯 Command Reference

| Command | Description |
| :--- | :--- |
| `python send_outreach.py --test-me` | Sends a single test email to yourself |
| `python send_outreach.py --dry-run` | Previews email rendering without sending |
| `python send_outreach.py --send` | Sends pending outreach with throttling |
| `python send_outreach.py --followup --dry-run` | Previews follow-up emails |
| `python send_outreach.py --followup --send` | Sends pending follow-ups |
| `python send_outreach.py --all --send` | Runs follow-ups, pauses, then runs new outreach |
| `python send_outreach.py --template <path>` | Uses a specific email template file |
| `python send_outreach.py --csv <path>` | Uses a custom CSV file |
| `python send_outreach.py --resume <path>` | Specifies a custom PDF resume to attach |
| `python send_outreach.py --limit <N>` | Limits current batch to N emails |
| `python personalize.py --resume <pdf>` | Enriches leads CSV with Gemini-generated hooks |
| `python personalize.py --dry-run` | Previews AI hook generation without saving |

---

## 🛡️ Responsible Outreach Ethics

* **Respect Recruiter Time:** Only reach out to relevant recruiters or hiring managers for roles matching your background.
* **Keep Volume Safe:** Never exceed 40 cold emails per day on a personal Gmail account.
* **Always Provide Value:** Cold emails should be concise (under 150 words) and focus on how you can solve problems for their team.
* **Honor Opt-Outs:** If someone replies asking not to be contacted, remove them immediately.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
