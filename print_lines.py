from pathlib import Path
text = Path('desktop/flutter_agentgpt/lib/views/main_layout.dart').read_text().splitlines()
for i in range(140, 170):
    print(f"{i+1}: {text[i]}")
