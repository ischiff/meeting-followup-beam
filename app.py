import os

import streamlit as st

from delivery import format_action_items_as_text, send_email, send_to_slack
from parser import extract_action_items

st.set_page_config(page_title="Meeting Follow-Up Automator", page_icon="📋")
st.title("📋 Meeting Follow-Up Automator")

st.write(
    "Paste meeting notes, review the auto-extracted action items, adjust "
    "owners/deadlines if needed, then send them to attendees."
)

if "action_items" not in st.session_state:
    st.session_state.action_items = []

notes = st.text_area(
    "Meeting Notes",
    placeholder=(
        "Paste your notes here...\n\n"
        "e.g.\nTODO: Sarah to send the revised proposal by Friday\n"
        "Action: follow up with legal (owner: Mike, due 7/18)"
    ),
    height=250,
)

if st.button("Generate Action Items", type="primary"):
    if notes.strip():
        st.session_state.action_items = extract_action_items(notes)
        if not st.session_state.action_items:
            st.info(
                "No action items found. Try lines starting with TODO, "
                "Action:, or AI:, e.g. 'TODO: Sarah to send the deck by Friday'."
            )
    else:
        st.warning("Please paste meeting notes first.")

# --- Review & assign ---
if st.session_state.action_items:
    st.subheader("Review & Assign")
    st.caption("Edit any field before sending — the parser is a best guess, not gospel.")

    header_cols = st.columns([3, 2, 2, 1])
    header_cols[0].markdown("**Action Item**")
    header_cols[1].markdown("**Owner**")
    header_cols[2].markdown("**Deadline**")
    header_cols[3].markdown("**Keep**")

    final_items = []
    for i, item in enumerate(st.session_state.action_items):
        cols = st.columns([3, 2, 2, 1])
        with cols[0]:
            text = st.text_input(
                "Action Item", value=item.get("text", ""), key=f"text_{i}", label_visibility="collapsed"
            )
        with cols[1]:
            owner = st.text_input(
                "Owner", value=item.get("owner", ""), key=f"owner_{i}", label_visibility="collapsed", placeholder="Owner"
            )
        with cols[2]:
            deadline = st.text_input(
                "Deadline", value=item.get("deadline", ""), key=f"deadline_{i}",
                label_visibility="collapsed", placeholder="Deadline",
            )
        with cols[3]:
            keep = st.checkbox("Keep", value=True, key=f"keep_{i}", label_visibility="collapsed")

        if keep and text.strip():
            final_items.append({"text": text.strip(), "owner": owner.strip(), "deadline": deadline.strip()})

    if not final_items:
        st.info("All rows removed — nothing to send.")

    st.divider()
    st.subheader("Send to Attendees")

    tab_slack, tab_email = st.tabs(["Slack", "Email"])

    with tab_slack:
        default_webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
        webhook_url = st.text_input(
            "Slack Incoming Webhook URL",
            value=default_webhook,
            type="password",
            help="Create one at https://api.slack.com/messaging/webhooks. "
            "Set SLACK_WEBHOOK_URL as an env var to pre-fill this.",
        )
        if st.button("Send to Slack"):
            if not webhook_url:
                st.warning("Enter a Slack webhook URL first.")
            else:
                with st.spinner("Sending to Slack..."):
                    success, message = send_to_slack(webhook_url, final_items)
                st.success(message) if success else st.error(message)

    with tab_email:
        col1, col2 = st.columns(2)
        with col1:
            smtp_host = st.text_input("SMTP Host", value=os.environ.get("SMTP_HOST", "smtp.gmail.com"))
            smtp_user = st.text_input("SMTP Username (sender email)", value=os.environ.get("SMTP_USER", ""))
        with col2:
            smtp_port = st.number_input("SMTP Port", value=int(os.environ.get("SMTP_PORT", 587)))
            smtp_password = st.text_input(
                "SMTP Password",
                value=os.environ.get("SMTP_PASSWORD", ""),
                type="password",
                help="For Gmail, use an App Password, not your normal login password.",
            )
        recipients_raw = st.text_input("Recipients (comma-separated emails)")

        if st.button("Send Email"):
            recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
            if not (smtp_host and smtp_user and smtp_password and recipients):
                st.warning("Fill in SMTP settings and at least one recipient.")
            else:
                with st.spinner("Sending email..."):
                    success, message = send_email(
                        smtp_host, int(smtp_port), smtp_user, smtp_password, recipients, final_items
                    )
                st.success(message) if success else st.error(message)

    with st.expander("Preview message"):
        st.code(format_action_items_as_text(final_items), language=None)