from flask import Flask, render_template, request
import pytesseract
from PIL import Image
import io
from pdf2image import convert_from_bytes
from spellchecker import SpellChecker
import re

app = Flask(__name__)

# ✅ Spellchecker object
spell = SpellChecker()

# ✅ Custom accepted words
CUSTOM_WORDS = ["smallpdf", "ocr", "pdf", "html", "pyspellchecker"]
for word in CUSTOM_WORDS:
    spell.word_frequency.add(word.lower())

# ✅ Detect more than 2 spaces between words
def detect_extra_spaces(text):
    results = []
    lines = text.split("\n")

    for line_number, line in enumerate(lines, start=1):
        matches = list(re.finditer(r'\s{2,}', line))

        for m in matches:
            results.append({
                "line": line_number,
                "content": line,
                "spaces_count": len(m.group()),
                "position": m.start() + 1
            })
    return results


# ✅ Word count
def get_total_words(text):
    return len(text.split())


# ✅ Line count
def get_total_lines(text):
    return len(text.split("\n"))


# ✅ Detect spelling errors
def detect_spelling_errors(text):
    errors = []
    words = text.split()

    for word in words:
        cleaned = ''.join(ch for ch in word if ch.isalpha())

        if cleaned:
            lw = cleaned.lower()
            if lw not in CUSTOM_WORDS and not lw.isnumeric():
                if spell.unknown([lw]):
                    suggestion = spell.correction(lw)
                    errors.append({"word": cleaned, "suggestion": suggestion})
    return errors


# ✅ OCR Confidence Score
def get_confidence_score(image):
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    confidences = [int(x) for x in data['conf'] if x != '-1']
    if not confidences:
        return 0
    return round(sum(confidences) / len(confidences), 2)


# ✅ Highlight text
def highlight_text(text, spelling_errors, extra_spaces):
    highlighted = text

    # Highlight spelling errors
    for error in spelling_errors:
        word = error["word"]
        highlighted = re.sub(
            rf'\b{re.escape(word)}\b',
            f'<span class="error-word">{word}</span>',
            highlighted
        )

    # Highlight multiple spaces
    for space in extra_spaces:
        count = space["spaces_count"]
        spaces = " " * count
        highlighted = highlighted.replace(spaces, f'<span class="multiple-space">{spaces}</span>')

    return highlighted


@app.route("/", methods=["GET", "POST"])
def home():
    extracted_text = ""
    extra_spaces_table = []
    spelling_errors = []
    total_words = 0
    total_lines = 0
    confidence = None

    if request.method == "POST":
        file = request.files.get("file")

        if file:
            file_bytes = file.read()
            filename = file.filename.lower()

            try:
                # ✅ PDF Handling
                if filename.endswith(".pdf"):
                    images = convert_from_bytes(file_bytes)
                    img = images[0]     # First page only
                    text = pytesseract.image_to_string(img, config="preserve_interword_spaces=1")
                    confidence = get_confidence_score(img)

                # ✅ Image Handling
                else:
                    img = Image.open(io.BytesIO(file_bytes))
                    text = pytesseract.image_to_string(img, config="preserve_interword_spaces=1")
                    confidence = get_confidence_score(img)

                # ✅ Processing
                extra_spaces_table = detect_extra_spaces(text)
                spelling_errors = detect_spelling_errors(text)
                total_words = get_total_words(text)
                total_lines = get_total_lines(text)

                extracted_text = highlight_text(text, spelling_errors, extra_spaces_table)

            except Exception as e:
                extracted_text = f"Error: {str(e)}"

    return render_template(
        "index.html",
        extracted_text=extracted_text,
        extra_spaces_table=extra_spaces_table,
        spelling_errors=spelling_errors,
        total_words=total_words,
        total_lines=total_lines,
        confidence=confidence
    )


if __name__ == "__main__":
    app.run(debug=True)
    