"""
Delivery channels for sending finalized action items to attendees.

Two channels are supported:
  - Slack, via an Incoming Webhook URL (simplest to set up, no SMTP creds).
  - Email, via SMTP (works with Gmail app passwords, SES SMTP, etc).

Both functions take a list of action item dicts (see parser.py) and return
(success: bool, message: str) so the caller can show a clean result in the UI.
"""

import smtplib
from email.mime.text import MIMEText

import requests


def format_action_items_as_text(action_items):
    """Plain-text summary shared by both delivery channels."""
    if not action_items:
        return "No action items."

    lines = ["Action items from this meeting:", ""]
    for item in action_items:
        owner = item.get("owner") or "Unassigned"
        deadline = item.get("deadline")
        line = f"- {item['text']}  (Owner: {owner}"
        if deadline:
            line += f", Due: {deadline}"
        line += ")"
        lines.append(line)
    return "\n".join(lines)


def send_to_slack(webhook_url, action_items):
    """Post the action items to a Slack channel via an Incoming Webhook.

    Set up a webhook at: https://api.slack.com/messaging/webhooks
    """
    if not webhook_url:
        return False, "No Slack webhook URL configured."

    text = format_action_items_as_text(action_items)

    try:
        response = requests.post(webhook_url, json={"text": text}, timeout=10)
        if response.status_code == 200:
            return True, "Sent to Slack."
        return False, f"Slack returned status {response.status_code}: {response.text}"
    except requests.RequestException as exc:
        return False, f"Failed to reach Slack: {exc}"


def send_email(smtp_host, smtp_port, smtp_user, smtp_password, recipients, action_items, subject="Meeting Action Items"):
    """Send the action items as a plain-text email over SMTP (with STARTTLS).

    Works with most providers' SMTP settings, e.g. Gmail:
      host=smtp.gmail.com, port=587, user=you@gmail.com, password=<app password>
    """
    if not recipients:
        return False, "No recipients specified."

    body = format_action_items_as_text(action_items)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipients, msg.as_string())
        return True, f"Emailed to {', '.join(recipients)}."
    except Exception as exc:  # smtplib raises several distinct exception types
        return False, f"Failed to send email: {exc}"