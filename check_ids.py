import re

with open('web/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html_ids = set(re.findall(r'id="([^"]+)"', html))

js_expected = ['user-input', 'send-btn', 'chat-messages', 'model-select', 'model-name',
    'ram-usage', 'token-count', 'response-time', 'status-indicator', 'status-text',
    'version-info', 'cost-info', 'loading-overlay', 'typing-indicator', 'clear-btn', 'performance-chart']

missing = [i for i in js_expected if i not in html_ids]
print(f'IDs faltando: {len(missing)}')
for m in missing:
    print(f'  - {m}')

present = [i for i in js_expected if i in html_ids]
print(f'Presentes: {len(present)}/{len(js_expected)}')
