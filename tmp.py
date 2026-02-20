from pathlib import Path
text=Path('desktop/flutter_agentgpt/lib/views/project_home.dart').read_text(encoding='utf-8')
print(text[:400])
