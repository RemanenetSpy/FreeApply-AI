#!/usr/bin/env python3
"""
FreeApply-AI: Automated, Safe, and Personalized Job Outreach Engine
------------------------------------------------------------------
A lightweight CLI tool to automate cold email outreach for job seekers
with randomized throttling, anti-spam safeguards, and template rendering.

Usage:
  python send_outreach.py --test-me
  python send_outreach.py --dry-run
  python send_outreach.py --send
  python send_outreach.py --followup --dry-run
  python send_outreach.py --all --send
"""

import argparse
import csv
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import random
import smtplib
import ssl
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ENV_FILE = os.path.join(BASE_DIR, ".env")
DEFAULT_LEADS_FILE = os.path.join(BASE_DIR, "leads.csv")
DEFAULT_FOLLOWUPS_FILE = os.path.join(BASE_DIR, "followups.csv")
DEFAULT_TEMPLATE_FILE = os.path.join(BASE_DIR, "templates", "operations_outreach.txt")
DEFAULT_FOLLOWUP_TEMPLATE = os.path.join(BASE_DIR, "templates", "followup.txt")
DEFAULT_LOG_FILE = os.path.join(BASE_DIR, "sent_history.csv")


def load_env(env_path: str) -> dict:
    """Load configuration from .env file or system environment variables."""
    config = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip().strip("\"'")

    # System environment variables take precedence
    for k, v in os.environ.items():
        config[k] = v
    return config


def get_today_sent_count(log_path: str) -> int:
    """Calculate the number of successful sends today."""
    if not os.path.exists(log_path):
        return 0
    today_str = datetime.now().strftime("%Y-%m-%d")
    count = 0
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 3 and row[0].startswith(today_str) and row[2].strip().upper() == "SUCCESS":
                    count += 1
    except Exception:
        pass
    return count


def get_sent_emails(log_path: str) -> set:
    """Retrieve all email addresses that have already received successful outreach."""
    sent = set()
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3 and row[2].strip().upper() == "SUCCESS":
                        sent.add(row[1].strip().lower())
        except Exception:
            pass
    return sent


def log_send_result(log_path: str, email: str, status: str, error: str = ""):
    """Record send outcome into an audit log CSV."""
    file_exists = os.path.exists(log_path)
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Email", "Status", "Details"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), email, status, error])


def render_template(template_path: str, data: dict) -> tuple[str, str]:
    """Parse email template and substitute dynamic variable placeholders."""
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found at: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    for key, value in data.items():
        content = content.replace(f"{{{{{key}}}}}", str(value))

    lines = content.splitlines()
    subject = "Application"
    body_lines = []

    for line in lines:
        if line.lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
        else:
            body_lines.append(line)

    return subject, "\n".join(body_lines).strip()


def get_ssl_context():
    """Create SSL context with system cert injection where available."""
    try:
        import truststore
        truststore.inject_into_ssl()
    except Exception:
        pass
    try:
        return ssl.create_default_context()
    except Exception:
        return ssl._create_unverified_context()


def send_single_email(
    smtp_server: str,
    port: int,
    sender_email: str,
    app_password: str,
    recipient_email: str,
    subject: str,
    body: str,
    sender_name: str = "",
    attachment_path: str | None = None,
):
    """Deliver an email over SMTP (SSL / STARTTLS) with optional PDF attachment."""
    msg = MIMEMultipart()
    display_from = f"{sender_name} <{sender_email}>" if sender_name else sender_email
    msg["From"] = display_from
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
        part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        msg.attach(part)

    context = get_ssl_context()
    port = int(port)

    def _deliver(ssl_ctx):
        if port == 465:
            with smtplib.SMTP_SSL(smtp_server, port, context=ssl_ctx, timeout=25) as server:
                server.login(sender_email, app_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())
        else:
            with smtplib.SMTP(smtp_server, port, timeout=25) as server:
                server.starttls(context=ssl_ctx)
                server.login(sender_email, app_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())

    try:
        _deliver(context)
    except ssl.SSLCertVerificationError:
        unverified_context = ssl._create_unverified_context()
        _deliver(unverified_context)


def execute_batch(
    csv_file: str,
    template_file: str,
    mode_label: str,
    smtp_config: dict,
    attachment_path: str | None,
    dry_run: bool = True,
    max_batch_limit: int | None = None,
) -> int:
    """Process a list of leads or follow-ups with safety gates and delay throttling."""
    if not os.path.exists(csv_file):
        print(f"[!] Target CSV not found: {csv_file}")
        return 0

    with open(csv_file, "r", encoding="utf-8") as f:
        leads = list(csv.DictReader(f))

    if not leads:
        print(f"[!] No entries found in {csv_file}")
        return 0

    sent_emails = get_sent_emails(DEFAULT_LOG_FILE)
    pending = [l for l in leads if l.get("email", "").strip().lower() not in sent_emails]

    print(f"\n{'=' * 60}")
    print(f"BATCH: {mode_label} ({len(pending)} pending out of {len(leads)} total)")
    print(f"{'=' * 60}")

    if not pending:
        print(f"[*] All {mode_label} contacts have already been reached in {DEFAULT_LOG_FILE}.")
        return 0

    if max_batch_limit and max_batch_limit > 0:
        pending = pending[:max_batch_limit]
        print(f"[*] Limiting current batch to {len(pending)} leads as requested.")

    # DRY RUN / PREVIEW MODE
    if dry_run:
        print(f"[*] Running in DRY-RUN mode. No actual emails will be sent.")
        preview_count = min(3, len(pending))
        for idx, lead in enumerate(pending[:preview_count], 1):
            lead_data = {
                "name": lead.get("name", "Hiring Team"),
                "email": lead.get("email", ""),
                "company": lead.get("company", "your company"),
                "role": lead.get("role", "Target Role"),
                "custom_hook": lead.get("custom_hook", ""),
                "original_subject": lead.get("original_subject", f"Application for {lead.get('role', 'Target Role')}"),
                "sender_name": smtp_config.get("sender_name", ""),
            }
            subj, body = render_template(template_file, lead_data)
            print(f"\n--- [Preview #{idx}] To: {lead.get('email')} ({lead.get('name')}) ---")
            print(f"Subject: {subj}")
            print(f"Attachment: {os.path.basename(attachment_path) if attachment_path else 'None'}")
            print(f"Body snippet:\n{body[:280]}...\n")

        print(f"[+] Dry run complete. {len(pending)} emails ready to send with --send.")
        return len(pending)

    # LIVE SEND MODE
    daily_limit = int(smtp_config.get("daily_limit", 35))
    min_delay = int(smtp_config.get("min_delay", 30))
    max_delay = int(smtp_config.get("max_delay", 60))

    sent_today = get_today_sent_count(DEFAULT_LOG_FILE)
    if sent_today >= daily_limit:
        print(f"[!] Safety Alert: Daily limit of {daily_limit} emails reached today ({sent_today} sent). Halting.")
        return 0

    sent_in_this_run = 0
    for idx, lead in enumerate(pending, 1):
        if sent_today + sent_in_this_run >= daily_limit:
            print(f"\n[!] Daily limit ({daily_limit}) reached during batch. Stopping cleanly to preserve inbox health.")
            break

        rec_email = lead.get("email", "").strip()
        lead_data = {
            "name": lead.get("name", "Hiring Team"),
            "email": rec_email,
            "company": lead.get("company", "your company"),
            "role": lead.get("role", "Target Role"),
            "custom_hook": lead.get("custom_hook", ""),
            "original_subject": lead.get("original_subject", f"Application for {lead.get('role', 'Target Role')}"),
            "sender_name": smtp_config.get("sender_name", ""),
        }
        subj, body = render_template(template_file, lead_data)

        print(f"[{idx}/{len(pending)}] Sending {mode_label} to {lead.get('name')} <{rec_email}> at {lead.get('company')}...")
        sys.stdout.flush()

        try:
            send_single_email(
                smtp_config["server"],
                smtp_config["port"],
                smtp_config["email"],
                smtp_config["password"],
                rec_email,
                subj,
                body,
                smtp_config["sender_name"],
                attachment_path=attachment_path,
            )
            print("   [+] Delivered successfully!")
            log_send_result(DEFAULT_LOG_FILE, rec_email, "SUCCESS")
            sent_in_this_run += 1
        except Exception as e:
            print(f"   [-] Failed to deliver: {e}")
            log_send_result(DEFAULT_LOG_FILE, rec_email, "FAILED", str(e))
        sys.stdout.flush()

        if idx < len(pending):
            delay = random.randint(min_delay, max_delay)
            print(f"   [*] Throttling delay: waiting {delay}s before next send...")
            sys.stdout.flush()
            time.sleep(delay)

    return sent_in_this_run


def main():
    parser = argparse.ArgumentParser(
        description="FreeApply-AI: Safe & Automated Cold Outreach for Job Seekers",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--test-me", action="store_true", help="Send a test verification email to your own address")
    parser.add_argument("--dry-run", action="store_true", help="Preview email generation without sending (default)")
    parser.add_argument("--send", action="store_true", help="Send pending emails with active rate-limiting")
    parser.add_argument("--followup", action="store_true", help="Target followups.csv using followup template")
    parser.add_argument("--all", action="store_true", help="Process both follow-ups and new outreach in sequence")
    parser.add_argument("--template", type=str, default=None, help="Custom template file path")
    parser.add_argument("--csv", type=str, default=None, help="Custom leads CSV file path")
    parser.add_argument("--resume", type=str, default=None, help="Path to PDF resume to attach")
    parser.add_argument("--no-resume", action="store_true", help="Do not attach any resume file")
    parser.add_argument("--limit", type=int, default=None, help="Max emails to send in this run")
    parser.add_argument("--env", type=str, default=DEFAULT_ENV_FILE, help="Path to custom .env file")

    args = parser.parse_args()

    print("=" * 60)
    print("        FreeApply-AI Cold Outreach Automation Engine        ")
    print("=" * 60)

    config = load_env(args.env)
    smtp_config = {
        "server": config.get("SMTP_SERVER", "smtp.gmail.com"),
        "port": int(config.get("SMTP_PORT", 465)),
        "email": config.get("SMTP_EMAIL", "").strip(),
        "password": config.get("SMTP_APP_PASSWORD", "").strip().replace(" ", ""),
        "sender_name": config.get("SENDER_NAME", "Job Seeker").strip(),
        "daily_limit": int(config.get("DAILY_SEND_LIMIT", 35)),
        "min_delay": int(config.get("MIN_DELAY_SECONDS", 30)),
        "max_delay": int(config.get("MAX_DELAY_SECONDS", 60)),
    }

    if not smtp_config["email"] or not smtp_config["password"] or "xxxx" in smtp_config["password"]:
        print("\n[!] Setup Required: Configure your credentials in .env")
        print("    1. Copy .env.example to .env")
        print("    2. Add your Gmail address and 16-character App Password")
        sys.exit(1)

    # Resume attachment logic
    resume_path = None
    if not args.no_resume:
        candidate_resume = args.resume or config.get("RESUME_PATH") or os.path.join(BASE_DIR, "resume.pdf")
        if candidate_resume and os.path.exists(candidate_resume):
            resume_path = candidate_resume
        elif args.resume:
            print(f"[!] Warning: Specified resume file not found: {args.resume}")

    # TEST MODE
    if args.test_me:
        print(f"\n[TEST MODE] Delivering verification email to {smtp_config['email']}...")
        if resume_path:
            print(f"[*] Attached resume: {os.path.basename(resume_path)}")
        subj = "FreeApply-AI: SMTP Verification Test"
        body = (
            f"Hello {smtp_config['sender_name']},\n\n"
            f"Congratulations! Your FreeApply-AI SMTP configuration is working perfectly.\n\n"
            f"- Sender Address: {smtp_config['email']}\n"
            f"- Resume Attached: {'Yes (' + os.path.basename(resume_path) + ')' if resume_path else 'No'}\n"
            f"- Daily Safety Cap: {smtp_config['daily_limit']} emails/day\n\n"
            f"You are now ready to run dry-run previews or dispatch tailored applications!"
        )
        try:
            send_single_email(
                smtp_config["server"],
                smtp_config["port"],
                smtp_config["email"],
                smtp_config["password"],
                smtp_config["email"],
                subj,
                body,
                smtp_config["sender_name"],
                attachment_path=resume_path,
            )
            print("[SUCCESS] Test email delivered! Check your inbox or spam folder.")
        except Exception as e:
            print(f"[FAILED] Error sending test email: {e}")
        return

    # DRY RUN vs LIVE SEND
    is_dry_run = args.dry_run or (not args.send and not args.all)

    # File selections
    leads_file = args.csv or (DEFAULT_FOLLOWUPS_FILE if args.followup else DEFAULT_LEADS_FILE)
    template_file = args.template or (
        DEFAULT_FOLLOWUP_TEMPLATE if args.followup else DEFAULT_TEMPLATE_FILE
    )

    if args.all:
        print("\n[*] Processing BOTH Follow-ups and New Outreach...")
        execute_batch(
            DEFAULT_FOLLOWUPS_FILE,
            DEFAULT_FOLLOWUP_TEMPLATE,
            "FOLLOW-UP",
            smtp_config,
            resume_path,
            dry_run=is_dry_run,
            max_batch_limit=args.limit,
        )
        if not is_dry_run:
            print("\n[*] Pausing 45s between batches...")
            time.sleep(45)
        execute_batch(
            DEFAULT_LEADS_FILE,
            DEFAULT_TEMPLATE_FILE,
            "NEW OUTREACH",
            smtp_config,
            resume_path,
            dry_run=is_dry_run,
            max_batch_limit=args.limit,
        )
    else:
        label = "FOLLOW-UP" if args.followup else "NEW OUTREACH"
        execute_batch(
            leads_file,
            template_file,
            label,
            smtp_config,
            resume_path,
            dry_run=is_dry_run,
            max_batch_limit=args.limit,
        )

    print("\n[DONE] Finished execution.")


if __name__ == "__main__":
    main()
