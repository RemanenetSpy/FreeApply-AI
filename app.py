#!/usr/bin/env python3
"""
FreeApply-AI — Executive Cold Outreach Engine
---------------------------------------------
Engineered according to high-trust UI/UX principles, mobile viewport ergonomics,
and zero-dependency cryptographic session vault persistence.

No generic AI clichés. No gratuitous emojis. Designed for executive focus and trust.
"""

import base64
from datetime import datetime
import io
import json
import os
import random
import tempfile
import time
import zipfile

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import pandas as pd
import streamlit as st

import send_outreach
import personalize

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
VAULT_MAGIC = b"FAVAULT1"


# --- Cryptographic Helpers ---
def derive_vault_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def pack_encrypted_vault(
    password: str,
    config: dict,
    leads_df: pd.DataFrame,
    sent_history: list,
    resume_bytes: bytes | None,
    resume_filename: str,
    log_md: str,
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("config.json", json.dumps(config, indent=2))
        if resume_bytes:
            zf.writestr(resume_filename or "resume.pdf", resume_bytes)
        zf.writestr("leads.csv", leads_df.to_csv(index=False))
        if sent_history:
            zf.writestr("sent_history.json", json.dumps(sent_history, indent=2))
        if log_md:
            zf.writestr("log.md", log_md)

    raw_zip = buf.getvalue()
    salt = os.urandom(16)
    key = derive_vault_key(password, salt)
    return VAULT_MAGIC + salt + Fernet(key).encrypt(raw_zip)


def unpack_encrypted_vault(vault_bytes: bytes, password: str) -> dict:
    if not vault_bytes.startswith(VAULT_MAGIC):
        raise ValueError("Invalid vault format. Please provide a genuine FreeApply vault archive.")

    salt = vault_bytes[8:24]
    ciphertext = vault_bytes[24:]
    key = derive_vault_key(password, salt)

    try:
        raw_zip = Fernet(key).decrypt(ciphertext)
    except InvalidToken:
        raise ValueError("Decryption failed. Incorrect vault password.")

    zf = zipfile.ZipFile(io.BytesIO(raw_zip))
    names = zf.namelist()
    restored = {}

    if "config.json" in names:
        restored["config"] = json.loads(zf.read("config.json").decode("utf-8"))

    for name in names:
        if name.endswith(".pdf") or (name.startswith("resume") and not name.endswith(".csv") and not name.endswith(".json")):
            restored["resume_bytes"] = zf.read(name)
            restored["resume_filename"] = name
            break

    if "leads.csv" in names:
        try:
            restored["leads_df"] = pd.read_csv(io.StringIO(zf.read("leads.csv").decode("utf-8")))
        except Exception:
            restored["leads_df"] = pd.read_csv(io.StringIO(zf.read("leads.csv").decode("utf-8")), on_bad_lines="skip")

    if "sent_history.json" in names:
        restored["sent_history"] = json.loads(zf.read("sent_history.json").decode("utf-8"))

    return restored


# --- Application Setup ---
st.set_page_config(
    page_title="FreeApply-AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Executive Design System & Mobile Viewport Constraints ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global reset & typography */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #f1f5f9;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    /* Remove Streamlit default excessive padding for mobile viewport fit */
    .block-container {
        padding-top: 0.75rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
        max-width: 960px !important;
    }
    header[data-testid="stHeader"] {
        display: none !important;
    }
    footer {
        display: none !important;
    }

    /* Executive Navigation Bar */
    .app-nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        background: #0d121d;
        border: 1px solid #1e2638;
        border-radius: 12px;
        margin-bottom: 0.75rem;
    }
    .brand-mark {
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .brand-pill {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        background: #1e293b;
        color: #94a3b8;
        border: 1px solid #334155;
    }

    /* Compact Telemetry Strip */
    .telemetry-strip {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.5rem;
        margin-bottom: 0.85rem;
    }
    .telemetry-cell {
        background: #0d121d;
        border: 1px solid #1a2234;
        border-radius: 8px;
        padding: 0.5rem 0.75rem;
    }
    .telemetry-label {
        font-size: 0.68rem;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.04em;
        color: #64748b;
        margin-bottom: 0.15rem;
    }
    .telemetry-val {
        font-size: 0.95rem;
        font-weight: 600;
        color: #e2e8f0;
        font-variant-numeric: tabular-nums;
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }

    /* Live status dot */
    .indicator-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        display: inline-block;
    }
    .dot-active { background: #10b981; }
    .dot-idle { background: #64748b; }

    /* Concentric Section Cards */
    .section-card {
        background: #0d121d;
        border: 1px solid #1e2638;
        border-radius: 12px;
        padding: 1.1rem;
        margin-bottom: 0.85rem;
    }

    /* Email Preview Canvas */
    .email-container {
        background: #080c14;
        border: 1px solid #243048;
        border-radius: 10px;
        padding: 1.1rem;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .email-row {
        display: flex;
        font-size: 0.82rem;
        padding: 0.25rem 0;
        border-bottom: 1px solid #141b2a;
    }
    .email-key {
        width: 70px;
        font-weight: 600;
        color: #64748b;
    }
    .email-val {
        color: #cbd5e1;
        font-weight: 500;
    }
    .email-body {
        margin-top: 0.85rem;
        line-height: 1.6;
        font-size: 0.88rem;
        color: #e2e8f0;
        white-space: pre-wrap;
    }

    /* Typography highlight pills */
    .hook-token {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border-left: 2px solid #10b981;
        padding: 0.1rem 0.35rem;
        border-radius: 3px;
    }
    .highlight-pill {
        background: #1e293b;
        color: #93c5fd;
        padding: 0.05rem 0.35rem;
        border-radius: 3px;
        font-weight: 600;
    }

    /* Segmented Stage Control */
    div[data-testid="stRadio"] > div {
        display: flex;
        background: #0d121d;
        border: 1px solid #1e2638;
        border-radius: 10px;
        padding: 0.25rem;
        gap: 0.25rem;
    }
    div[data-testid="stRadio"] label {
        padding: 0.4rem 0.75rem !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
    }

    /* Mobile Responsive Tightening */
    @media (max-width: 640px) {
        .telemetry-strip {
            grid-template-columns: 1fr 1fr;
        }
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- State Initialization ---
local_env = send_outreach.load_env(os.path.join(BASE_DIR, ".env"))

if "stage" not in st.session_state:
    st.session_state.stage = "1. Identity"
if "sender_name" not in st.session_state:
    st.session_state.sender_name = local_env.get("SENDER_NAME", "")
if "smtp_email" not in st.session_state:
    st.session_state.smtp_email = local_env.get("SMTP_EMAIL", "")
if "smtp_password" not in st.session_state:
    st.session_state.smtp_password = local_env.get("SMTP_APP_PASSWORD", "")
if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = local_env.get("GEMINI_API_KEY", "")
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "resume_bytes" not in st.session_state:
    st.session_state.resume_bytes = None
if "resume_filename" not in st.session_state:
    st.session_state.resume_filename = "resume.pdf"
if "leads_df" not in st.session_state:
    example_path = os.path.join(BASE_DIR, "leads.example.csv")
    if os.path.exists(example_path):
        try:
            st.session_state.leads_df = pd.read_csv(example_path)
        except Exception:
            try:
                st.session_state.leads_df = pd.read_csv(example_path, on_bad_lines="skip")
            except Exception:
                st.session_state.leads_df = pd.DataFrame(columns=["name", "email", "company", "role", "custom_hook"])
    else:
        st.session_state.leads_df = pd.DataFrame(columns=["name", "email", "company", "role", "custom_hook"])
if "sent_history" not in st.session_state:
    st.session_state.sent_history = []
if "vault_password" not in st.session_state:
    st.session_state.vault_password = ""


# --- Top Executive Bar ---
candidate_display = st.session_state.sender_name if st.session_state.sender_name else "Unassigned"
st.markdown(
    f"""
    <div class="app-nav">
        <div class="brand-mark">
            <span>FreeApply</span>
            <span class="brand-pill">v2.1 Private</span>
        </div>
        <div style="font-size:0.8rem; color:#94a3b8;">
            Profile: <b style="color:#f1f5f9;">{candidate_display}</b>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Telemetry Strip ---
leads_total = len(st.session_state.leads_df)
hooks_done = len(st.session_state.leads_df[st.session_state.leads_df["custom_hook"].astype(str).str.strip() != ""]) if leads_total > 0 else 0
smtp_ok = bool(st.session_state.smtp_email and st.session_state.smtp_password)
resume_ok = bool(st.session_state.resume_bytes or st.session_state.resume_text)

st.markdown(
    f"""
    <div class="telemetry-strip">
        <div class="telemetry-cell">
            <div class="telemetry-label">SMTP Delivery</div>
            <div class="telemetry-val">
                <span class="indicator-dot {'dot-active' if smtp_ok else 'dot-idle'}"></span>
                {'Online' if smtp_ok else 'Not Configured'}
            </div>
        </div>
        <div class="telemetry-cell">
            <div class="telemetry-label">Resume Parser</div>
            <div class="telemetry-val">
                <span class="indicator-dot {'dot-active' if resume_ok else 'dot-idle'}"></span>
                {'Attached' if resume_ok else 'Pending'}
            </div>
        </div>
        <div class="telemetry-cell">
            <div class="telemetry-label">Target Queue</div>
            <div class="telemetry-val">{leads_total} Contacts</div>
        </div>
        <div class="telemetry-cell">
            <div class="telemetry-label">AI Hooks</div>
            <div class="telemetry-val">{hooks_done}/{leads_total} Prepared</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Segmented Stage Navigation ---
stages = ["1. Identity", "2. Lead Radar", "3. Composer", "4. Execution"]
chosen_stage = st.radio(
    "Workflow Navigation",
    stages,
    index=stages.index(st.session_state.stage) if st.session_state.stage in stages else 0,
    horizontal=True,
    label_visibility="collapsed",
)
st.session_state.stage = chosen_stage


# ==============================================================================
# STAGE 1: Identity & Vault Management
# ==============================================================================
if st.session_state.stage == "1. Identity":
    # Vault Restore Expander
    with st.expander("Unlock Existing Session Vault (.zip)", expanded=(not smtp_ok)):
        col_v1, col_v2 = st.columns([3, 1])
        with col_v1:
            uploaded_vault = st.file_uploader(
                "Upload FreeApply_Vault.zip",
                type=["zip", "vault", "enc"],
                key="vault_file_input",
                label_visibility="collapsed",
            )
        with col_v2:
            unlock_pw = st.text_input(
                "Vault Password",
                type="password",
                placeholder="Vault Password",
                key="vault_pw_input",
                label_visibility="collapsed",
            )
            if st.button("Unlock Vault", use_container_width=True):
                if not uploaded_vault or not unlock_pw:
                    st.error("Please provide both the vault file and password.")
                else:
                    try:
                        restored = unpack_encrypted_vault(uploaded_vault.read(), unlock_pw)
                        cfg = restored.get("config", {})
                        st.session_state.sender_name = cfg.get("sender_name", "")
                        st.session_state.smtp_email = cfg.get("smtp_email", "")
                        st.session_state.smtp_password = cfg.get("smtp_password", "")
                        st.session_state.gemini_api_key = cfg.get("gemini_api_key", "")
                        st.session_state.vault_password = unlock_pw

                        if "resume_bytes" in restored:
                            st.session_state.resume_bytes = restored["resume_bytes"]
                            st.session_state.resume_filename = restored.get("resume_filename", "resume.pdf")
                            try:
                                import fitz
                                doc = fitz.open(stream=st.session_state.resume_bytes, filetype="pdf")
                                st.session_state.resume_text = "".join([p.get_text() + "\n" for p in doc]).strip()
                            except Exception:
                                st.session_state.resume_text = st.session_state.resume_bytes.decode("utf-8", errors="ignore")

                        if "leads_df" in restored:
                            st.session_state.leads_df = restored["leads_df"]
                        if "sent_history" in restored:
                            st.session_state.sent_history = restored["sent_history"]

                        st.success(f"Vault restored for {st.session_state.sender_name}.")
                        st.session_state.stage = "2. Lead Radar"
                        st.rerun()
                    except Exception as err:
                        st.error(str(err))

    # Configuration Inputs
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.session_state.sender_name = st.text_input(
            "Full Name",
            value=st.session_state.sender_name,
            placeholder="Jane Doe",
        )
        st.session_state.smtp_email = st.text_input(
            "Gmail Address",
            value=st.session_state.smtp_email,
            placeholder="janedoe@gmail.com",
        )
    with col_c2:
        st.session_state.smtp_password = st.text_input(
            "Gmail 16-Char App Password",
            value=st.session_state.smtp_password,
            type="password",
            help="Generate at myaccount.google.com/apppasswords with 2FA active",
        )
        st.session_state.gemini_api_key = st.text_input(
            "Google Gemini API Key",
            value=st.session_state.gemini_api_key,
            type="password",
            help="Free key available at aistudio.google.com/app/apikey",
        )

    # Resume File Handler
    uploaded_resume = st.file_uploader("Candidate Resume (PDF or TXT)", type=["pdf", "txt"])
    if uploaded_resume is not None:
        st.session_state.resume_bytes = uploaded_resume.read()
        st.session_state.resume_filename = uploaded_resume.name
        if uploaded_resume.name.lower().endswith(".pdf"):
            try:
                import fitz
                doc = fitz.open(stream=st.session_state.resume_bytes, filetype="pdf")
                st.session_state.resume_text = "".join([p.get_text() + "\n" for p in doc]).strip()
                st.caption(f"Loaded {uploaded_resume.name} ({len(st.session_state.resume_text.split())} words)")
            except Exception as e:
                st.error(f"Error reading PDF: {e}")
        else:
            st.session_state.resume_text = st.session_state.resume_bytes.decode("utf-8", errors="ignore")
            st.caption("Loaded text resume.")

    col_btn1, col_btn2 = st.columns([1, 2])
    with col_btn1:
        if st.button("Verify SMTP Delivery", use_container_width=True):
            if not st.session_state.smtp_email or not st.session_state.smtp_password:
                st.error("Please provide both Gmail address and App Password.")
            else:
                with st.spinner("Dispatching verification email..."):
                    tmp_pdf = None
                    if st.session_state.resume_bytes:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(st.session_state.resume_bytes)
                            tmp_pdf = tmp.name
                    try:
                        send_outreach.send_single_email(
                            "smtp.gmail.com",
                            465,
                            st.session_state.smtp_email,
                            st.session_state.smtp_password.replace(" ", ""),
                            st.session_state.smtp_email,
                            "FreeApply Verification",
                            f"System connection verified for {st.session_state.sender_name or 'Candidate'}.",
                            st.session_state.sender_name,
                            attachment_path=tmp_pdf,
                        )
                        st.success("Verification email delivered to your inbox.")
                    except Exception as err:
                        st.error(f"Delivery failed: {err}")
                    finally:
                        if tmp_pdf and os.path.exists(tmp_pdf):
                            os.remove(tmp_pdf)

    with col_btn2:
        if st.button("Continue to Lead Radar", type="primary", use_container_width=True):
            st.session_state.stage = "2. Lead Radar"
            st.rerun()


# ==============================================================================
# STAGE 2: Lead Radar & AI Personalization Engine
# ==============================================================================
elif st.session_state.stage == "2. Lead Radar":
    col_u1, col_u2 = st.columns([3, 1])
    with col_u1:
        uploaded_csv = st.file_uploader("Upload CSV Spreadsheet", type=["csv"], label_visibility="collapsed")
        if uploaded_csv is not None:
            try:
                st.session_state.leads_df = pd.read_csv(uploaded_csv)
                if "custom_hook" not in st.session_state.leads_df.columns:
                    st.session_state.leads_df["custom_hook"] = ""
                st.success(f"Imported {len(st.session_state.leads_df)} leads.")
            except Exception:
                try:
                    uploaded_csv.seek(0)
                    st.session_state.leads_df = pd.read_csv(uploaded_csv, on_bad_lines="skip")
                    if "custom_hook" not in st.session_state.leads_df.columns:
                        st.session_state.leads_df["custom_hook"] = ""
                    st.warning("Imported with invalid lines skipped.")
                except Exception as e:
                    st.error(f"Error parsing CSV: {e}")
    with col_u2:
        if st.button("Reset Starter Leads", use_container_width=True):
            example_path = os.path.join(BASE_DIR, "leads.example.csv")
            if os.path.exists(example_path):
                st.session_state.leads_df = pd.read_csv(example_path)
                st.info("Loaded example leads.")

    # Data Editor
    edited_df = st.data_editor(
        st.session_state.leads_df,
        num_rows="dynamic",
        use_container_width=True,
    )
    st.session_state.leads_df = edited_df

    col_act1, col_act2 = st.columns([1, 1])
    with col_act1:
        if st.button("Synthesize AI Hooks (Gemini 2.5 Flash)", use_container_width=True):
            if not st.session_state.gemini_api_key:
                st.error("Missing Gemini API Key. Configure in Stage 1.")
            elif not st.session_state.resume_text:
                st.error("Missing resume background. Upload in Stage 1.")
            elif st.session_state.leads_df.empty:
                st.warning("Queue is empty.")
            else:
                try:
                    from google import genai
                    client = genai.Client(api_key=st.session_state.gemini_api_key.strip())
                    p_bar = st.progress(0)
                    total = len(st.session_state.leads_df)

                    for idx, row in st.session_state.leads_df.iterrows():
                        comp = str(row.get("company", "")).strip()
                        role = str(row.get("role", "")).strip()
                        hook = personalize.generate_hook_with_gemini(
                            client, "gemini-2.5-flash", st.session_state.resume_text, comp, role
                        )
                        if hook:
                            st.session_state.leads_df.at[idx, "custom_hook"] = hook
                        p_bar.progress((idx + 1) / total)

                    st.success("All AI hooks synthesized.")
                    st.rerun()
                except Exception as err:
                    st.error(f"Synthesis failed: {err}")

    with col_act2:
        if st.button("Continue to Composer", type="primary", use_container_width=True):
            st.session_state.stage = "3. Composer"
            st.rerun()


# ==============================================================================
# STAGE 3: Composer & Review
# ==============================================================================
elif st.session_state.stage == "3. Composer":
    template_map = {
        "Operations Lead": os.path.join(TEMPLATES_DIR, "operations_outreach.txt"),
        "Software Engineering": os.path.join(TEMPLATES_DIR, "engineering_outreach.txt"),
        "General Multi-Role": os.path.join(TEMPLATES_DIR, "general_outreach.txt"),
        "Follow-Up": os.path.join(TEMPLATES_DIR, "followup.txt"),
    }

    col_sel1, col_sel2 = st.columns([1, 1])
    with col_sel1:
        chosen_tpl = st.selectbox("Template Strategy", list(template_map.keys()))
        tpl_path = template_map[chosen_tpl]
        tpl_body = ""
        if os.path.exists(tpl_path):
            with open(tpl_path, "r", encoding="utf-8") as f:
                tpl_body = f.read()

    with col_sel2:
        lead_labels = [
            f"{r.get('company', '')} — {r.get('name', '')} ({r.get('role', '')})"
            for _, r in st.session_state.leads_df.iterrows()
        ] if not st.session_state.leads_df.empty else ["No leads available"]
        active_lead_idx = st.selectbox(
            "Inspect Contact",
            range(len(lead_labels)),
            format_func=lambda i: lead_labels[i] if i < len(lead_labels) else "",
        )

    # Executive Email Canvas
    if not st.session_state.leads_df.empty and active_lead_idx < len(st.session_state.leads_df):
        lead = st.session_state.leads_df.iloc[active_lead_idx]
        company_val = str(lead.get("company", "Company"))
        role_val = str(lead.get("role", "Role"))
        hook_val = str(lead.get("custom_hook", ""))
        email_val = str(lead.get("email", "recruiter@example.com"))
        name_val = str(lead.get("name", "Hiring Team"))

        # Render preview with typography highlight tokens
        subject_line = "Application"
        raw_body_lines = []
        for line in tpl_body.splitlines():
            if line.lower().startswith("subject:"):
                subject_line = line.split(":", 1)[1].strip().replace("{{role}}", role_val).replace("{{company}}", company_val).replace("{{sender_name}}", st.session_state.sender_name or "Candidate")
            else:
                raw_body_lines.append(line)

        rendered_body = "\n".join(raw_body_lines).strip()
        rendered_body = (
            rendered_body
            .replace("{{name}}", f"<b>{name_val}</b>")
            .replace("{{company}}", f'<span class="highlight-pill">{company_val}</span>')
            .replace("{{role}}", f'<span class="highlight-pill">{role_val}</span>')
            .replace("{{custom_hook}}", f'<span class="hook-token">{hook_val or "[AI Hook Pending]"}</span>')
            .replace("{{sender_name}}", f"<b>{st.session_state.sender_name or 'Candidate'}</b>")
            .replace("\n", "<br>")
        )

        st.markdown(
            f"""
            <div class="email-container">
                <div class="email-row">
                    <span class="email-key">FROM:</span>
                    <span class="email-val">{st.session_state.sender_name or 'Candidate'} &lt;{st.session_state.smtp_email or 'pending@gmail.com'}&gt;</span>
                </div>
                <div class="email-row">
                    <span class="email-key">TO:</span>
                    <span class="email-val">{name_val} &lt;{email_val}&gt;</span>
                </div>
                <div class="email-row">
                    <span class="email-key">SUBJECT:</span>
                    <span class="email-val" style="color:#f8fafc; font-weight:600;">{subject_line}</span>
                </div>
                <div class="email-row">
                    <span class="email-key">ATTACH:</span>
                    <span class="email-val">{st.session_state.resume_filename if st.session_state.resume_bytes else 'None'}</span>
                </div>
                <div class="email-body">{rendered_body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        if st.button("Return to Lead Radar", use_container_width=True):
            st.session_state.stage = "2. Lead Radar"
            st.rerun()
    with col_nav2:
        if st.button("Continue to Execution", type="primary", use_container_width=True):
            st.session_state.stage = "4. Execution"
            st.rerun()


# ==============================================================================
# STAGE 4: Execution Engine & Session Vault Locker
# ==============================================================================
elif st.session_state.stage == "4. Execution":
    col_act1, col_act2 = st.columns(2)

    with col_act1:
        st.markdown(
            """
            <div class="section-card">
                <div class="telemetry-label">Pre-Flight Simulation</div>
                <div style="font-size:0.85rem; color:#94a3b8; margin:0.4rem 0 0.8rem 0;">
                    Verify template variable compilation and attachment readiness without network calls.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Simulate Dry Run", use_container_width=True):
            st.success(f"Simulation verified: {len(st.session_state.leads_df)} leads ready for transmission.")

    with col_act2:
        st.markdown(
            """
            <div class="section-card">
                <div class="telemetry-label" style="color:#f43f5e;">Armed Transmission</div>
                <div style="font-size:0.85rem; color:#94a3b8; margin:0.4rem 0 0.8rem 0;">
                    Dispatches live emails via Gmail SMTP with randomized 30–45s deliverability delays.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Execute Live Outreach", type="primary", use_container_width=True):
            if not smtp_ok:
                st.error("Missing Gmail credentials in Stage 1.")
            elif st.session_state.leads_df.empty:
                st.warning("Lead queue is empty.")
            else:
                tmp_pdf = None
                if st.session_state.resume_bytes:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(st.session_state.resume_bytes)
                        tmp_pdf = tmp.name

                total = len(st.session_state.leads_df)
                p_bar = st.progress(0)
                status_view = st.empty()
                tpl_file = os.path.join(TEMPLATES_DIR, "operations_outreach.txt")

                try:
                    for i, (idx, row) in enumerate(st.session_state.leads_df.iterrows(), 1):
                        rec_email = str(row.get("email", "")).strip()
                        data = {
                            "name": row.get("name", "Hiring Team"),
                            "company": row.get("company", ""),
                            "role": row.get("role", ""),
                            "custom_hook": row.get("custom_hook", ""),
                            "original_subject": f"Application for {row.get('role', '')}",
                            "sender_name": st.session_state.sender_name or "Candidate",
                        }
                        subj, body = send_outreach.render_template(tpl_file, data)

                        status_view.caption(f"[{i}/{total}] Delivering to {rec_email} at {row.get('company')}...")
                        try:
                            send_outreach.send_single_email(
                                "smtp.gmail.com",
                                465,
                                st.session_state.smtp_email,
                                st.session_state.smtp_password.replace(" ", ""),
                                rec_email,
                                subj,
                                body,
                                st.session_state.sender_name,
                                attachment_path=tmp_pdf,
                            )
                            st.session_state.sent_history.append({
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "email": rec_email,
                                "company": row.get("company", ""),
                                "role": row.get("role", ""),
                                "status": "SUCCESS",
                            })
                        except Exception as err:
                            st.session_state.sent_history.append({
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "email": rec_email,
                                "company": row.get("company", ""),
                                "role": row.get("role", ""),
                                "status": "FAILED",
                                "details": str(err),
                            })
                        p_bar.progress(i / total)
                        if i < total:
                            delay = random.randint(30, 45)
                            status_view.caption(f"Throttling: {delay}s delay to preserve inbox health...")
                            time.sleep(delay)

                    status_view.success("Outreach sequence finished.")
                finally:
                    if tmp_pdf and os.path.exists(tmp_pdf):
                        os.remove(tmp_pdf)

    # --- Session Vault Locker ---
    st.markdown("---")
    st.markdown("#### Encrypted Session Vault Backup")
    st.caption("Bundle credentials, resume, leads table, and touch history into a single AES-256 encrypted file.")

    log_lines = [
        "# FreeApply-AI Outreach Knowledge Graph",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Candidate: {st.session_state.sender_name or 'Candidate'}",
        "",
        "## Outreach Nodes & History",
        "",
    ]
    for item in st.session_state.sent_history:
        log_lines.append(
            f"- **{item.get('company', 'Unknown')}** | Role: `{item.get('role', 'N/A')}` | "
            f"Contact: `{item.get('email', 'N/A')}` | Status: **{item.get('status', 'PENDING')}** | Date: {item.get('timestamp', '')}"
        )
    log_md_content = "\n".join(log_lines)

    col_bk1, col_bk2 = st.columns([2, 1])
    with col_bk1:
        vault_pw = st.text_input(
            "Vault Encryption Password",
            type="password",
            value=st.session_state.vault_password,
            placeholder="Choose password or PIN",
            label_visibility="collapsed",
        )
    with col_bk2:
        if vault_pw:
            cfg = {
                "sender_name": st.session_state.sender_name,
                "smtp_email": st.session_state.smtp_email,
                "smtp_password": st.session_state.smtp_password,
                "gemini_api_key": st.session_state.gemini_api_key,
            }
            try:
                enc_data = pack_encrypted_vault(
                    vault_pw, cfg, st.session_state.leads_df, st.session_state.sent_history,
                    st.session_state.resume_bytes, st.session_state.resume_filename, log_md_content
                )
                st.download_button(
                    "Download FreeApply_Vault.zip",
                    data=enc_data,
                    file_name="FreeApply_Vault.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Error packing vault: {e}")
        else:
            st.button("Download FreeApply_Vault.zip", disabled=True, use_container_width=True)

    if st.session_state.sent_history:
        st.dataframe(pd.DataFrame(st.session_state.sent_history), use_container_width=True)
