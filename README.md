# Opt-In Email Sample Generator

A consent-based freelance email-copywriting tool. No scraping, no bulk
cold email, no payment-before-delivery. Free samples first, payment only
after the client confirms they want the full campaign.

## Files
- `config.py` — settings, reads API keys from environment variables
- `utils.py` — AI content generation, email sending, reply checking, PDF invoices
- `main.py` — orchestrator loop (run this)
- `landing.html` — the signup page
- `requirements.txt` — Python dependencies

## Setup

### 1. Install dependencies
```
pip install -r requirements.txt
```

### 2. Set environment variables
```
export GROQ_API_KEY="gsk_..."        # or OPENAI_API_KEY="sk-..."
export GMAIL_ADDRESS="youremail@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
```
Get a Gmail App Password: Google Account → Security → 2-Step
Verification → App passwords. Do NOT use your normal Gmail password.

### 3. Connect the landing page to the system
`landing.html` currently posts to `/submit`, which doesn't exist yet —
you need a tiny backend (Flask is easiest) that takes the form data and
appends a row to `landing_page_submissions.csv` with columns:
`name, email, business_name, niche`

Minimal Flask example (save as `server.py` next to the other files):
```python
from flask import Flask, request, jsonify
import csv, os

app = Flask(__name__, static_folder=".")

@app.route("/")
def home():
    return app.send_static_file("landing.html")

@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()
    file_exists = os.path.exists("landing_page_submissions.csv")
    with open("landing_page_submissions.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "email", "business_name", "niche"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(port=5000)
```
Run it with `python server.py`, then visit `http://localhost:5000`.

### 4. Run the orchestrator
```
python main.py
```
It loops every 30 minutes: sends free samples to new signups, checks
your inbox for replies, and delivers invoices for confirmed orders.

## Workflow
1. Visitor fills the landing page form → saved to `landing_page_submissions.csv`
2. `main.py` sends them 3 free sample emails automatically
3. If they reply "interested" → logged to `orders.csv` as `pending_invoice`
4. **You manually review and change status to `confirmed`** in `orders.csv`
   (this human step is intentional — never auto-charge someone)
5. Next cycle: full 30-email campaign + PDF invoice generated and sent,
   status updates to `delivered`
6. Client pays via the link in the invoice email (replace `PAYMENT_LINK_HERE`
   with your real PayPal/Stripe link in `utils.py`)

## Ethical safeguards built in
- Only ever emails addresses that filled out the form themselves
- Free value (3 samples) delivered before any sales conversation
- Invoice/payment only sent after you manually confirm the order
- Rate-limited to 20 emails/hour to protect your Gmail account
- No fake urgency, countdowns, or pressure language anywhere
- All errors logged to `errors.log`, loop never crashes

## Before going live
- Replace `youremail@gmail.com` in `landing.html` with your real address
- Replace `PAYMENT_LINK_HERE` in `utils.py` (`send_invoice` function)
  with your actual PayPal.me or Stripe payment link
- Test the whole flow yourself first (sign up on your own form, confirm
  you receive samples, reply "interested", manually confirm, check you
  receive the invoice) before sharing the page publicly
