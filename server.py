from flask import Flask, request, jsonify
import csv
import os

app = Flask(_name_, static_folder=".")

@app.route("/")
def home():
    return app.send_static_file("index.html")  # nayi dark blue website

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

if _name_ == "_main_":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
