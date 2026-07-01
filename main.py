"""
Orchestrator for the Opt-In Email Sample Generator.

Loop every 30 minutes:
  1. Check for new landing page signups -> send 3 free sample emails
  2. Check inbox for replies -> detect intent, log to orders.csv
  3. Process CONFIRMED orders -> generate campaign + invoice + send

ETHICAL RULES ENFORCED:
- Only emails to opt-in addresses (landing_page_submissions.csv)
- Free samples before any payment discussion
- Invoice only sent after explicit client confirmation
- No scraping, no bulk unsolicited emails, no fake urgency
"""

import csv
import logging
import time
import traceback
from datetime import datetime
from pathlib import Path

from config import validate_config, SUBMISSIONS_CSV, ORDERS_CSV
from utils import (
    generate_sample_emails,
    generate_full_campaign,
    send_email,
    check_replies,
    generate_invoice_pdf,
    send_invoice,
)

logging.basicConfig(
    filename="errors.log",
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

SAMPLES_SENT_CSV = Path("samples_sent.csv")


def _get_processed_submissions() -> set:
    processed = set()
    if SAMPLES_SENT_CSV.exists():
        with open(SAMPLES_SENT_CSV, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                processed.add(row["email"])
    return processed


def _mark_samples_sent(email_addr, business_name, niche):
    file_exists = SAMPLES_SENT_CSV.exists()
    with open(SAMPLES_SENT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "business_name", "niche", "sent_at"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "email": email_addr, "business_name": business_name,
            "niche": niche, "sent_at": datetime.now().isoformat(),
        })


def _get_confirmed_orders() -> list:
    if not ORDERS_CSV.exists():
        return []
    confirmed = []
    with open(ORDERS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") == "confirmed":
                confirmed.append(row)
    return confirmed


def _mark_order_processing(email_addr):
    if not ORDERS_CSV.exists():
        return
    rows = []
    with open(ORDERS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["email"] == email_addr and row["status"] == "confirmed":
                row["status"] = "processing"
            rows.append(row)
    with open(ORDERS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def process_new_signups():
    """Send 3 free sample emails to anyone who filled the landing page form."""
    if not SUBMISSIONS_CSV.exists():
        return 0

    processed = _get_processed_submissions()
    new_signups = []
    with open(SUBMISSIONS_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            em = row.get("email", "").strip().lower()
            if em and em not in processed:
                new_signups.append(row)

    sent_count = 0
    for signup in new_signups:
        try:
            name = signup.get("name", "there")
            business_name = signup.get("business_name", "Your Business")
            niche = signup.get("niche", "general")
            em = signup.get("email", "").strip().lower()
            if not em:
                continue

            samples = generate_sample_emails(business_name, niche)

            for i, sample in enumerate(samples, 1):
                subject = sample["subject"]
                body_plain = sample["body"]
                body_html = f"""
                <html><body style="font-family: Georgia, serif; line-height:1.6; color:#333; max-width:600px; margin:0 auto;">
                    <p>Hi {name},</p>
                    <p>Here is sample email <strong>{i} of 3</strong> for <strong>{business_name}</strong>:</p>
                    <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
                    <h2 style="color:#1a1a1a;font-size:18px;">{subject}</h2>
                    <div style="white-space:pre-wrap;">{body_plain.replace(chr(10), '<br>')}</div>
                    <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
                    <p style="font-size:13px;color:#666;">
                        These are free samples -- no obligation. If you'd like the full 30-email campaign,
                        just reply with "interested" and we'll discuss next steps.
                    </p>
                </body></html>
                """
                body_plain_full = (
                    f"Hi {name},\n\nHere is sample email {i} of 3 for {business_name}:\n\n---\n\n"
                    f"Subject: {subject}\n\n{body_plain}\n\n---\n\n"
                    f"These are free samples -- no obligation. If you'd like the full 30-email "
                    f"campaign, just reply with \"interested\" and we'll discuss next steps."
                )

                success = send_email(em, subject, body_html, body_plain_full)
                if not success:
                    logging.error(f"Failed to send sample {i} to {em}")
                    break
                time.sleep(2)

            _mark_samples_sent(em, business_name, niche)
            sent_count += 1
        except Exception as e:
            logging.error(f"Error processing signup {signup}: {e}\n{traceback.format_exc()}")

    return sent_count


def process_confirmed_orders():
    """Generate full campaign + invoice for CONFIRMED orders only."""
    orders = _get_confirmed_orders()
    processed = 0

    for order in orders:
        try:
            em = order["email"]
            business_name = order.get("business_name", "Your Business")
            _mark_order_processing(em)

            campaign = generate_full_campaign(business_name, "general")
            pdf_path = generate_invoice_pdf(business_name, campaign)
            success = send_invoice(em, pdf_path)
            if success:
                processed += 1
            else:
                logging.error(f"Failed to send invoice to {em}")
        except Exception as e:
            logging.error(f"Error processing confirmed order {order}: {e}\n{traceback.format_exc()}")

    return processed


def main():
    print("=" * 60)
    print("Opt-In Email Sample Generator -- Starting Up")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Checking configuration...")

    try:
        validate_config()
        print("Configuration valid")
    except EnvironmentError as e:
        print(f"Configuration error: {e}")
        return

    print("Starting main loop (runs every 30 minutes). Press Ctrl+C to stop.\n")

    cycle = 0
    while True:
        cycle += 1
        print(f"\n--- Cycle {cycle} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

        try:
            sent = process_new_signups()
            print(f"  Sent sample emails to {sent} new signup(s)" if sent else "  No new signups")
        except Exception as e:
            logging.error(f"Error in process_new_signups: {e}\n{traceback.format_exc()}")
            print("  Error processing signups (see errors.log)")

        try:
            new_orders = check_replies()
            if new_orders:
                print(f"  Detected {len(new_orders)} new order intent(s)")
                for o in new_orders:
                    print(f"    - {o['email']} ({o['business_name']}) -> pending_invoice")
            else:
                print("  No new replies with purchase intent")
        except Exception as e:
            logging.error(f"Error in check_replies: {e}\n{traceback.format_exc()}")
            print("  Error checking replies (see errors.log)")

        try:
            delivered = process_confirmed_orders()
            print(f"  Delivered {delivered} campaign invoice(s)" if delivered else "  No confirmed orders")
        except Exception as e:
            logging.error(f"Error in process_confirmed_orders: {e}\n{traceback.format_exc()}")
            print("  Error processing orders (see errors.log)")

        print(f"--- Cycle {cycle} complete. Sleeping 30 minutes... ---")
        try:
            time.sleep(1800)
        except KeyboardInterrupt:
            print("\nShutdown requested. Exiting gracefully.")
            break


if __name__ == "__main__":
    main()
