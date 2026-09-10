#!/usr/bin/env python3
"""
FreeApply-AI: Gemini AI Personalization Engine
---------------------------------------------
Generates high-converting, hyper-personalized 1-2 sentence opening hooks
connecting a candidate's background to target companies using Google Gemini.

Usage:
  python personalize.py --resume resume.pdf --csv leads.csv
  python personalize.py --dry-run
"""

import argparse
import csv
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ENV_FILE = os.path.join(BASE_DIR, ".env")
DEFAULT_LEADS_FILE = os.path.join(BASE_DIR, "leads.csv")
DEFAULT_RESUME_FILE = os.path.join(BASE_DIR, "resume.pdf")


def load_env(env_path: str) -> dict:
    config = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip().strip("\"'")
    for k, v in os.environ.items():
        config[k] = v
    return config


def extract_resume_text(resume_path: str) -> str:
    """Extract text from PDF or plain text resume."""
    if not os.path.exists(resume_path):
        raise FileNotFoundError(f"Resume file not found at: {resume_path}")

    ext = os.path.splitext(resume_path)[1].lower()
    if ext == ".txt":
        with open(resume_path, "r", encoding="utf-8") as f:
            return f.read()

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(resume_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return text.strip()
    except ImportError:
        print("[!] PyMuPDF is not installed. Install via: pip install pymupdf")
        sys.exit(1)
    except Exception as e:
        raise RuntimeError(f"Error reading PDF resume: {e}")


def generate_hook_with_gemini(client, model_name: str, candidate_summary: str, company: str, role: str) -> str:
    """Invoke Gemini API to create an authentic 1-2 sentence tailored hook."""
    prompt = f"""You are an elite career strategist and executive copywriter.
Craft a 1 to 2 sentence personalized hook for a cold email to {company} for a {role} position.

Candidate Resume Summary:
\"\"\"{candidate_summary[:2000]}\"\"\"

Target Company: {company}
Target Role: {role}

CRITICAL RULES:
1. Exactly 1 to 2 sentences. No more.
2. Directly bridge a specific candidate strength/accomplishment with {company}'s market focus or operational demands.
3. NEVER use generic cliché phrases like "I was thrilled to see", "I am excited to apply", "Hope this finds you well".
4. Sound natural, professional, confident, and direct.
5. Output ONLY the raw hook sentence(s). No markdown formatting, quotes, or conversational filler.
"""
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return response.text.strip().strip("\"'")
    except Exception as e:
        print(f"[!] Gemini generation error for {company}: {e}")
        return ""


def main():
    parser = argparse.ArgumentParser(
        description="FreeApply-AI: Generate AI-Personalized Outreach Hooks using Gemini",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--csv", type=str, default=None, help="Path to leads CSV (default: leads.csv)")
    parser.add_argument("--resume", type=str, default=None, help="Path to candidate resume PDF/TXT")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="Gemini model to use (default: gemini-2.5-flash)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing custom_hook values")
    parser.add_argument("--dry-run", action="store_true", help="Preview generated hooks without writing to CSV")
    parser.add_argument("--env", type=str, default=DEFAULT_ENV_FILE, help="Path to custom .env file")

    args = parser.parse_args()

    print("=" * 60)
    print("      FreeApply-AI: Gemini AI Personalization Engine        ")
    print("=" * 60)

    config = load_env(args.env)
    api_key = config.get("GEMINI_API_KEY", "").strip()

    if not api_key or "your_gemini" in api_key:
        print("\n[!] Setup Required: GEMINI_API_KEY not found in .env")
        print("    Get your free key at: https://aistudio.google.com/app/apikey")
        print("    Add `GEMINI_API_KEY=your_key_here` to your .env file.")
        sys.exit(1)

    csv_path = args.csv or config.get("LEADS_CSV") or DEFAULT_LEADS_FILE
    if not os.path.exists(csv_path):
        # Fallback to leads.example.csv if leads.csv doesn't exist
        example_csv = os.path.join(BASE_DIR, "leads.example.csv")
        if os.path.exists(example_csv):
            print(f"[*] {csv_path} not found. Using {example_csv} as reference.")
            csv_path = example_csv
        else:
            print(f"[!] Leads CSV file not found: {csv_path}")
            sys.exit(1)

    resume_path = args.resume or config.get("RESUME_PATH") or DEFAULT_RESUME_FILE
    if not os.path.exists(resume_path):
        print(f"[!] Resume file not found at: {resume_path}")
        print("    Please provide --resume <path_to_resume.pdf>")
        sys.exit(1)

    print(f"[*] Reading candidate profile from: {os.path.basename(resume_path)}...")
    resume_text = extract_resume_text(resume_path)
    print(f"    Extracted {len(resume_text.split())} words from resume.")

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except ImportError:
        print("[!] google-genai package is not installed. Install via: pip install google-genai")
        sys.exit(1)

    # Read CSV
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if "custom_hook" not in fieldnames:
        fieldnames.append("custom_hook")

    updated_count = 0
    print(f"[*] Processing {len(rows)} leads in {os.path.basename(csv_path)}...\n")

    for idx, row in enumerate(rows, 1):
        company = row.get("company", "").strip()
        role = row.get("role", "").strip()
        existing_hook = row.get("custom_hook", "").strip()

        if existing_hook and not args.force:
            print(f"[{idx}/{len(rows)}] Skipping {company} (Hook already exists)")
            continue

        print(f"[{idx}/{len(rows)}] Generating hook for {role} at {company}...")
        hook = generate_hook_with_gemini(client, args.model, resume_text, company, role)

        if hook:
            print(f"    -> Generated: \"{hook}\"\n")
            row["custom_hook"] = hook
            updated_count += 1
        else:
            print("    -> [!] Generation skipped or failed.\n")

    if args.dry_run:
        print(f"[*] DRY RUN: {updated_count} hooks generated. Changes NOT saved to file.")
        return

    if updated_count > 0:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"[SUCCESS] Updated {updated_count} leads in {csv_path}!")
    else:
        print("[*] No changes needed.")


if __name__ == "__main__":
    main()
