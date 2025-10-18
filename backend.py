# backend.py
from flask import Flask, request, jsonify
import whisper
import google.generativeai as genai
import tempfile
import smtplib
from email.message import EmailMessage
import os

# ---------- CONFIG ----------
GEMINI_API_KEY = "AIzaSyBxHQro_i4Lh0V1Yf4bUIDkM6wwlxjB60Y"
genai.configure(api_key=GEMINI_API_KEY)

EMAIL_ADDRESS = "shivamagain25@gmail.com"
EMAIL_PASSWORD = "kstm bzmn xxyd vjpu"  # use app password if using Gmail

# ---------- Initialize ----------
app = Flask(__name__)
model = whisper.load_model("base")  # Load once, reuse

# ---------- HELPER FUNCTIONS ----------
def transcribe_with_whisper(audio_file_path):
    result = model.transcribe(audio_file_path, task='transcribe')
    return result["text"]

def analyze_with_gemini(transcript):
    model_g = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"""
You are a classroom summarizer AI.

Here is a transcript of a class:

{transcript}

Please extract the following:
1. Topic taught
2. Subtopics taught
3. Activities by the teacher
4. Summary of the class (2-3 paragraphs)
5. Homework assigned (if any)
6. Important bullet points
7. Relevance of explanations to the topic
8. Any irregularities or problems in teaching

Respond clearly and well-formatted.
"""
    response = model_g.generate_content(prompt)
    return response.text

def send_email(to_address, subject, body, attachment_path=None):
    msg = EmailMessage()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_address
    msg['Subject'] = subject
    msg.set_content(body)

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as f:
            file_data = f.read()
            file_name = os.path.basename(attachment_path)
        msg.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=file_name)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

def save_report(metadata, content, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for key, value in metadata.items():
            f.write(f"{key}: {value}\n")
        f.write("\n")
        f.write(content)

# ---------- API ROUTE ----------
@app.route('/process_class', methods=['POST'])
def process_class():
    try:
        # ---------- Receive audio + metadata ----------
        audio_file = request.files.get('audio_file')
        if not audio_file:
            return jsonify({"error": "No audio file provided"}), 400

        teacher_name = request.form.get('teacher_name', '')
        period_number = request.form.get('period_number', '')
        subject = request.form.get('subject', '')
        start_time = request.form.get('start_time', '')
        grade = request.form.get('grade', '')
        section = request.form.get('section', '')
        email_to = request.form.get('email', '')

        metadata = {
            "Teacher Name": teacher_name,
            "Period Number": period_number,
            "Subject": subject,
            "Start Time": start_time,
            "Class": grade,
            "Section": section
        }

        # ---------- Save audio temporarily ----------
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            audio_file.save(tmp.name)
            audio_path = tmp.name

        # ---------- Transcribe ----------
        transcript = transcribe_with_whisper(audio_path)
        transcript_file = f"{teacher_name}_transcript.txt"
        save_report(metadata, transcript, transcript_file)

        # ---------- Gemini analysis ----------
        report = analyze_with_gemini(transcript)
        report_file = f"{teacher_name}_class_report.txt"
        save_report(metadata, report, report_file)

        # ---------- Send email ----------
        email_subject = f"Class Report for {subject} - {teacher_name}"
        email_body = f"Dear {teacher_name},\n\nPlease find attached the class report.\n\nRegards,\nClass Data System"
        send_email(email_to, email_subject, email_body, report_file)

        # Clean up temporary audio
        os.remove(audio_path)

        return jsonify({"status": "success", "message": "Report generated and emailed successfully!"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ---------- RUN ----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
