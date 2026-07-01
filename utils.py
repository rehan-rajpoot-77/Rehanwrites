"""
Utility module for the Opt-In Email Sample Generator.
Contains AI content generation, email sending, reply listening,
and PDF invoice generation -- all consent-based and ethical.
"""

import csv
import imaplib
import email
import json
import logging
import os
import re
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from config import (
    AI_PROVIDER,
    GROQ_API_KEY,
    OPENAI_API_KEY,
    GMAIL_ADDRESS,
    GMAIL_APP_PASSWORD,
    SMTP_SERVER,
    SMTP_PORT,
    IMAP_SERVER,
    MAX_EMAILS_PER_HOUR,
    CAMPAIGN_PRICE,
    CAMPAIGN_EMAIL_COUNT,
    INVOICES_DIR,
    ORDERS_CSV,
)

logging.basicConfig(
    filename="errors.log",
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_email_send_times = []


# =============================================================================
# AI Content Generator
# =============================================================================

def _call_groq_api(system_prompt: str, user_prompt: str) -> str:
    """Call the Groq API to generate content."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4000,
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers, json=payload, timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _call_openai_api(system_prompt: str, user_prompt: str) -> str:
    """Call the OpenAI API to generate content (fallback)."""
    import openai
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=4000,
    )
    return response.choices[0].message.content


def _call_ai(system_prompt: str, user_prompt: str) -> str:
    """Route AI calls to the configured provider (Groq or OpenAI)."""
    if AI_PROVIDER == "groq":
        return _call_groq_api(system_prompt, user_prompt)
    elif AI_PROVIDER == "openai":
        return _call_openai_api(system_prompt, user_prompt)
    raise RuntimeError("No AI provider configured. Set GROQ_API_KEY or OPENAI_API_KEY.")


def generate_sample_emails(business_name: str, niche: str) -> list:
    """Generate 3 short, warm, value-first sample emails (no urgency/pressure)."""
    system_prompt = (
        "You are an expert email copywriter who believes in ethical marketing. "
        "You write warm, helpful, genuinely valuable emails. "
        "NEVER use fake urgency, fake scarcity, countdown timers, or pressure tactics. "
        "Output must be valid JSON: [{\"subject\": \"...\", \"body\": \"...\"}, ...] -- exactly 3 items."
    )
    user_prompt = (
        f"Business Name: {business_name}\nNiche/Industry: {niche}\n\n"
        f"Generate 3 short marketing emails (150-250 words each). "
        f"Each should share a genuinely useful tip and end with a soft, honest CTA. "
        f"Return ONLY valid JSON, no markdown fences."
    )

    try:
        raw = _call_ai(system_prompt, user_prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        emails = json.loads(raw)
        if not isinstance(emails, list) or len(emails) != 3:
            raise ValueError("Expected 3 emails")
        for e in emails:
            if "subject" not in e or "body" not in e:
                raise ValueError("Missing keys")
        return emails
    except Exception as e:
        logging.error(f"Sample generation failed, using fallback: {e}")
        return [
            {"subject": f"A quick tip for {business_name}",
             "body": f"Hi there,\n\nA quick insight that has helped businesses like {business_name} in {niche}: focus on genuine relationships with your audience first.\n\nReply if you'd like to chat about your email strategy.\n\nBest,\nYour Email Copywriter"},
            {"subject": "The one thing most businesses overlook",
             "body": f"Hi,\n\nAfter working with {niche} businesses, I've noticed: the ones that succeed show up consistently for their audience.\n\nOne valuable email per week, every week -- no gimmicks needed.\n\nBest,\nYour Email Copywriter"},
            {"subject": f"How {business_name} can stand out",
             "body": f"Hi there,\n\nIn a crowded {niche} market, businesses that stand out have a clear, authentic voice. Write like you talk -- your audience will notice.\n\nReply if you want to explore this further.\n\nBest,\nYour Email Copywriter"},
        ]


def generate_full_campaign(business_name: str, niche: str) -> list:
    """Generate a 30-email nurture campaign for a CONFIRMED paying client."""
    system_prompt = (
        "You are a senior email copywriter specializing in long-term nurture campaigns. "
        "You believe in permission-based marketing and never use manipulation. "
        "NEVER use fake urgency, scarcity, countdowns, or pressure tactics. "
        "Output must be a valid JSON array with exactly 30 items: "
        "[{\"subject\": \"...\", \"body\": \"...\"}, ...]"
    )
    user_prompt = (
        f"Business Name: {business_name}\nNiche/Industry: {niche}\n\n"
        f"Create a 30-email nurture campaign:\n"
        f"1-5: Welcome series\n6-20: Value & education\n"
        f"21-28: Soft CTAs, honest objection handling\n29-30: Direct, respectful offer.\n"
        f"200-350 words each. Return ONLY valid JSON, no markdown fences."
    )

    try:
        raw = _call_ai(system_prompt, user_prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        emails = json.loads(raw)
        if not isinstance(emails, list) or len(emails) != CAMPAIGN_EMAIL_COUNT:
            raise ValueError("Wrong count")
        for e in emails:
            if "subject" not in e or "body" not in e:
                raise ValueError("Missing keys")
        return emails
    except Exception as e:
        logging.error(f"Campaign generation failed, using fallback: {e}")
        fallback = []
        for i in range(1, CAMPAIGN_EMAIL_COUNT + 1):
            fallback.append({
                "subject": f"Email {i}: Your {niche} journey continues",
                "body": f"Hi there,\n\nThis is email {i} of your campaign for {business_name}. "
                        f"Consistency and authenticity win in {niche}. Keep showing up for your audience.\n\nBest,\nYour Email Copywriter",
            })
        return fallback


# =============================================================================
# Email Sender
# =============================================================================

def _check_rate_limit() -> bool:
    """Enforce max emails/hour."""
    global _email_send_times
    now = datetime.now()
    _email_send_times = [t for t in _email_send_times if now - t < timedelta(hours=1)]
    return len(_email_send_times) < MAX_EMAILS_PER_HOUR


def send_email(to_email: str, subject: str, body_html: str, body_plain: str) -> bool:
    """
    Send an email via Gmail SMTP (HTML + plain text).
    Only ever call this with addresses that opted in via the landing page form.
    """
    if not _check_rate_limit():
        logging.warning(f"Rate limit hit. Skipping email to {to_email}")
        return False
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        logging.error("Gmail credentials not configured.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg.attach(MIMEText(body_plain, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, [to_email], msg.as_string())
        _email_send_times.append(datetime.now())
        return True
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")
        return False


# =============================================================================
# Reply Listener
# =============================================================================

def check_replies() -> list:
    """Check Gmail inbox for UNSEEN emails showing purchase intent, log to orders.csv."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        logging.error("Gmail credentials not configured.")
        return []

    new_orders = []
    # Use word-boundary regex so "yes" doesn't match inside "system", "eyes", etc.
    intent_keywords = [
        r"\byes\b", r"\binterested\b", r"\bbuy\b",
        r"let'?s do it", r"\bi'?m in\b", r"sign me up",
    ]
    intent_pattern = re.compile("|".join(intent_keywords), re.IGNORECASE)

    # Skip automated/notification senders so they never get treated as leads
    blocked_sender_patterns = [
        "noreply", "no-reply", "donotreply", "do-not-reply",
        "notifications@", "notification@", "mailer-daemon",
        "facebookmail.com", "instagram.com", "twitter.com", "x.com",
        "linkedin.com", "openai.com", "anthropic.com", "google.com",
        "microsoft.com", "apple.com", "amazon.com", "support@",
        "alerts@", "updates@", "info@", "team@",
    ]

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        _, data = mail.search(None, "UNSEEN")
        email_ids = data[0].split()

        for eid in email_ids:
            _, msg_data = mail.fetch(eid, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            from_header = msg.get("From", "")
            sender_match = re.search(r"<([^>]+)>", from_header)
            sender_email = sender_match.group(1) if sender_match else from_header.strip()

            # Skip known automated/notification senders entirely
            sender_lower = sender_email.lower()
            if any(pattern in sender_lower for pattern in blocked_sender_patterns):
                mail.store(eid, "+FLAGS", "\\Seen")
                continue

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ct = part.get_content_type()
                    if ct == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    elif ct == "text/html":
                        html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        body = re.sub(r"<[^>]+>", " ", html)
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            body_lower = body.lower()
            if intent_pattern.search(body_lower):
                business_name = "Unknown"
                biz_match = re.search(r"(?:business|company|for)\s*:?\s*([A-Za-z0-9\s&]+)", body, re.IGNORECASE)
                if biz_match:
                    business_name = biz_match.group(1).strip()[:100]

                existing_emails = set()
                if ORDERS_CSV.exists():
                    with open(ORDERS_CSV, "r", newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        existing_emails = {row["email"] for row in reader}

                if sender_email not in existing_emails:
                    order = {
                        "email": sender_email,
                        "business_name": business_name,
                        "status": "pending_invoice",
                        "date": datetime.now().isoformat(),
                    }
                    new_orders.append(order)
                    file_exists = ORDERS_CSV.exists()
                    with open(ORDERS_CSV, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=["email", "business_name", "status", "date"])
                        if not file_exists:
                            writer.writeheader()
                        writer.writerow(order)

            mail.store(eid, "+FLAGS", "\\Seen")

        mail.close()
        mail.logout()
    except Exception as e:
        logging.error(f"Error checking replies: {e}")

    return new_orders


# =============================================================================
# PDF Invoice Generator
# =============================================================================

def generate_invoice_pdf(business_name: str, campaign_emails: list) -> str:
    """Generate a PDF listing the 30 campaign emails. Call only for CONFIRMED orders."""
    if not campaign_emails or len(campaign_emails) != CAMPAIGN_EMAIL_COUNT:
        raise ValueError(f"Campaign must contain exactly {CAMPAIGN_EMAIL_COUNT} emails")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^\w\s-]", "", business_name).strip().replace(" ", "_")
    pdf_path = INVOICES_DIR / f"invoice_{safe_name}_{timestamp}.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter,
                             rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("InvoiceTitle", parent=styles["Heading1"], fontSize=24, spaceAfter=30)
    story.append(Paragraph("Campaign Invoice & Preview", title_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"<b>Client:</b> {business_name}", styles["Normal"]))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%B %d, %Y')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Service:</b> {CAMPAIGN_EMAIL_COUNT}-Email Nurture Campaign", styles["Normal"]))
    story.append(Paragraph(f"<b>Total:</b> ${CAMPAIGN_PRICE:,.2f}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("<b>Campaign Email Sequence</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.1 * inch))

    for i, em in enumerate(campaign_emails, 1):
        story.append(Paragraph(f"<b>Email {i}:</b> {em['subject']}", styles["Heading3"]))
        body_clean = em["body"].replace("\n", "<br/>")
        story.append(Paragraph(body_clean, styles["Normal"]))
        story.append(Spacer(1, 0.15 * inch))

    story.append(Spacer(1, 0.3 * inch))
    payment_style = ParagraphStyle("Payment", parent=styles["Normal"], fontSize=12)
    story.append(Paragraph(
        f"Payment of ${CAMPAIGN_PRICE:,.2f} is due upon agreement. "
        f"Use the payment link in the email to complete your order.",
        payment_style
    ))

    doc.build(story)
    return str(pdf_path)


def send_invoice(to_email: str, pdf_path: str) -> bool:
    """Send invoice PDF + payment link, then mark order as delivered in orders.csv."""
    subject = "Your 30-Email Campaign Invoice & Preview"
    body_plain = (
        f"Hi there,\n\nThank you for confirming your order! Attached is your complete "
        f"30-email campaign preview and invoice.\n\n"
        f"Complete payment here:\nPAYMENT_LINK_HERE\n\n"
        f"After payment, I'll send the final campaign files in your preferred format.\n\n"
        f"Questions? Just reply.\n\nBest,\nYour Email Copywriter"
    )
    body_html = f"""
    <html><body style="font-family: Georgia, serif; line-height:1.6; color:#333; max-width:600px; margin:0 auto;">
        <p>Hi there,</p>
        <p>Thank you for confirming your order! Attached is your complete
        <strong>30-email campaign preview and invoice</strong>.</p>
        <p>Complete payment here:</p>
        <p style="text-align:center; margin:30px 0;">
            <a href="PAYMENT_LINK_HERE" style="background:#1a1a1a;color:white;padding:12px 24px;text-decoration:none;border-radius:4px;display:inline-block;">Complete Payment</a>
        </p>
        <p>After payment, I'll send the final campaign files in your preferred format.</p>
        <p>Questions? Just reply.</p>
        <p>Best regards,<br>Your Email Copywriter</p>
    </body></html>
    """

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg_alt = MIMEMultipart("alternative")
    msg_alt.attach(MIMEText(body_plain, "plain", "utf-8"))
    msg_alt.attach(MIMEText(body_html, "html", "utf-8"))
    msg.attach(msg_alt)

    try:
        with open(pdf_path, "rb") as f:
            from email.mime.base import MIMEBase
            from email import encoders
            attachment = MIMEBase("application", "pdf")
            attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header("Content-Disposition", f"attachment; filename={os.path.basename(pdf_path)}")
            msg.attach(attachment)
    except Exception as e:
        logging.error(f"Failed to attach PDF {pdf_path}: {e}")
        return False

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, [to_email], msg.as_string())
    except Exception as e:
        logging.error(f"Failed to send invoice to {to_email}: {e}")
        return False

    try:
        if ORDERS_CSV.exists():
            rows = []
            with open(ORDERS_CSV, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row["email"] == to_email and row["status"] == "confirmed":
                        row["status"] = "delivered"
                    rows.append(row)
            with open(ORDERS_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
    except Exception as e:
        logging.error(f"Failed to update order status for {to_email}: {e}")

    return True
