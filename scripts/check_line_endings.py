#!/usr/bin/env python3
from pathlib import Path
import sys

files = [
    'README_P0_Implementation.md',
    'ROADMAP_P0_P3.md',
    'deploy/alertmanager.yml',
    'deploy/docker-compose.yml',
    'deploy/prometheus.yml',
    'deploy/workflow_alerts.yml',
    'scripts/run_local.cmd',
]

root = Path('.')
print('Checking files for CRLF and BOM')
for f in files:
    p = root / f
    if not p.exists():
        print(f"MISSING: {f}")
        continue
    data = p.read_bytes()
    has_bom = data.startswith(b"\xef\xbb\xbf")
    has_crlf = b'\r\n' in data
    has_lf = b'\n' in data
    print(f"{f}: BOM={has_bom}, CRLF_present={has_crlf}, LF_present={has_lf}")
