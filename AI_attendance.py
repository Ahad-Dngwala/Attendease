from flask import Flask, request, jsonify, send_file, render_template_string
from google.cloud import vision
import os
from flask_cors import CORS
import re
import csv
from io import StringIO
import toastify

app = Flask(__name__)
CORS(app)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"First Hackathon\Google_ocr\service-account-file.json"
client = vision.ImageAnnotatorClient()

# Store extracted roll numbers with attendance status
extracted_roll_numbers = {}

@app.route('/')
def serve_frontend():
    return render_template_string("AI_attendance.html")
@app.route('/api/upload', methods=['POST'])
def upload_images():
    if 'files' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({"error": "No files selected"}), 400

    results = []

    for file in files:
        try:
            image_content = file.read()
            if not image_content:
                results.append({"file": file.filename, "error": "Empty file uploaded"})
                continue

            image = vision.Image(content=image_content)
            response = client.text_detection(image=image)
            texts = response.text_annotations

            if not texts:
                results.append({"file": file.filename, "error": "No text detected"})
                continue

            extracted_text = texts[0].description
            cleaned_text = re.sub(r"[^0-9, ]", "", extracted_text)
            cleaned_text = ", ".join(set(cleaned_text.split()))
            for num in cleaned_text.split(", "):
                extracted_roll_numbers[num] = "Present"

            results.append({"file": file.filename, "text": cleaned_text})

        except Exception as e:
            results.append({"file": file.filename, "error": str(e)})

    return jsonify({"results": results, "attendance": extracted_roll_numbers})

@app.route('/api/mark_present', methods=['POST'])
def mark_present():
    data = request.json
    roll_number = data.get("roll_number")
    if roll_number in extracted_roll_numbers:
        extracted_roll_numbers[roll_number] = "Present"
        return jsonify({"success": True, "message": f"Roll number {roll_number} marked as Present"})
    return jsonify({"success": False, "message": "Roll number not found"}), 400

@app.route('/api/export', methods=['GET'])
def export_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Roll Number", "Status"])
    for number, status in sorted(extracted_roll_numbers.items()):
        writer.writerow([number, status])
    output.seek(0)
    return send_file(StringIO(output.getvalue()), mimetype="text/csv", as_attachment=True, download_name="attendance.csv")

if __name__ == '__main__':
    app.run(debug=True, port=5500)
