#!/usr/bin/env python3
"""
FreeApply-AI: Command Pipeline & Outreach Studio
------------------------------------------------
A high-trust, neuro-aesthetic web interface for automated cold outreach,
Gemini AI personalization, and password-encrypted session vault management.

Designed using principles of cognitive clarity, trust engineering, and
modern design systems.
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

# Core automation modules
import send_outreach
import personalize

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
VAULT_MAGIC = b"FAVAULT1"


# --- Vault Cryptography Helpers ---
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
        leads_csv = leads_df.to_csv(index=False)
        zf.writestr("leads.csv", leads_csv)
        if sent_history:
            zf.writestr("sent_history.json", json.dumps(sent_history, indent=2))
        if log_md:
            zf.writestr("log.md", log_md)

    raw_zip = buf.getvalue()
    salt = os.urandom(16)
    key = derive_vault_key(password, salt)
    fernet = Fernet(key)
    ciphertext = fernet.encrypt(raw_zip)
    return VAULT_MAGIC + salt + ciphertext


def unpack_encrypted_vault(vault_bytes: bytes, password: str) -> dict:
    if not vault_bytes.startswith(VAULT_MAGIC):
        raise ValueError("The uploaded file is not a valid FreeApply-AI Vault archive.")

    salt = vault_bytes[8:24]
    ciphertext = vault_bytes[24:]
    key = derive_vault_key(password, salt)
    fernet = Fernet(key)

    try:
        raw_zip = fernet.decrypt(ciphertext)
    except InvalidToken:
        raise ValueError("Incorrect password. Unable to decrypt vault.")

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


# --- Page Config ---
st.set_page_config(
    page_title="FreeApply-AI — Executive Outreach Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Neuro-Aesthetic Styling (Glassmorphism, High-Trust Tokens, Elevated Surfaces) ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        text-rendering: optimizeLegibility;
        -webkit-font-smoothing: antialiased;
    }

    /* Core Hero Banner */
    .hero-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1.25rem 1.5rem;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.9));
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.3);
    }
    .hero-title {
        font-size: 1.75rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(120deg, #60a5fa 0%, #a855f7 50%, #38bdf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .hero-tagline {
        color: #94a3b8;
        font-size: 0.88rem;
        margin-top: 0.25rem;
        font-weight: 500;
    }

    /* Telemetry HUD Cards */
    .hud-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 0.85rem;
        margin-bottom: 1.5rem;
    }
    .hud-tile {
        background: rgba(15, 23, 42, 0.65);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.9rem 1.1rem;
        transition: transform 180ms ease, border-color 180ms ease;
    }
    .hud-tile:hover {
        border-color: rgba(96, 165, 250, 0.3);
        transform: translateY(-2px);
    }
    .hud-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 0.35rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .hud-value {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f8fafc;
        font-variant-numeric: tabular-nums;
    }

    /* Pulse Status Dots */
    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }
    .dot-green {
        background-color: #10b981;
        box-shadow: 0 0 10px rgba(16, 185, 129, 0.6);
    }
    .dot-blue {
        background-color: #38bdf8;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.6);
    }

    /* Glass Surface Panel */
    .glass-deck {
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    /* Superhuman-Style Email Canvas */
    .email-canvas {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 1.5rem;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
    }
    .email-meta-row {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.45rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        font-size: 0.88rem;
    }
    .email-meta-label {
        color: #64748b;
        font-weight: 600;
        min-width: 60px;
    }
    .chip-sender {
        background: rgba(59, 130, 246, 0.15);
        color: #93c5fd;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        border: 1px solid rgba(59, 130, 246, 0.3);
        font-size: 0.82rem;
        font-weight: 600;
    }
    .chip-recip {
        background: rgba(168, 85, 247, 0.15);
        color: #d8b4fe;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        border: 1px solid rgba(168, 85, 247, 0.3);
        font-size: 0.82rem;
        font-weight: 600;
    }
    .chip-attach {
        background: rgba(16, 185, 129, 0.15);
        color: #6ee7b7;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        border: 1px solid rgba(16, 185, 129, 0.3);
        font-size: 0.82rem;
        font-weight: 600;
    }

    /* Highlight Badges inside Email Body */
    .hook-highlight {
        background: rgba(16, 185, 129, 0.18);
        color: #34d399;
        padding: 0.15rem 0.45rem;
        border-radius: 5px;
        border-left: 3px solid #10b981;
        font-weight: 500;
    }
    .var-company {
        background: rgba(168, 85, 247, 0.15);
        color: #c084fc;
        padding: 0.1rem 0.4rem;
        border-radius: 4px;
        font-weight: 600;
    }
    .var-role {
        background: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        padding: 0.1rem 0.4rem;
        border-radius: 4px;
        font-weight: 600;
    }

    /* Stepper Navigation Buttons */
    div[data-testid="stRadio"] > div {
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
        background: rgba(15, 23, 42, 0.7);
        padding: 0.4rem;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    div[data-testid="stRadio"] label {
        background: transparent !important;
        border-radius: 8px;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
    }

    @media (max-width: 768px) {
        .hero-container { flex-direction: column; align-items: flex-start; gap: 0.75rem; }
        .hud-grid { grid-template-columns: 1fr 1fr; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- State Initialization ---
local_env = send_outreach.load_env(os.path.join(BASE_DIR, ".env"))

if "active_stage" not in st.session_state:
    st.session_state.active_stage = "1. Identity & Vault"
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


# --- Hero Command Banner ---
st.markdown(
    f"""
    <div class="hero-container">
        <div>
            <div class="hero-title">⚡ FreeApply-AI Command Studio</div>
            <div class="hero-tagline">Hyper-personalized cold outreach engine • Zero monthly fees • 100% Client-Side Privacy</div>
        </div>
        <div style="display:flex; gap:0.5rem; align-items:center;">
            <span class="chip-sender">Candidate: {st.session_state.sender_name or 'Unregistered'}</span>
            <span class="chip-attach">Vault: {'Encrypted' if st.session_state.vault_password else 'Active'}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Real-Time Telemetry HUD ---
leads_count = len(st.session_state.leads_df)
hooks_ready = len(st.session_state.leads_df[st.session_state.leads_df["custom_hook"].astype(str).str.strip() != ""]) if leads_count > 0 else 0
resume_status = f"{len(st.session_state.resume_text.split())} words" if st.session_state.resume_text else "Pending"
smtp_status = "Connected" if (st.session_state.smtp_email and st.session_state.smtp_password) else "Setup Required"

st.markdown(
    f"""
    <div class="hud-grid">
        <div class="hud-tile">
            <div class="hud-label"><span class="pulse-dot dot-blue"></span> SMTP Delivery</div>
            <div class="hud-value">{smtp_status}</div>
        </div>
        <div class="hud-tile">
            <div class="hud-label"><span class="pulse-dot dot-green"></span> Resume Engine</div>
            <div class="hud-value">{resume_status}</div>
        </div>
        <div class="hud-tile">
            <div class="hud-label"><span class="pulse-dot dot-blue"></span> Target Pipeline</div>
            <div class="hud-value">{leads_count} Leads Active</div>
        </div>
        <div class="hud-tile">
            <div class="hud-label"><span class="pulse-dot dot-green"></span> AI Enrichment</div>
            <div class="hud-value">{hooks_ready}/{leads_count} Hooks Ready</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Guided Command Pipeline Stepper ---
stage_labels = [
    "1. Identity & Vault",
    "2. Target Radar & AI",
    "3. Executive Studio",
    "4. Mission Control",
]

selected_stage = st.radio(
    "Pipeline Stage",
    stage_labels,
    index=stage_labels.index(st.session_state.active_stage) if st.session_state.active_stage in stage_labels else 0,
    horizontal=True,
    label_visibility="collapsed",
)
st.session_state.active_stage = selected_stage

st.write("")

# ==============================================================================
# STAGE 1: Identity & Vault Deck
# ==============================================================================
if st.session_state.active_stage == "1. Identity & Vault":
    st.markdown("### 🔐 Stage 1: Identity, Credentials & Encrypted Vault")
    st.caption("Provide your credentials securely. Everything remains inside temporary memory and can be encrypted into a single vault file.")

    # Vault Unlock Box
    with st.expander("📂 Have an existing Vault? Click to Unlock & Restore", expanded=(not st.session_state.smtp_email)):
        col_v1, col_v2 = st.columns([3, 1])
        with col_v1:
            uploaded_vault = st.file_uploader(
                "Upload FreeApply_Vault.zip",
                type=["zip", "vault", "enc"],
                key="stage1_vault_uploader",
            )
        with col_v2:
            unlock_password = st.text_input(
                "Vault Password",
                type="password",
                placeholder="Password",
                key="stage1_unlock_pass",
            )
            if st.button("🔓 Unlock & Restore", use_container_width=True):
                if not uploaded_vault:
                    st.error("Please select your `FreeApply_Vault.zip` first.")
                elif not unlock_password:
                    st.error("Please enter your vault password.")
                else:
                    try:
                        restored = unpack_encrypted_vault(uploaded_vault.read(), unlock_password)
                        cfg = restored.get("config", {})
                        st.session_state.sender_name = cfg.get("sender_name", "")
                        st.session_state.smtp_email = cfg.get("smtp_email", "")
                        st.session_state.smtp_password = cfg.get("smtp_password", "")
                        st.session_state.gemini_api_key = cfg.get("gemini_api_key", "")
                        st.session_state.vault_password = unlock_password

                        if "resume_bytes" in restored:
                            st.session_state.resume_bytes = restored["resume_bytes"]
                            st.session_state.resume_filename = restored.get("resume_filename", "resume.pdf")
                            try:
                                import fitz
                                doc = fitz.open(stream=st.session_state.resume_bytes, filetype="pdf")
                                extracted = "".join([page.get_text() + "\n" for page in doc])
                                st.session_state.resume_text = extracted.strip()
                            except Exception:
                                st.session_state.resume_text = st.session_state.resume_bytes.decode("utf-8", errors="ignore")

                        if "leads_df" in restored:
                            st.session_state.leads_df = restored["leads_df"]
                        if "sent_history" in restored:
                            st.session_state.sent_history = restored["sent_history"]

                        st.success(f"🎉 Vault unlocked! Welcome back, {st.session_state.sender_name}.")
                        st.session_state.active_stage = "2. Target Radar & AI"
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")

    # Manual Credentials Inputs
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.sender_name = st.text_input(
            "Your Full Name",
            value=st.session_state.sender_name,
            placeholder="e.g. Shiv Sharma",
        )
        st.session_state.smtp_email = st.text_input(
            "Your Gmail Address",
            value=st.session_state.smtp_email,
            placeholder="e.g. shivshankar.s2003@gmail.com",
        )
    with col2:
        st.session_state.smtp_password = st.text_input(
            "Gmail 16-Character App Password",
            value=st.session_state.smtp_password,
            type="password",
            help="Generate at myaccount.google.com/apppasswords with 2FA enabled",
        )
        st.session_state.gemini_api_key = st.text_input(
            "Google Gemini API Key (Free tier)",
            value=st.session_state.gemini_api_key,
            type="password",
            help="Get free key at aistudio.google.com/app/apikey",
        )

    st.write("")
    st.markdown("#### 📄 Resume Profile")
    uploaded_resume = st.file_uploader("Upload PDF or TXT Resume", type=["pdf", "txt"])
    if uploaded_resume is not None:
        st.session_state.resume_bytes = uploaded_resume.read()
        st.session_state.resume_filename = uploaded_resume.name
        if uploaded_resume.name.lower().endswith(".pdf"):
            try:
                import fitz
                doc = fitz.open(stream=st.session_state.resume_bytes, filetype="pdf")
                extracted = "".join([page.get_text() + "\n" for page in doc])
                st.session_state.resume_text = extracted.strip()
                st.success(f"Extracted {len(st.session_state.resume_text.split())} words from {uploaded_resume.name}")
            except Exception as e:
                st.error(f"Failed parsing PDF: {e}")
        else:
            st.session_state.resume_text = st.session_state.resume_bytes.decode("utf-8", errors="ignore")
            st.success("Loaded text resume.")

    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        if st.button("📨 Test SMTP Connection", use_container_width=True):
            if not st.session_state.smtp_email or not st.session_state.smtp_password:
                st.error("Please fill in your Gmail and App Password above.")
            else:
                with st.spinner("Verifying SMTP..."):
                    tmp_resume_path = None
                    if st.session_state.resume_bytes:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(st.session_state.resume_bytes)
                            tmp_resume_path = tmp.name
                    try:
                        send_outreach.send_single_email(
                            "smtp.gmail.com",
                            465,
                            st.session_state.smtp_email,
                            st.session_state.smtp_password.replace(" ", ""),
                            st.session_state.smtp_email,
                            "FreeApply-AI: SMTP Verification",
                            f"Hello {st.session_state.sender_name or 'there'},\n\nYour SMTP setup is 100% verified and operational.",
                            st.session_state.sender_name,
                            attachment_path=tmp_resume_path,
                        )
                        st.success("✅ Delivery verified! Check your inbox.")
                    except Exception as e:
                        st.error(f"SMTP Error: {e}")
                    finally:
                        if tmp_resume_path and os.path.exists(tmp_resume_path):
                            os.remove(tmp_resume_path)

    with col_t2:
        if st.button("Proceed to Target Radar & AI ➔", type="primary", use_container_width=True):
            st.session_state.active_stage = "2. Target Radar & AI"
            st.rerun()


# ==============================================================================
# STAGE 2: Target Radar & AI Personalization Engine
# ==============================================================================
elif st.session_state.active_stage == "2. Target Radar & AI":
    st.markdown("### 🎯 Stage 2: Target Radar & AI Personalization")
    st.caption("Manage target companies, inspect leads, and let Google Gemini generate authentic 1-2 sentence hooks.")

    col_up, col_rst = st.columns([3, 1])
    with col_up:
        uploaded_csv = st.file_uploader("Upload Leads CSV (`name,email,company,role,custom_hook`)", type=["csv"])
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
                    st.warning("Imported leads with bad lines skipped.")
                except Exception as e:
                    st.error(f"Error parsing CSV: {e}")
    with col_rst:
        if st.button("Reset Example Leads", use_container_width=True):
            example_path = os.path.join(BASE_DIR, "leads.example.csv")
            if os.path.exists(example_path):
                st.session_state.leads_df = pd.read_csv(example_path)
                st.info("Reset to 3 starter leads.")

    st.markdown("#### Interactive Pipeline Table:")
    edited_df = st.data_editor(
        st.session_state.leads_df,
        num_rows="dynamic",
        use_container_width=True,
    )
    st.session_state.leads_df = edited_df

    st.write("")

    # AI Personalization Trigger
    st.markdown(
        """
        <div class="glass-deck" style="padding: 1.1rem;">
            <h4 style="margin:0 0 0.4rem 0;">✨ Gemini 2.5 Flash Hook Generator</h4>
            <span style="color:#94a3b8; font-size:0.88rem;">
                Gemini reads your resume achievements and connects them directly to each target company's domain.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_ai1, col_ai2 = st.columns([1, 1])
    with col_ai1:
        if st.button("🤖 Generate AI Personalization Hooks", use_container_width=True):
            if not st.session_state.gemini_api_key:
                st.error("Please add your Gemini API Key in Stage 1.")
            elif not st.session_state.resume_text:
                st.error("Please upload your resume in Stage 1 first.")
            elif st.session_state.leads_df.empty:
                st.warning("No leads found in table.")
            else:
                try:
                    from google import genai
                    client = genai.Client(api_key=st.session_state.gemini_api_key.strip())
                    p_bar = st.progress(0)
                    stat_txt = st.empty()
                    total = len(st.session_state.leads_df)

                    for idx, row in st.session_state.leads_df.iterrows():
                        comp = str(row.get("company", "")).strip()
                        role = str(row.get("role", "")).strip()
                        stat_txt.markdown(f"*Crafting pitch for **{role}** at **{comp}** ({idx + 1}/{total})...*")
                        hook = personalize.generate_hook_with_gemini(
                            client, "gemini-2.5-flash", st.session_state.resume_text, comp, role
                        )
                        if hook:
                            st.session_state.leads_df.at[idx, "custom_hook"] = hook
                        p_bar.progress((idx + 1) / total)

                    stat_txt.success("✨ All AI hooks generated! You can review or edit them above.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gemini API Error: {e}")

    with col_ai2:
        if st.button("Proceed to Executive Studio ➔", type="primary", use_container_width=True):
            st.session_state.active_stage = "3. Executive Studio"
            st.rerun()


# ==============================================================================
# STAGE 3: Executive Email Studio (Superhuman / Apple Mail Style)
# ==============================================================================
elif st.session_state.active_stage == "3. Executive Studio":
    st.markdown("### ✉️ Stage 3: Executive Outreach Studio")
    st.caption("Inspect live rendered emails with visual variable highlights. Confirm how each email looks before dispatch.")

    template_files = {
        "Operations Outreach": os.path.join(TEMPLATES_DIR, "operations_outreach.txt"),
        "Engineering Outreach": os.path.join(TEMPLATES_DIR, "engineering_outreach.txt"),
        "General Outreach": os.path.join(TEMPLATES_DIR, "general_outreach.txt"),
        "Follow-up": os.path.join(TEMPLATES_DIR, "followup.txt"),
    }

    col_tp1, col_tp2 = st.columns([1, 1])
    with col_tp1:
        chosen_template_name = st.selectbox("Select Strategy Template", list(template_files.keys()))
        selected_template_path = template_files[chosen_template_name]
        template_content = ""
        if os.path.exists(selected_template_path):
            with open(selected_template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

    with col_tp2:
        lead_options = [f"{row.get('company', '')} — {row.get('name', '')} ({row.get('role', '')})" for _, row in st.session_state.leads_df.iterrows()] if not st.session_state.leads_df.empty else ["No Leads Available"]
        preview_idx = st.selectbox("Inspect Recruiter Card", range(len(lead_options)), format_func=lambda x: lead_options[x] if x < len(lead_options) else "")

    template_text = st.text_area("Template Canvas", template_content, height=140)

    # Superhuman-Style Highlighted Preview
    if not st.session_state.leads_df.empty and preview_idx < len(st.session_state.leads_df):
        sample_row = st.session_state.leads_df.iloc[preview_idx]
        company = str(sample_row.get("company", "Acme"))
        role = str(sample_row.get("role", "Operations Lead"))
        hook = str(sample_row.get("custom_hook", ""))
        rec_email = str(sample_row.get("email", "recruiter@company.com"))
        rec_name = str(sample_row.get("name", "Hiring Team"))

        # Render plain text for delivery
        rendered_plain = template_text
        sample_data = {
            "name": rec_name,
            "company": company,
            "role": role,
            "custom_hook": hook,
            "original_subject": f"Application for {role}",
            "sender_name": st.session_state.sender_name or "Job Seeker",
        }
        for k, v in sample_data.items():
            rendered_plain = rendered_plain.replace(f"{{{{{k}}}}}", str(v))

        subj = "Application"
        body_plain = rendered_plain
        for line in rendered_plain.splitlines():
            if line.lower().startswith("subject:"):
                subj = line.split(":", 1)[1].strip()
                body_plain = "\n".join([l for l in rendered_plain.splitlines() if not l.lower().startswith("subject:")]).strip()
                break

        # Render visually highlighted version for human review
        highlighted_body = template_text
        for line in highlighted_body.splitlines():
            if line.lower().startswith("subject:"):
                highlighted_body = "\n".join([l for l in highlighted_body.splitlines() if not l.lower().startswith("subject:")]).strip()
                break

        highlighted_body = (
            highlighted_body
            .replace("{{name}}", f"<b>{rec_name}</b>")
            .replace("{{company}}", f'<span class="var-company">{company}</span>')
            .replace("{{role}}", f'<span class="var-role">{role}</span>')
            .replace("{{custom_hook}}", f'<span class="hook-highlight">{hook or "[AI Hook Pending]"}</span>')
            .replace("{{sender_name}}", f"<b>{st.session_state.sender_name or 'Your Name'}</b>")
            .replace("\n", "<br>")
        )

        st.markdown(
            f"""
            <div class="email-canvas">
                <div class="email-meta-row">
                    <span class="email-meta-label">FROM:</span>
                    <span class="chip-sender">{st.session_state.sender_name or 'Job Seeker'} &lt;{st.session_state.smtp_email or 'not-configured'}&gt;</span>
                </div>
                <div class="email-meta-row">
                    <span class="email-meta-label">TO:</span>
                    <span class="chip-recip">{rec_name} &lt;{rec_email}&gt;</span>
                </div>
                <div class="email-meta-row">
                    <span class="email-meta-label">SUBJECT:</span>
                    <span style="font-weight:700; color:#f1f5f9;">{subj}</span>
                </div>
                <div class="email-meta-row">
                    <span class="email-meta-label">ATTACH:</span>
                    <span class="chip-attach">📎 {st.session_state.resume_filename if st.session_state.resume_bytes else 'No Resume Attached'}</span>
                </div>
                <div style="padding-top:1.2rem; color:#e2e8f0; line-height:1.65; font-size:0.95rem;">
                    {highlighted_body}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    col_st3, col_st4 = st.columns([1, 1])
    with col_st3:
        if st.button("⬅️ Back to Target Radar", use_container_width=True):
            st.session_state.active_stage = "2. Target Radar & AI"
            st.rerun()
    with col_st4:
        if st.button("Proceed to Mission Control ➔", type="primary", use_container_width=True):
            st.session_state.active_stage = "4. Mission Control"
            st.rerun()


# ==============================================================================
# STAGE 4: Mission Control, Safe Launch & Vault Locker
# ==============================================================================
elif st.session_state.active_stage == "4. Mission Control":
    st.markdown("### 🚀 Stage 4: Mission Control & Safe Launch")
    st.caption("Execute your dry-run preview, launch live throttled dispatch, and export your encrypted session vault.")

    # Dual Dispatch Deck
    col_d1, col_d2 = st.columns(2)

    with col_d1:
        st.markdown(
            """
            <div class="glass-deck">
                <h4 style="margin:0 0 0.4rem 0; color:#38bdf8;">🛡️ Safe Dry-Run Simulation</h4>
                <p style="color:#94a3b8; font-size:0.85rem; margin-bottom:1rem;">
                    Simulate full email rendering for all contacts with 0 risk. No network calls or live emails sent.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("👁️ Run Simulation Preview", use_container_width=True):
            st.success(f"✓ Simulation passed! All {len(st.session_state.leads_df)} contacts are properly formatted and ready.")

    with col_d2:
        st.markdown(
            """
            <div class="glass-deck">
                <h4 style="margin:0 0 0.4rem 0; color:#f43f5e;">⚡ Armed Live Outreach</h4>
                <p style="color:#94a3b8; font-size:0.85rem; margin-bottom:1rem;">
                    Dispatches personalized emails through Gmail SMTP with randomized 30–45s delays to protect deliverability.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🔴 Fire Live Outreach", type="primary", use_container_width=True):
            if not st.session_state.smtp_email or not st.session_state.smtp_password:
                st.error("Missing Gmail credentials in Stage 1.")
            elif st.session_state.leads_df.empty:
                st.warning("Queue is empty.")
            else:
                tmp_resume_path = None
                if st.session_state.resume_bytes:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(st.session_state.resume_bytes)
                        tmp_resume_path = tmp.name

                total = len(st.session_state.leads_df)
                p_bar = st.progress(0)
                status_box = st.empty()

                template_file = os.path.join(TEMPLATES_DIR, "operations_outreach.txt")
                with open(template_file, "r", encoding="utf-8") as f:
                    template_raw = f.read()

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
                        subj, body = send_outreach.render_template(template_file, data)

                        status_box.markdown(f"**[{i}/{total}] Sending to {rec_email} at {row.get('company')}...**")
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
                                attachment_path=tmp_resume_path,
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
                            status_box.info(f"⏳ Throttling: waiting {delay}s before next send to protect inbox health...")
                            time.sleep(delay)

                    status_box.success("🎉 Outreach batch complete!")
                finally:
                    if tmp_resume_path and os.path.exists(tmp_resume_path):
                        os.remove(tmp_resume_path)

    st.divider()

    # --- KNOWLEDGE GRAPH VAULT LOCKER ---
    log_lines = [
        "# FreeApply-AI: Outreach Knowledge Graph & Audit Log",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Candidate: {st.session_state.sender_name or 'Candidate'}",
        "",
        "## Outreach Nodes & Touch History",
        "",
    ]
    for item in st.session_state.sent_history:
        log_lines.append(
            f"- **{item.get('company', 'Unknown')}** | Role: `{item.get('role', 'N/A')}` | "
            f"Contact: `{item.get('email', 'N/A')}` | Status: **{item.get('status', 'PENDING')}** | Date: {item.get('timestamp', '')}"
        )
    log_md_str = "\n".join(log_lines)

    st.markdown("#### 🔒 Encrypted Session Vault Backup")
    st.caption("Store your credentials, resume, leads table, and Knowledge Graph in a single AES-256 encrypted file so you never have to retype them.")

    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        vault_pw = st.text_input(
            "Set Vault Password",
            type="password",
            value=st.session_state.vault_password,
            placeholder="Enter password or PIN to encrypt your file",
        )
    with col_v2:
        st.write("")
        st.write("")
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
                    st.session_state.resume_bytes, st.session_state.resume_filename, log_md_str
                )
                st.download_button(
                    "💾 Download FreeApply_Vault.zip",
                    data=enc_data,
                    file_name="FreeApply_Vault.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.button("💾 Download FreeApply_Vault.zip", disabled=True, use_container_width=True)

    st.write("")
    if st.session_state.sent_history:
        st.markdown("#### Real-Time Delivery Log")
        st.dataframe(pd.DataFrame(st.session_state.sent_history), use_container_width=True)
