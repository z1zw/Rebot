import re

path = r'c:\Users\16320\Desktop\Experiments\Agnet\Rebot\desktop\flutter_agentgpt\lib\services\api_service.dart'
with open(path, 'rb') as f:
    raw = f.read()
for enc in ['utf-8', 'utf-8-sig', 'utf-16', 'latin-1']:
    try:
        text = raw.decode(enc)
        print(f"Decoded with {enc}")
        break
    except:
        continue
lines = text.splitlines(keepends=True)

result = []
skip_next = False
for i, line in enumerate(lines):
    if skip_next:
        skip_next = False
        continue
    stripped = line.strip()
    if stripped == ',' and i + 1 < len(lines) and lines[i + 1].strip().startswith('timeout:'):
        continue
    result.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(result)

print(f"Removed {len(lines) - len(result)} lone comma lines")
