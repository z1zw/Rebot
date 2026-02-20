from pathlib import Path
from rebot.tools.fs_tools import _canonical_path
root=Path('.').resolve()
for path in ['../README.md','.rebot/secret.txt']:
    try:
        print('ok', path, _canonical_path(root, path))
    except Exception as exc:
        print('err', path, exc)
