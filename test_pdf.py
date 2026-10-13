import json
import urllib.request
import http.cookiejar

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

# Authenticate
url = 'http://localhost:8070/web/session/authenticate'
data = {
    'jsonrpc': '2.0',
    'method': 'call',
    'params': {
        'db': 'odoo19',
        'login': 'admin',
        'password': 'admin'
    },
    'id': 1
}

req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'})
response = opener.open(req)
result = json.loads(response.read())
print('Auth uid:', result.get('result', {}).get('uid'))

# Download PDF
pdf_url = 'http://localhost:8070/report/pdf/sale.report_saleorder/895'
pdf_req = urllib.request.Request(pdf_url)
try:
    pdf_response = opener.open(pdf_req)
    pdf_data = pdf_response.read()
    out_path = r'c:\odoo-dev\odoo19\test_quotation.pdf'
    with open(out_path, 'wb') as f:
        f.write(pdf_data)
    print(f'PDF saved to {out_path}, size={len(pdf_data)} bytes')
    print(f'Content-Type: {pdf_response.headers.get("Content-Type")}')
    if pdf_data[:5] == b'%PDF-':
        print('SUCCESS: Valid PDF file generated!')
    else:
        print('WARNING: Not a valid PDF')
except urllib.error.HTTPError as e:
    print(f'HTTP Error {e.code}: {e.reason}')
    body = e.read().decode('utf-8', errors='replace')
    # Extract error message
    if 'Error message' in body:
        start = body.find('Error message')
        print(body[start:start+500])
    else:
        print(body[:500])
