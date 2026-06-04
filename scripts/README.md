Script layout

- `runtime/`
  - `run_local.cmd`
  - `run_local.ps1`
  - `status_local.cmd`
  - `status_local.ps1`
  - `stop_local.cmd`
  - `stop_local.ps1`
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
scripts\runtime\run_local.cmd -Port 8010
scripts\runtime\run_local.cmd -Reload
scripts\runtime\run_local.cmd status -Port 8010
scripts\runtime\run_local.cmd stop -Port 8010
scripts\runtime\status_local.cmd -Port 8010
scripts\runtime\stop_local.cmd -Port 8010
python scripts\text\normalize_text_files.py --root . --dry-run
python scripts\text\normalize_text_files.py --root . --fix
```

Notes

- `scripts\runtime\run_local.cmd` starts the local service in the current console foreground.
- By default it runs in single-process mode without hot reload, so `Ctrl+C` exits more predictably on Windows.
- Pass `-Reload` only when you want hot reload while editing code.
- If you started it in the current console, stop it with `Ctrl+C`.
- Use `scripts\runtime\run_local.cmd status -Port <port>` to inspect whether the local service is running, which PID owns the port, and whether reload is enabled.
- If the service is still running in another window or as a leftover background process, stop it with `scripts\runtime\run_local.cmd stop -Port <port>` or `scripts\runtime\stop_local.cmd -Port <port>`.
- `run_local.cmd` does not support typing an interactive `exit` command after startup; it forwards to `uvicorn`, so the normal foreground shutdown path is `Ctrl+C`.
- When `-Reload` is enabled, the watcher is limited to `src` and excludes `src/tests/*`.
- Git scripts read repository remote settings from the repository root `.env`.
- Text scripts skip binary files and common asset directories such as `.git`, `runtime`, `node_modules`, `venv`, and `__pycache__`.
