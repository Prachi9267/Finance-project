from flask import Flask, render_template, request
from analyzer import analyze_statement
from pypdf import PdfReader
from pypdf import PdfWriter
import os
import sys

if not os.environ.get("JAVA_HOME"):
    nix_java_path = "/nix/var/nix/profiles/default"
    os.environ["JAVA_HOME"] = nix_java_path

    os.environ["PATH"] = f"{nix_java_path}/bin:{os.environ.get('PATH', '')}"

os.environ["LD_LIBRARY_PATH"] = (
    "/nix/var/nix/profiles/default/lib/server:"
    "/nix/var/nix/profiles/default/lib/openjdk/lib/server:"
    f"{os.environ.get('LD_LIBRARY_PATH', '')}"
)

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():

    if "pdf" not in request.files:
        return "No PDF uploaded"

    file = request.files["pdf"]

    if file.filename == "":
        return "No file selected"

    pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)

    file.save(pdf_path)
    password = request.form.get("pdf_password", "")

    pdf_to_analyze = pdf_path
    if password:
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(pdf_path)
        if reader.is_encrypted:
            reader.decrypt(password)
            unlocked_pdf = pdf_path.replace(".pdf", "_unlocked.pdf")
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)
            with open(unlocked_pdf, "wb") as f:
                writer.write(f)
            pdf_to_analyze = unlocked_pdf

    try:
        results = analyze_statement(pdf_to_analyze)

        return render_template("results.html", results=results)

    except Exception as e:
        return f"""
        <h2>Error</h2>
        <p>{str(e)}</p>
        """


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    app.run(host="0.0.0.0", port=port)
