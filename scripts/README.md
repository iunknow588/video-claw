Normalize text files script

Usage:

From project root or scripts folder run:

```powershell
python scripts\normalize_text_files.py --root . --dry-run
python scripts\normalize_text_files.py --root . --fix
```

Notes:
- Script will skip binary files and common asset directories (`.git`, `runtime`, `node_modules`, `venv`, `__pycache__`).
- If `chardet` is installed it will improve encoding detection; otherwise the script falls back to UTF-8/latin-1 heuristics.
- Always run with `--dry-run` first to review changes before `--fix`.
