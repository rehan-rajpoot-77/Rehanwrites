from flask import Flask, request, jsonify
import csv
import os

app = Flask(__name__, static_folder=".")

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

if __name__ == "__main__":
    app.run(port=5000)
