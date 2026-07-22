from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)
API_BASE = "http://localhost:8000"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/cases", methods=["GET"])
def list_cases():
    try:
        resp = requests.get(f"{API_BASE}/cases", timeout=10)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/cases/<case_id>", methods=["GET"])
def get_case(case_id):
    try:
        resp = requests.get(f"{API_BASE}/cases/{case_id}", timeout=10)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/invoices", methods=["POST"])
def submit_invoice():
    payload = request.get_json()
    try:
        resp = requests.post(f"{API_BASE}/invoices", json=payload, timeout=35)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/cases/<case_id>/approve", methods=["POST"])
def approve_case(case_id):
    try:
        resp = requests.post(f"{API_BASE}/cases/{case_id}/approve", timeout=15)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/cases/<case_id>/reject", methods=["POST"])
def reject_case(case_id):
    try:
        resp = requests.post(f"{API_BASE}/cases/{case_id}/reject", timeout=15)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/cases/<case_id>/manual-resolve", methods=["POST"])
def manual_resolve(case_id):
    payload = request.get_json()
    try:
        resp = requests.post(f"{API_BASE}/cases/{case_id}/manual-resolve", json=payload, timeout=15)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502


if __name__ == "__main__":
    app.run(debug=True, port=5000)