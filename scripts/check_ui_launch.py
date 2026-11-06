#!/usr/bin/env python3
"""Check local Streamlit health and initial application rendering; stop the server."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='NEW directory for launch logs')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    os.chdir(ROOT)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    argv = [sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'app/streamlit_app.py'),
            '--server.address', '127.0.0.1', '--server.headless', 'true',
            '--browser.gatherUsageStats', 'false', '--server.port', str(port)]
    report = dict(command=argv, cwd=str(ROOT), port=port, status='failed',
                  scope='Health endpoint plus Streamlit AppTest initial render; no new browser upload/download check.')
    with (output / 'server.txt').open('w') as log:
        process = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('Streamlit exited before becoming healthy')
                try:
                    with urlopen(f'http://127.0.0.1:{port}/_stcore/health', timeout=1) as response:
                        if response.status == 200 and response.read() == b'ok':
                            report['health'] = 'HTTP 200 ok'
                            break
                except OSError:
                    pass
                time.sleep(.1)
            else:
                raise RuntimeError('Streamlit health check timed out')
            from streamlit.testing.v1 import AppTest
            app = AppTest.from_file(str(ROOT / 'app/streamlit_app.py')).run(timeout=30)
            if app.exception:
                raise RuntimeError(str(app.exception))
            if app.selectbox(key='profile_category').value != 'Unknown':
                raise RuntimeError('Initial category applicability was not Unknown')
            report.update(status='passed', initial_app_render='passed', category='Unknown')
        except Exception as exc:
            report['error'] = f'{type(exc).__name__}: {exc}'
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            report['server_stopped'] = process.poll() is not None
    (output / 'launch.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    raise SystemExit(0 if report['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
