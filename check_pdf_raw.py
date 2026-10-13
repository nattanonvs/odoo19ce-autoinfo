# Check raw PDF bytes for FM-XX-001
with open(r'c:\odoo-dev\odoo19\test_quotation.pdf', 'rb') as f:
    data = f.read()

# Search for the text in raw bytes
search = b'FM-XX-001'
count = data.count(search)
print(f'FM-XX-001 found {count} times in raw PDF bytes')

if count > 0:
    # Show context around each occurrence
    idx = 0
    for i in range(count):
        idx = data.find(search, idx)
        start = max(0, idx - 50)
        end = min(len(data), idx + 80)
        context = data[start:end]
        # Try to decode as latin-1 for display
        print(f'\n--- Occurrence {i+1} at byte {idx} ---')
        print(context.decode('latin-1', errors='replace'))
        idx += 1
else:
    print('FM-XX-001 NOT found in PDF. Checking if footer injection works...')
    # Check for Rev.00 too
    rev_count = data.count(b'Rev.00')
    print(f'Rev.00 found {rev_count} times')

# Also check the page count and structure
print(f'\nPDF size: {len(data)} bytes')
print(f'PDF header: {data[:20]}')
