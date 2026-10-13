import PyPDF2
reader = PyPDF2.PdfReader(r'c:\odoo-dev\odoo19\test_footer_output.pdf')
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    print(f"=== Page {i+1} ===")
    print(text)
    print()
