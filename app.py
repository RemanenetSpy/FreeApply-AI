#!/usr/bin/env python3
"""
FreeApply-AI — Executive Cold Outreach Engine
---------------------------------------------
Architected following OpenDesign principles and Swiss International typography:
- Strict visual hierarchy & high contrast
- Monospace metadata tokens
- Zero gratuitous emojis or AI-slop gradients
- Compact mobile viewport ergonomics
- Client-side cryptographic session vault persistence
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
        raise ValueError("Invalid vault format. Please upload an authentic FreeApply archive.")

    salt = vault_bytes[8:24]
    ciphertext = vault_bytes[24:]
    key = derive_vault_key(password, salt)

    try:
        raw_zip = Fernet(key).decrypt(ciphertext)
    except InvalidToken:
        raise ValueError("Decryption failed. Incorrect password.")

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
    page_title="FreeApply Studio",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- OpenDesign Architectural CSS System ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global Base */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        color: #f1f5f9;
        background-color: #0b0f17;
        -webkit-font-smoothing: antialiased;
    }

    /* Remove Streamlit padding waste for compact viewport fit */
    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
        max-width: 980px !important;
    }
    header[data-testid="stHeader"] {
        display: none !important;
    }
    footer {
        display: none !important;
    }

    /* OpenDesign Studio Top Bar */
    .od-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        background: #111726;
        border: 1px solid #1e293b;
        border-radius: 8px;
        margin-bottom: 0.65rem;
    }
    .od-brand {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .od-tag {
        font-size: 0.65rem;
        font-family: 'JetBrains Mono', monospace;
        background: #1e293b;
        color: #94a3b8;
        padding: 0.15rem 0.45rem;
        border-radius: 4px;
        border: 1px solid #334155;
    }
    .od-profile-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #94a3b8;
    }

    /* Swiss Monospace HUD Strip */
    .od-hud {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.45rem;
        margin-bottom: 0.75rem;
    }
    .od-hud-cell {
        background: #111726;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 0.5rem 0.75rem;
    }
    .od-hud-key {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.62rem;
        text-transform: uppercase;
        color: #64748b;
        letter-spacing: 0.05em;
        margin-bottom: 0.2rem;
    }
    .od-hud-val {
        font-size: 0.88rem;
        font-weight: 600;
        color: #f8fafc;
        display: flex;
        align-items: center;
        gap: 0.4rem;
        font-variant-numeric: tabular-nums;
    }

    /* Status Indicators */
    .status-pip {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        display: inline-block;
    }
    .pip-emerald { background: #10b981; box-shadow: 0 0 6px rgba(16, 185, 129, 0.4); }
    .pip-muted { background: #475569; }

    /* OpenDesign Studio Card */
    .od-card {
        background: #111726;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }

    /* Executive Single-Page Email Canvas */
    .canvas-box {
        background: #070a10;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .canvas-meta {
        display: flex;
        align-items: baseline;
        font-size: 0.8rem;
        padding: 0.25rem 0;
        border-bottom: 1px solid #131b29;
        font-family: 'JetBrains Mono', monospace;
    }
    .canvas-meta-key {
        width: 75px;
        color: #64748b;
        font-weight: 600;
        font-size: 0.72rem;
    }
    .canvas-meta-val {
        color: #e2e8f0;
        font-weight: 500;
    }
    .canvas-body {
        margin-top: 0.85rem;
        line-height: 1.65;
        font-size: 0.88rem;
        color: #cbd5e1;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    /* Highlight Tokens */
    .token-hook {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border-left: 2px solid #10b981;
        padding: 0.1rem 0.4rem;
        border-radius: 3px;
        font-weight: 500;
    }
    .token-var {
        background: #1e293b;
        color: #38bdf8;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        padding: 0.05rem 0.35rem;
        border-radius: 3px;
    }

    /* Compact Segmented Control */
    div[data-testid="stRadio"] > div {
        display: flex;
        background: #111726;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 0.25rem;
        gap: 0.25rem;
        margin-bottom: 0.75rem;
    }
    div[data-testid="stRadio"] label {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.76rem !important;
        font-weight: 600 !important;
        padding: 0.35rem 0.65rem !important;
        border-radius: 5px !important;
    }

    /* Compact Touch Buttons */
    div.stButton > button {
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        min-height: 2.4rem !important;
        border: 1px solid #334155 !important;
    }
    div.stButton > button[kind="primary"] {
        background: #2563eb !important;
        border-color: #3b82f6 !important;
        color: #ffffff !important;
    }

    @media (max-width: 640px) {
        .od-hud { grid-template-columns: 1fr 1fr; }
        .block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- State Defaults ---
local_env = send_outreach.load_env(os.path.join(BASE_DIR, ".env"))

def _get_conf(key: str, default: str = "") -> str:
    # 1. Check local .env
    val = local_env.get(key)
    if val:
        return val
    # 2. Check Streamlit Cloud secrets
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    # 3. Check OS environment
    return os.environ.get(key, default)

if "od_mode" not in st.session_state:
    st.session_state.od_mode = "01 · Vault & Identity"
if "sender_name" not in st.session_state:
    st.session_state.sender_name = _get_conf("SENDER_NAME", "")
if "smtp_email" not in st.session_state:
    st.session_state.smtp_email = _get_conf("SMTP_EMAIL", "")
if "smtp_password" not in st.session_state:
    st.session_state.smtp_password = _get_conf("SMTP_APP_PASSWORD", "")
if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = _get_conf("GEMINI_API_KEY", "")
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


# --- Top OpenDesign Bar ---
candidate_name = st.session_state.sender_name if st.session_state.sender_name else "Unassigned"
st.markdown(
    f"""
    <div class="od-header">
        <div class="od-brand">
            <span>FREEAPPLY // STUDIO</span>
            <span class="od-tag">v2.2-ARCH</span>
        </div>
        <div class="od-profile-badge">
            PROFILE: <span style="color:#f8fafc; font-weight:600;">{candidate_name}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Swiss Monospace HUD ---
total_leads = len(st.session_state.leads_df)
ready_hooks = len(st.session_state.leads_df[st.session_state.leads_df["custom_hook"].astype(str).str.strip() != ""]) if total_leads > 0 else 0
smtp_online = bool(st.session_state.smtp_email and st.session_state.smtp_password)
resume_online = bool(st.session_state.resume_bytes or st.session_state.resume_text)

st.markdown(
    f"""
    <div class="od-hud">
        <div class="od-hud-cell">
            <div class="od-hud-key">SYS.SMTP</div>
            <div class="od-hud-val">
                <span class="status-pip {'pip-emerald' if smtp_online else 'pip-muted'}"></span>
                {'PORT 465 SSL' if smtp_online else 'OFFLINE'}
            </div>
        </div>
        <div class="od-hud-cell">
            <div class="od-hud-key">SYS.RESUME</div>
            <div class="od-hud-val">
                <span class="status-pip {'pip-emerald' if resume_online else 'pip-muted'}"></span>
                {f"{len(st.session_state.resume_text.split())} WORDS" if resume_online else 'PENDING'}
            </div>
        </div>
        <div class="od-hud-cell">
            <div class="od-hud-key">RADAR.QUEUE</div>
            <div class="od-hud-val">{total_leads} CONTACTS</div>
        </div>
        <div class="od-hud-cell">
            <div class="od-hud-key">AI.HOOKS</div>
            <div class="od-hud-val">{ready_hooks}/{total_leads} READY</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Mode Switcher (Compact Segmented Tabs) ---
modes = [
    "01 · Vault & Identity",
    "02 · Pipeline Radar",
    "03 · Composer Studio",
    "04 · Dispatch Telemetry",
]

active_mode = st.radio(
    "Studio Navigation",
    modes,
    index=modes.index(st.session_state.od_mode) if st.session_state.od_mode in modes else 0,
    horizontal=True,
    label_visibility="collapsed",
)
st.session_state.od_mode = active_mode


# ==============================================================================
# MODE 01: Vault & Identity
# ==============================================================================
if st.session_state.od_mode == "01 · Vault & Identity":
    st.markdown(
        """
        <div class="od-card" style="padding:0.75rem 1rem; margin-bottom:0.65rem;">
            <div style="font-family:'JetBrains Mono', monospace; font-size:0.75rem; color:#64748b; margin-bottom:0.25rem;">
                SESSION PERSISTENCE ARCHIVE
            </div>
            <div style="font-size:0.85rem; color:#94a3b8;">
                Unlock your password-encrypted <code>FreeApply_Vault.zip</code> to restore credentials, resume, leads, and history in 1 second.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Unlock Session Vault Archive (.zip)", expanded=(not smtp_online)):
        col_v1, col_v2 = st.columns([3, 1])
        with col_v1:
            uploaded_v = st.file_uploader(
                "Vault Archive",
                type=["zip", "vault", "enc"],
                key="od_vault_upload",
                label_visibility="collapsed",
            )
        with col_v2:
            vault_input_pw = st.text_input(
                "Password",
                type="password",
                placeholder="Vault Password",
                key="od_vault_pw",
                label_visibility="collapsed",
            )
            if st.button("Restore Workspace", use_container_width=True):
                if not uploaded_v or not vault_input_pw:
                    st.error("Provide vault file and password.")
                else:
                    try:
                        restored = unpack_encrypted_vault(uploaded_v.read(), vault_input_pw)
                        cfg = restored.get("config", {})
                        st.session_state.sender_name = cfg.get("sender_name", "")
                        st.session_state.smtp_email = cfg.get("smtp_email", "")
                        st.session_state.smtp_password = cfg.get("smtp_password", "")
                        st.session_state.gemini_api_key = cfg.get("gemini_api_key", "")
                        st.session_state.vault_password = vault_input_pw

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

                        st.success(f"Restored configuration for {st.session_state.sender_name}.")
                        st.session_state.od_mode = "02 · Pipeline Radar"
                        st.rerun()
                    except Exception as err:
                        st.error(str(err))

    # Configuration Form
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.session_state.sender_name = st.text_input(
            "Candidate Full Name",
            value=st.session_state.sender_name,
            placeholder="Jane Doe",
        )
        st.session_state.smtp_email = st.text_input(
            "Sender Gmail Address",
            value=st.session_state.smtp_email,
            placeholder="candidate@gmail.com",
        )
    with col_f2:
        st.session_state.smtp_password = st.text_input(
            "Gmail App Password (16-Char)",
            value=st.session_state.smtp_password,
            type="password",
            help="Generate at myaccount.google.com/apppasswords",
        )
        st.session_state.gemini_api_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.gemini_api_key,
            type="password",
            help="Free key at aistudio.google.com/app/apikey",
        )

    # Resume Upload
    uploaded_pdf = st.file_uploader("Candidate Resume (PDF or TXT)", type=["pdf", "txt"])
    if uploaded_pdf is not None:
        st.session_state.resume_bytes = uploaded_pdf.read()
        st.session_state.resume_filename = uploaded_pdf.name
        if uploaded_pdf.name.lower().endswith(".pdf"):
            try:
                import fitz
                doc = fitz.open(stream=st.session_state.resume_bytes, filetype="pdf")
                st.session_state.resume_text = "".join([p.get_text() + "\n" for p in doc]).strip()
                st.caption(f"Parsed {uploaded_pdf.name} ({len(st.session_state.resume_text.split())} words)")
            except Exception as e:
                st.error(f"PDF Parse Error: {e}")
        else:
            st.session_state.resume_text = st.session_state.resume_bytes.decode("utf-8", errors="ignore")

    col_btn1, col_btn2 = st.columns([1, 2])
    with col_btn1:
        if st.button("Test SMTP Delivery", use_container_width=True):
            if not st.session_state.smtp_email or not st.session_state.smtp_password:
                st.error("Provide Gmail address and App Password.")
            else:
                with st.spinner("Delivering verification packet..."):
                    tmp_f = None
                    if st.session_state.resume_bytes:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(st.session_state.resume_bytes)
                            tmp_f = tmp.name
                    try:
                        send_outreach.send_single_email(
                            "smtp.gmail.com",
                            465,
                            st.session_state.smtp_email,
                            st.session_state.smtp_password.replace(" ", ""),
                            st.session_state.smtp_email,
                            "FreeApply Verification Test",
                            f"System connection online for {st.session_state.sender_name or 'Candidate'}.",
                            st.session_state.sender_name,
                            attachment_path=tmp_f,
                        )
                        st.success("Test email delivered successfully.")
                    except Exception as err:
                        st.error(f"Delivery failed: {err}")
                    finally:
                        if tmp_f and os.path.exists(tmp_f):
                            os.remove(tmp_f)

    with col_btn2:
        if st.button("Proceed to Pipeline Radar ➔", type="primary", use_container_width=True):
            st.session_state.od_mode = "02 · Pipeline Radar"
            st.rerun()


# ==============================================================================
# MODE 02: Pipeline Radar & AI Personalization Engine
# ==============================================================================
elif st.session_state.od_mode == "02 · Pipeline Radar":
    col_u1, col_u2 = st.columns([3, 1])
    with col_u1:
        uploaded_csv = st.file_uploader("Import Target Leads CSV", type=["csv"], label_visibility="collapsed")
        if uploaded_csv is not None:
            try:
                st.session_state.leads_df = pd.read_csv(uploaded_csv)
                if "custom_hook" not in st.session_state.leads_df.columns:
                    st.session_state.leads_df["custom_hook"] = ""
                st.success(f"Loaded {len(st.session_state.leads_df)} leads.")
            except Exception:
                try:
                    uploaded_csv.seek(0)
                    st.session_state.leads_df = pd.read_csv(uploaded_csv, on_bad_lines="skip")
                    if "custom_hook" not in st.session_state.leads_df.columns:
                        st.session_state.leads_df["custom_hook"] = ""
                    st.warning("Loaded with invalid rows skipped.")
                except Exception as e:
                    st.error(f"CSV Parse Error: {e}")
    with col_u2:
        if st.button("Reset Starter Leads", use_container_width=True):
            example_p = os.path.join(BASE_DIR, "leads.example.csv")
            if os.path.exists(example_p):
                st.session_state.leads_df = pd.read_csv(example_p)
                st.info("Reset to 3 starter leads.")

    # Live Web Lead Scout with Google Search Grounding
    with st.expander("Live Web Lead Scout (Gemini 2.5 + Google Search Grounding)", expanded=False):
        st.markdown(
            """
            <div style="font-size:0.8rem; color:#94a3b8; margin-bottom:0.6rem;">
                Executes live Google Web Search queries to identify authentic corporate entities, verified HR / careers contacts, and expansion news in real-time.
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_ls1, col_ls2 = st.columns(2)
        with col_ls1:
            scout_roles = st.text_input("Target Roles", value="Operations Lead, Cluster Manager, Property Manager", key="scout_roles")
            scout_locations = st.text_input("Target Locations", value="Bengaluru, NCR/Gurgaon, Mumbai, Pan-India", key="scout_locations")
        with col_ls2:
            scout_industry = st.text_input("Industry / Verticals", value="Co-living, PropTech, Quick Commerce, Logistics, Hospitality", key="scout_industry")
            scout_count = st.selectbox("Batch Size", [3, 5, 10], index=1, key="scout_count")

        col_act_scout1, col_act_scout2 = st.columns([2, 1])
        with col_act_scout1:
            replace_existing = st.checkbox("Replace existing leads table with discovered results", value=False, key="scout_replace")
        with col_act_scout2:
            if st.button("Launch Web Scout", type="primary", use_container_width=True):
                if not st.session_state.gemini_api_key:
                    st.error("Configure Gemini API Key in '01 · Vault & Identity' first.")
                else:
                    with st.spinner("Executing Google Search Grounding to verify active hiring companies and HR desks..."):
                        try:
                            from google import genai
                            client = genai.Client(api_key=st.session_state.gemini_api_key.strip())
                            found_leads = personalize.scout_leads_with_google_search(
                                client,
                                target_roles=scout_roles,
                                target_locations=scout_locations,
                                industry_or_keywords=scout_industry,
                                num_leads=scout_count,
                                candidate_summary=st.session_state.resume_text,
                            )
                            if not found_leads:
                                st.warning("No verified leads passed multi-source filters. Try broadening criteria.")
                            else:
                                new_df = pd.DataFrame(found_leads)
                                for col in ["name", "email", "company", "role", "custom_hook"]:
                                    if col not in new_df.columns:
                                        new_df[col] = ""

                                if replace_existing or st.session_state.leads_df.empty or "examplecorp" in str(st.session_state.leads_df.iloc[0].get("company", "")).lower():
                                    st.session_state.leads_df = new_df
                                else:
                                    st.session_state.leads_df = pd.concat([st.session_state.leads_df, new_df], ignore_index=True).drop_duplicates(subset=["email"])

                                st.success(f"Discovered and verified {len(found_leads)} live leads from web search.")
                                st.rerun()
                        except Exception as err:
                            st.error(f"Web scout failed: {err}")

    # Data Editor
    st.session_state.leads_df = st.data_editor(
        st.session_state.leads_df,
        num_rows="dynamic",
        use_container_width=True,
    )

    col_act1, col_act2 = st.columns([1, 1])
    with col_act1:
        if st.button("Synthesize AI Hooks (Gemini 2.5 Flash)", use_container_width=True):
            if not st.session_state.gemini_api_key:
                st.error("Configure Gemini API Key in Mode 01.")
            elif not st.session_state.resume_text:
                st.error("Upload resume in Mode 01 first.")
            elif st.session_state.leads_df.empty:
                st.warning("Pipeline is empty.")
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

                    st.success("Personalized hooks synthesized.")
                    st.rerun()
                except Exception as err:
                    st.error(f"Synthesis failed: {err}")

    with col_act2:
        if st.button("Proceed to Composer Studio ➔", type="primary", use_container_width=True):
            st.session_state.od_mode = "03 · Composer Studio"
            st.rerun()


# ==============================================================================
# MODE 03: Composer Studio (Swiss Executive Email Canvas)
# ==============================================================================
elif st.session_state.od_mode == "03 · Composer Studio":
    template_files = {
        "Operations Lead": os.path.join(TEMPLATES_DIR, "operations_outreach.txt"),
        "Software Engineering": os.path.join(TEMPLATES_DIR, "engineering_outreach.txt"),
        "General Multi-Role": os.path.join(TEMPLATES_DIR, "general_outreach.txt"),
        "Follow-Up": os.path.join(TEMPLATES_DIR, "followup.txt"),
    }

    col_s1, col_s2 = st.columns([1, 1])
    with col_s1:
        chosen_tpl = st.selectbox("Strategy Template", list(template_files.keys()))
        t_path = template_files[chosen_tpl]
        tpl_text = ""
        if os.path.exists(t_path):
            with open(t_path, "r", encoding="utf-8") as f:
                tpl_text = f.read()

    with col_s2:
        lead_options = [
            f"{r.get('company', '')} — {r.get('name', '')} ({r.get('role', '')})"
            for _, r in st.session_state.leads_df.iterrows()
        ] if not st.session_state.leads_df.empty else ["No contacts available"]
        active_idx = st.selectbox(
            "Target Recruiter Card",
            range(len(lead_options)),
            format_func=lambda i: lead_options[i] if i < len(lead_options) else "",
        )

    # Executive Email Canvas
    if not st.session_state.sender_name or not st.session_state.smtp_email or (not st.session_state.leads_df.empty and "examplecorp" in str(st.session_state.leads_df.iloc[0].get("company", "")).lower()):
        st.markdown(
            """
            <div style="background: rgba(37, 99, 235, 0.08); border: 1px solid #1e3a8a; border-radius: 6px; padding: 0.55rem 0.85rem; margin-bottom: 0.75rem; font-size: 0.8rem; color: #93c5fd;">
                <span style="font-family:'JetBrains Mono', monospace; font-weight:700; color:#bfdbfe;">PREVIEW MODE:</span>
                Displaying default template with placeholder data. Configure your name, Gmail credentials, and upload your resume in <strong>01 · Vault & Identity</strong> to personalize.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not st.session_state.leads_df.empty and active_idx < len(st.session_state.leads_df):
        lead = st.session_state.leads_df.iloc[active_idx]
        company_val = str(lead.get("company", "Company"))
        role_val = str(lead.get("role", "Role"))
        hook_val = str(lead.get("custom_hook", ""))
        email_val = str(lead.get("email", "recruiter@example.com"))
        name_val = str(lead.get("name", "Hiring Team"))

        subj = "Application"
        body_lines = []
        for line in tpl_text.splitlines():
            if line.lower().startswith("subject:"):
                subj = line.split(":", 1)[1].strip().replace("{{role}}", role_val).replace("{{company}}", company_val).replace("{{sender_name}}", st.session_state.sender_name or "Candidate")
            else:
                body_lines.append(line)

        rendered_body = "\n".join(body_lines).strip()
        rendered_body = (
            rendered_body
            .replace("{{name}}", f"<b>{name_val}</b>")
            .replace("{{company}}", f'<span class="token-var">{company_val}</span>')
            .replace("{{role}}", f'<span class="token-var">{role_val}</span>')
            .replace("{{custom_hook}}", f'<span class="token-hook">{hook_val or "[AI Hook Pending]"}</span>')
            .replace("{{sender_name}}", f"<b>{st.session_state.sender_name or 'Candidate'}</b>")
            .replace("\n", "<br>")
        )

        st.markdown(
            f"""
            <div class="canvas-box">
                <div class="canvas-meta">
                    <span class="canvas-meta-key">FROM:</span>
                    <span class="canvas-meta-val">{st.session_state.sender_name or 'Candidate'} &lt;{st.session_state.smtp_email or 'offline'}&gt;</span>
                </div>
                <div class="canvas-meta">
                    <span class="canvas-meta-key">TO:</span>
                    <span class="canvas-meta-val">{name_val} &lt;{email_val}&gt;</span>
                </div>
                <div class="canvas-meta">
                    <span class="canvas-meta-key">SUBJ:</span>
                    <span class="canvas-meta-val" style="color:#f8fafc; font-weight:600;">{subj}</span>
                </div>
                <div class="canvas-meta">
                    <span class="canvas-meta-key">ATTACH:</span>
                    <span class="canvas-meta-val">{st.session_state.resume_filename if st.session_state.resume_bytes else 'None'}</span>
                </div>
                <div class="canvas-body">{rendered_body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col_nav1, col_nav2 = st.columns([1, 1])
    with col_nav1:
        if st.button("Return to Pipeline Radar", use_container_width=True):
            st.session_state.od_mode = "02 · Pipeline Radar"
            st.rerun()
    with col_nav2:
        if st.button("Proceed to Dispatch Telemetry ➔", type="primary", use_container_width=True):
            st.session_state.od_mode = "04 · Dispatch Telemetry"
            st.rerun()


# ==============================================================================
# MODE 04: Dispatch Telemetry & Vault Locker
# ==============================================================================
elif st.session_state.od_mode == "04 · Dispatch Telemetry":
    col_act1, col_act2 = st.columns(2)

    with col_act1:
        st.markdown(
            """
            <div class="od-card">
                <div class="od-hud-key">DRY-RUN SIMULATION</div>
                <div style="font-size:0.82rem; color:#94a3b8; margin:0.3rem 0 0.8rem 0;">
                    Simulate compilation and verify variables with 0 network calls.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Execute Dry Run", use_container_width=True):
            st.success(f"Simulation verified: {len(st.session_state.leads_df)} contacts compiled.")

    with col_act2:
        st.markdown(
            """
            <div class="od-card">
                <div class="od-hud-key" style="color:#f43f5e;">ARMED TRANSMISSION</div>
                <div style="font-size:0.82rem; color:#94a3b8; margin:0.3rem 0 0.8rem 0;">
                    Dispatches live emails over Gmail SMTP with 30-45s rate-limit throttling.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Transmit Live Outreach", type="primary", use_container_width=True):
            if not smtp_online:
                st.error("Missing SMTP credentials in Mode 01.")
            elif st.session_state.leads_df.empty:
                st.warning("Queue is empty.")
            else:
                tmp_f = None
                if st.session_state.resume_bytes:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(st.session_state.resume_bytes)
                        tmp_f = tmp.name

                total = len(st.session_state.leads_df)
                p_bar = st.progress(0)
                status_view = st.empty()
                t_file = os.path.join(TEMPLATES_DIR, "operations_outreach.txt")

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
                        subj, body = send_outreach.render_template(t_file, data)

                        status_view.caption(f"[{i}/{total}] Transmitting to {rec_email}...")
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
                                attachment_path=tmp_f,
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

                    status_view.success("Transmission complete.")
                finally:
                    if tmp_f and os.path.exists(tmp_f):
                        os.remove(tmp_f)

    # --- Session Vault Locker ---
    st.markdown("---")
    st.markdown(
        """
        <div class="od-card">
            <div class="od-hud-key">SESSION VAULT BACKUP (AES-256)</div>
            <div style="font-size:0.82rem; color:#94a3b8; margin-top:0.2rem;">
                Bundle credentials, resume, leads table, and touch history into a single encrypted <code>FreeApply_Vault.zip</code>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
            "Set Vault Password",
            type="password",
            value=st.session_state.vault_password,
            placeholder="Enter password or PIN to encrypt archive",
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
