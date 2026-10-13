from PyPDF2 import PdfReader

reader = PdfReader(r'c:\odoo-dev\odoo19\test_quotation.pdf')
print(f'Number of pages: {len(reader.pages)}')

all_text = ''
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    all_text += f'\n--- Page {i+1} ---\n'
    all_text += text

# Search for ISO footer
if 'FM-XX-001' in all_text:
    print('\nSUCCESS: FM-XX-001 found in PDF!')
    # Count occurrences
    count = all_text.count('FM-XX-001')
    print(f'  Occurrences: {count}')
    if count >= 2:
        print('  Both bottom-left and bottom-right corners have the ISO number.')
else:
    print('\nWARNING: FM-XX-001 NOT found in PDF text')

if 'Rev.00' in all_text or 'Rev' in all_text:
    print('SUCCESS: Revision found in PDF')

# Show the bottom portion of the text (footer area)
print('\n--- Last 500 chars of PDF text ---')
print(all_text[-500:])
