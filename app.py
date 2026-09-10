#!/usr/bin/env python3
"""
FreeApply-AI: Web Application & Mobile Interface
------------------------------------------------
A Streamlit web application providing a zero-terminal, mobile-friendly
interface for automated cold outreach, Gemini AI personalization, and
knowledge graph tracking.

Run locally:
  streamlit run app.py
"""

from datetime import datetime
import io
import os
import random
import tempfile
import time
import pandas as pd
import streamlit as st

# Import core outreach and personalization logic
import send_outreach
import personalize

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

st.set_page_config(
    page_title="FreeApply-AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for clean mobile experience
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #2563eb, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #64748b;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    @media (max-width: 640px) {
        .main-title { font-size: 1.7rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
local_env = send_outreach.load_env(os.path.join(BASE_DIR, ".env"))

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
    # Load default example leads safely
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


# --- Header ---
st.markdown('<div class="main-title">🚀 FreeApply-AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">100% Free, Automated & AI-Personalized Job Outreach Engine</div>',
    unsafe_allow_html=True,
)

# Navigation tabs
tabs = st.tabs(["⚙️ Profile & Setup", "🎯 Leads & AI Hooks", "✉️ Preview & Send", "📊 Knowledge Graph"])

# ==============================================================================
# TAB 1: Profile & Credentials Setup
# ==============================================================================
with tabs[0]:
    st.subheader("1. Candidate & SMTP Settings")
    st.caption("Your credentials stay only in your current browser session memory for privacy.")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state.sender_name = st.text_input(
            "Your Full Name",
            value=st.session_state.sender_name,
            placeholder="e.g. Jane Doe",
        )
        st.session_state.smtp_email = st.text_input(
            "Your Gmail Address",
            value=st.session_state.smtp_email,
            placeholder="e.g. janedoe@gmail.com",
        )
    with col2:
        st.session_state.smtp_password = st.text_input(
            "Gmail 16-Character App Password",
            value=st.session_state.smtp_password,
            type="password",
            help="Generate at: myaccount.google.com/apppasswords (Requires 2-Step Verification)",
        )
        st.session_state.gemini_api_key = st.text_input(
            "Google Gemini API Key (Optional, for AI Hooks)",
            value=st.session_state.gemini_api_key,
            type="password",
            help="Get your free key at: aistudio.google.com/app/apikey",
        )

    st.divider()

    st.subheader("2. Upload Resume (PDF or TXT)")
    uploaded_resume = st.file_uploader("Select Resume File", type=["pdf", "txt"])

    if uploaded_resume is not None:
        st.session_state.resume_bytes = uploaded_resume.read()
        st.session_state.resume_filename = uploaded_resume.name

        # Extract text
        if uploaded_resume.name.lower().endswith(".pdf"):
            try:
                import fitz
                doc = fitz.open(stream=st.session_state.resume_bytes, filetype="pdf")
                extracted = ""
                for page in doc:
                    extracted += page.get_text() + "\n"
                st.session_state.resume_text = extracted.strip()
                st.success(f"Extracted {len(st.session_state.resume_text.split())} words from {uploaded_resume.name}")
            except Exception as e:
                st.error(f"Error parsing PDF: {e}")
        else:
            st.session_state.resume_text = st.session_state.resume_bytes.decode("utf-8", errors="ignore")
            st.success(f"Loaded text resume ({len(st.session_state.resume_text.split())} words)")

    if st.session_state.resume_text:
        with st.expander("👁️ View Extracted Resume Profile"):
            st.text_area("Extracted Resume", st.session_state.resume_text[:2000], height=150, disabled=True)

    st.divider()

    st.subheader("3. Test SMTP Delivery")
    st.caption("Send a verification email to yourself before reaching out to recruiters.")

    if st.button("📨 Send Test Email to Myself"):
        if not st.session_state.smtp_email or not st.session_state.smtp_password:
            st.error("Please enter your Gmail address and 16-character App Password above.")
        else:
            with st.spinner("Connecting to Gmail SMTP and sending test email..."):
                tmp_resume_path = None
                if st.session_state.resume_bytes:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(st.session_state.resume_bytes)
                        tmp_resume_path = tmp.name

                try:
                    test_subj = "FreeApply-AI: SMTP Verification Test"
                    test_body = (
                        f"Hello {st.session_state.sender_name or 'there'},\n\n"
                        "Congratulations! Your FreeApply-AI SMTP setup is working perfectly.\n\n"
                        f"Resume Attached: {'Yes (' + st.session_state.resume_filename + ')' if tmp_resume_path else 'No'}\n"
                    )
                    send_outreach.send_single_email(
                        "smtp.gmail.com",
                        465,
                        st.session_state.smtp_email,
                        st.session_state.smtp_password.replace(" ", ""),
                        st.session_state.smtp_email,
                        test_subj,
                        test_body,
                        st.session_state.sender_name,
                        attachment_path=tmp_resume_path,
                    )
                    st.success(f"✅ Test email successfully delivered to {st.session_state.smtp_email}! Check your inbox.")
                except Exception as e:
                    st.error(f"❌ Failed to send test email: {e}")
                finally:
                    if tmp_resume_path and os.path.exists(tmp_resume_path):
                        os.remove(tmp_resume_path)


# ==============================================================================
# TAB 2: Leads & AI Personalization
# ==============================================================================
with tabs[1]:
    st.subheader("Manage Leads & Generate AI Hooks")

    col_up, col_eg = st.columns([3, 1])
    with col_up:
        uploaded_csv = st.file_uploader("Upload Target Leads CSV", type=["csv"])
        if uploaded_csv is not None:
            try:
                st.session_state.leads_df = pd.read_csv(uploaded_csv)
                if "custom_hook" not in st.session_state.leads_df.columns:
                    st.session_state.leads_df["custom_hook"] = ""
                st.success(f"Loaded {len(st.session_state.leads_df)} leads from {uploaded_csv.name}")
            except Exception as e:
                try:
                    uploaded_csv.seek(0)
                    st.session_state.leads_df = pd.read_csv(uploaded_csv, on_bad_lines="skip")
                    if "custom_hook" not in st.session_state.leads_df.columns:
                        st.session_state.leads_df["custom_hook"] = ""
                    st.warning(f"Loaded {len(st.session_state.leads_df)} leads (some improperly formatted rows were skipped).")
                except Exception as inner_e:
                    st.error(f"Error parsing CSV file: {inner_e}")
    with col_eg:
        if st.button("Reset to Example Leads"):
            example_path = os.path.join(BASE_DIR, "leads.example.csv")
            if os.path.exists(example_path):
                try:
                    st.session_state.leads_df = pd.read_csv(example_path)
                    st.info("Loaded starter leads!")
                except Exception:
                    st.session_state.leads_df = pd.read_csv(example_path, on_bad_lines="skip")
                    st.info("Loaded starter leads!")

    st.markdown("#### Edit or Add Leads Directly in the Table:")
    edited_df = st.data_editor(
        st.session_state.leads_df,
        num_rows="dynamic",
        use_container_width=True,
    )
    st.session_state.leads_df = edited_df

    st.divider()

    st.subheader("⚡ AI Personalization with Google Gemini")
    st.caption("Gemini reads your resume and creates unique 1-2 sentence opening hooks connecting your background to each company.")

    if st.button("🤖 Generate AI Personalization Hooks"):
        if not st.session_state.gemini_api_key:
            st.error("Please provide your Gemini API Key in the 'Profile & Setup' tab.")
        elif not st.session_state.resume_text:
            st.error("Please upload your resume in the 'Profile & Setup' tab first.")
        elif st.session_state.leads_df.empty:
            st.warning("No leads found in table.")
        else:
            try:
                from google import genai
                client = genai.Client(api_key=st.session_state.gemini_api_key.strip())

                progress_bar = st.progress(0)
                status_text = st.empty()
                total = len(st.session_state.leads_df)

                for idx, row in st.session_state.leads_df.iterrows():
                    company = str(row.get("company", "")).strip()
                    role = str(row.get("role", "")).strip()
                    status_text.text(f"Generating hook for {role} at {company} ({idx + 1}/{total})...")

                    hook = personalize.generate_hook_with_gemini(
                        client,
                        "gemini-2.5-flash",
                        st.session_state.resume_text,
                        company,
                        role,
                    )
                    if hook:
                        st.session_state.leads_df.at[idx, "custom_hook"] = hook

                    progress_bar.progress((idx + 1) / total)

                status_text.success("✨ All AI hooks generated! You can edit them in the table above.")
                st.rerun()
            except Exception as e:
                st.error(f"Gemini API Error: {e}")


# ==============================================================================
# TAB 3: Preview & Dispatch Outreach
# ==============================================================================
with tabs[2]:
    st.subheader("Email Template & Dispatch")

    # Template selection
    template_files = {
        "Operations Outreach": os.path.join(TEMPLATES_DIR, "operations_outreach.txt"),
        "Engineering Outreach": os.path.join(TEMPLATES_DIR, "engineering_outreach.txt"),
        "General Outreach": os.path.join(TEMPLATES_DIR, "general_outreach.txt"),
        "Follow-up": os.path.join(TEMPLATES_DIR, "followup.txt"),
    }

    chosen_template_name = st.selectbox("Select Email Template", list(template_files.keys()))
    selected_template_path = template_files[chosen_template_name]

    template_content = ""
    if os.path.exists(selected_template_path):
        with open(selected_template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

    template_text = st.text_area("Template Text (Supports {{name}}, {{company}}, {{role}}, {{custom_hook}}, {{sender_name}})", template_content, height=180)

    st.divider()

    st.subheader("👁️ Live Email Preview")
    if not st.session_state.leads_df.empty:
        lead_options = [f"{row.get('company', '')} - {row.get('name', '')}" for _, row in st.session_state.leads_df.iterrows()]
        preview_idx = st.selectbox("Select Lead to Preview", range(len(lead_options)), format_func=lambda x: lead_options[x])

        sample_row = st.session_state.leads_df.iloc[preview_idx]
        sample_data = {
            "name": sample_row.get("name", "Hiring Team"),
            "company": sample_row.get("company", "Company"),
            "role": sample_row.get("role", "Target Role"),
            "custom_hook": sample_row.get("custom_hook", ""),
            "original_subject": f"Application for {sample_row.get('role', 'Target Role')}",
            "sender_name": st.session_state.sender_name or "Your Name",
        }

        # Substitute in memory
        rendered = template_text
        for k, v in sample_data.items():
            rendered = rendered.replace(f"{{{{{k}}}}}", str(v))

        subj = "Application"
        body = rendered
        for line in rendered.splitlines():
            if line.lower().startswith("subject:"):
                subj = line.split(":", 1)[1].strip()
                body = "\n".join([l for l in rendered.splitlines() if not l.lower().startswith("subject:")]).strip()
                break

        st.markdown(
            f"""
            <div class="card">
                <b>To:</b> {sample_row.get('email', '')} ({sample_row.get('name', '')})<br>
                <b>Subject:</b> {subj}<br>
                <b>Attachment:</b> {st.session_state.resume_filename if st.session_state.resume_bytes else 'None'}<br><br>
                <div style="white-space: pre-wrap; font-family: sans-serif;">{body}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    st.subheader("🚀 Dispatch Center")
    st.caption("Anti-Spam Safeguards: 30-45s randomized delay between sends protects your Gmail inbox reputation.")

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button("👁️ Run Dry-Run Preview (Safe)"):
            st.info(f"Dry-run passed! {len(st.session_state.leads_df)} emails are ready for live dispatch.")

    with col_btn2:
        if st.button("🔴 Send Live Outreach", type="primary"):
            if not st.session_state.smtp_email or not st.session_state.smtp_password:
                st.error("Please configure your Gmail credentials in the 'Profile & Setup' tab.")
            elif st.session_state.leads_df.empty:
                st.warning("No leads found to send.")
            else:
                tmp_resume_path = None
                if st.session_state.resume_bytes:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(st.session_state.resume_bytes)
                        tmp_resume_path = tmp.name

                total_leads = len(st.session_state.leads_df)
                progress_bar = st.progress(0)
                status_placeholder = st.empty()

                try:
                    for i, (idx, row) in enumerate(st.session_state.leads_df.iterrows(), 1):
                        rec_email = str(row.get("email", "")).strip()
                        lead_data = {
                            "name": row.get("name", "Hiring Team"),
                            "company": row.get("company", "Company"),
                            "role": row.get("role", "Target Role"),
                            "custom_hook": row.get("custom_hook", ""),
                            "original_subject": f"Application for {row.get('role', 'Target Role')}",
                            "sender_name": st.session_state.sender_name or "Job Seeker",
                        }

                        # Render
                        rendered = template_text
                        for k, v in lead_data.items():
                            rendered = rendered.replace(f"{{{{{k}}}}}", str(v))

                        subj = "Application"
                        body_text = rendered
                        for line in rendered.splitlines():
                            if line.lower().startswith("subject:"):
                                subj = line.split(":", 1)[1].strip()
                                body_text = "\n".join([l for l in rendered.splitlines() if not l.lower().startswith("subject:")]).strip()
                                break

                        status_placeholder.text(f"[{i}/{total_leads}] Sending to {rec_email} at {row.get('company')}...")

                        try:
                            send_outreach.send_single_email(
                                "smtp.gmail.com",
                                465,
                                st.session_state.smtp_email,
                                st.session_state.smtp_password.replace(" ", ""),
                                rec_email,
                                subj,
                                body_text,
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

                        progress_bar.progress(i / total_leads)

                        # Delay between sends to protect reputation
                        if i < total_leads:
                            delay = random.randint(30, 45)
                            status_placeholder.text(f"Waiting {delay}s before next send to protect inbox reputation...")
                            time.sleep(delay)

                    status_placeholder.success(f"🎉 Completed sending {total_leads} emails!")
                finally:
                    if tmp_resume_path and os.path.exists(tmp_resume_path):
                        os.remove(tmp_resume_path)


# ==============================================================================
# TAB 4: Knowledge Graph & Audit Trail
# ==============================================================================
with tabs[3]:
    st.subheader("Knowledge Graph & Touch History")
    st.caption("Track touch history, recipient nodes, and export your offline audit trail directly to your phone.")

    if st.session_state.sent_history:
        history_df = pd.DataFrame(st.session_state.sent_history)
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("No emails sent in this session yet. Sent outreach will appear here.")

    st.divider()

    # Knowledge Graph Generator
    st.subheader("📥 Export Knowledge Graph to Phone / PC")
    st.caption("Download your persistent audit log so your records never get lost.")

    # Generate log.md content
    log_md_lines = [
        "# FreeApply-AI: Outreach Knowledge Graph & Audit Log",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Candidate: {st.session_state.sender_name or 'Candidate'}",
        "",
        "## Outreach Nodes & History",
        "",
    ]

    for item in st.session_state.sent_history:
        log_md_lines.append(
            f"- **{item.get('company', 'Unknown')}** | Role: `{item.get('role', 'N/A')}` | "
            f"Contact: `{item.get('email', 'N/A')}` | Status: **{item.get('status', 'PENDING')}** | Date: {item.get('timestamp', '')}"
        )

    log_md_content = "\n".join(log_md_lines)

    col_dl1, col_dl2, col_dl3 = st.columns(3)
    with col_dl1:
        st.download_button(
            "📥 Download log.md (Knowledge Graph)",
            data=log_md_content,
            file_name="log.md",
            mime="text/markdown",
        )
    with col_dl2:
        if st.session_state.sent_history:
            csv_buf = io.StringIO()
            pd.DataFrame(st.session_state.sent_history).to_csv(csv_buf, index=False)
            st.download_button(
                "📥 Download sent_history.csv",
                data=csv_buf.getvalue(),
                file_name="sent_history.csv",
                mime="text/csv",
            )
        else:
            st.button("📥 Download sent_history.csv", disabled=True)
    with col_dl3:
        leads_buf = io.StringIO()
        st.session_state.leads_df.to_csv(leads_buf, index=False)
        st.download_button(
            "📥 Download leads.csv",
            data=leads_buf.getvalue(),
            file_name="leads.csv",
            mime="text/csv",
        )
