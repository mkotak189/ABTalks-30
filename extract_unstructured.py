import pdfplumber
import docx
import pytesseract
from pdf2image import convert_from_path
import re
import os

os.makedirs("raw_text", exist_ok=True)

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)  # collapse whitespace
    text = text.strip()
    return text

# --- Benefits PDF ---
with pdfplumber.open("sample_docs/benefits.pdf") as pdf:
    benefits_text = ""
    for page in pdf.pages:
        benefits_text += page.extract_text() + "\n"
benefits_text = clean_text(benefits_text)
with open("raw_text/benefits.txt", "w", encoding="utf-8") as f:
    f.write(benefits_text)
print("Saved raw_text/benefits.txt")

# --- Claims process Word doc ---
doc = docx.Document("sample_docs/claims_process.docx")
claims_text = "\n".join(p.text for p in doc.paragraphs)
claims_text = clean_text(claims_text)
with open("raw_text/claims_process.txt", "w", encoding="utf-8") as f:
    f.write(claims_text)
print("Saved raw_text/claims_process.txt")

# --- Enrollment scan (OCR) ---
images = convert_from_path("sample_docs/enrollment_scan.pdf")
enrollment_text = ""
for i, image in enumerate(images):
    enrollment_text += f"Page {i+1}:\n"
    enrollment_text += pytesseract.image_to_string(image)
    enrollment_text += "\n"
enrollment_text = clean_text(enrollment_text)
with open("raw_text/enrollment.txt", "w", encoding="utf-8") as f:
    f.write(enrollment_text)
print("Saved raw_text/enrollment.txt")