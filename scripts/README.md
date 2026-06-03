Script layout

- `runtime/`
  - `run_local.cmd`
  - `run_local.ps1`
- `git/`
  - `get.cmd`
  - `get.ps1`
  - `commit.cmd`
  - `commit.ps1`
- `text/`
  - `normalize_text_files.py`
  - `check_line_endings.py`

Common commands

```powershell
scripts\runtime\run_local.cmd
python scripts\text\normalize_text_files.py --root . --dry-run
python scripts\text\normalize_text_files.py --root . --fix
```

Notes

- Git scripts read repository remote settings from the repository root `.env`.
- Text scripts skip binary files and common asset directories such as `.git`, `runtime`, `node_modules`, `venv`, and `__pycache__`.
