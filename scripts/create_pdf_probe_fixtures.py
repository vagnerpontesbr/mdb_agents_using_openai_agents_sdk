"""Generate two synthetic PDFs and rendered pages for the Phase 0 CPU probe."""

from pathlib import Path
import subprocess

from pypdf import PdfReader
from reportlab.pdfgen import canvas


def main() -> None:
    output = Path("artifacts/compatibility/pdf")
    output.mkdir(parents=True, exist_ok=True)
    text_pdf = output / "text.pdf"
    document = canvas.Canvas(str(text_pdf), pagesize=(612, 792))
    document.setTitle("Synthetic telecom compatibility fixture")
    pages = [
        ("Optical signal procedure", "Check the optical cable before restarting the router."),
        ("Escalation procedure", "Open a support ticket if the red light remains on."),
    ]
    for number, (title, instruction) in enumerate(pages, 1):
        document.setFont("Helvetica-Bold", 18)
        document.drawString(54, 720, title)
        document.setFont("Helvetica", 12)
        document.drawString(54, 682, "Synthetic fixture - no customer data")
        document.drawString(54, 636, instruction)
        document.drawString(54, 54, f"Page {number}")
        document.showPage()
    document.save()
    subprocess.run(["pdftoppm", "-r", "150", "-png", str(text_pdf),
                    str(output / "text")], check=True, timeout=60)
    scanned = canvas.Canvas(str(output / "scanned.pdf"), pagesize=(612, 792))
    for number in (1, 2):
        scanned.drawImage(str(output / f"text-{number}.png"), 0, 0, 612, 792)
        scanned.showPage()
    scanned.save()
    assert all(not page.extract_text().strip()
               for page in PdfReader(output / "scanned.pdf").pages)
    subprocess.run(["pdftoppm", "-r", "100", "-png", str(output / "scanned.pdf"),
                    str(output / "scanned")], check=True, timeout=60)
    print("Created two two-page PDFs; scanned fixture has no embedded text.")


if __name__ == "__main__":
    main()
