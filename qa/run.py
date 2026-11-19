"""Run isolated Playwright journeys and emit JSON/HTML reports, screenshots, traces."""
import argparse
import html
import importlib.metadata
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class ReportResult(unittest.TextTestResult):
    records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({'test': test.id(), 'status': 'passed'})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({'test': test.id(), 'status': 'failed', 'error': self._exc_info_to_string(err, test)})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({'test': test.id(), 'status': 'error', 'error': self._exc_info_to_string(err, test)})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records.append({'test': test.id(), 'status': 'skipped', 'reason': reason})

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.records.append({'test': subtest.id(), 'status': 'failed', 'error': self._exc_info_to_string(err, test)})


def wait_ready(url, process):
    for _ in range(80):
        if process.poll() is not None:
            raise RuntimeError(f'Server exited before readiness: {url}')
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(.25)
    raise RuntimeError(f'Readiness timeout: {url}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], default='chromium')
    parser.add_argument('--test', help='Optional unittest method name, e.g. test_payment_and_ticket_journey')
    args = parser.parse_args()
    output = ROOT / '.tmp' / 'qa' / (time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(2))
    output.mkdir(parents=True)
    os.environ.update({
        'TICKETFLOW_QA_DIR': str(output), 'DJANGO_SETTINGS_MODULE': 'config.qa_settings',
        'DEBUG': '1', 'SECRET_KEY': secrets.token_urlsafe(50), 'PAYMENT_SECRET': secrets.token_urlsafe(32),
        'PAYMENT_URL': 'http://127.0.0.1:8991',
    })
    report = {'status': 'blocked', 'tests': [], 'browser': args.browser,
              'database': 'isolated SQLite', 'artifacts': str(output), 'versions': {}}
    for name in ['Django', 'playwright', 'qrcode', 'opencv-python', 'whitenoise']:
        try:
            report['versions'][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            report['versions'][name] = 'not installed'
    processes, streams = [], []
    browser = playwright = None
    code = 2
    try:
        import django
        django.setup()
        from django.core.management import call_command
        from playwright.sync_api import sync_playwright
        # Fail as BLOCKED before any test setup if browser startup is unavailable.
        playwright = sync_playwright().start()
        browser = getattr(playwright, args.browser).launch(headless=True, **({'executable_path': os.environ['QA_BROWSER_PATH'], 'args': ['--no-sandbox', '--disable-dev-shm-usage']} if os.environ.get('QA_BROWSER_PATH') else {}))
        def prepare_database():
            from django.db import close_old_connections
            call_command('migrate', verbosity=0)
            call_command('setup_roles', verbosity=0)
            close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(prepare_database).result(timeout=90)
        for label, port, settings_module in [('web', 8990, 'config.qa_settings'), ('payment', 8991, 'payment_service.settings')]:
            log = (output / f'{label}.log').open('w', encoding='utf-8')
            streams.append(log)
            command = [sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload', '--settings=' + settings_module]
            process = subprocess.Popen(command, cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            processes.append(process)
            wait_ready(f'http://127.0.0.1:{port}/health/live/', process)
        from qa.test_journeys import TicketFlowJourneys
        TicketFlowJourneys.browser = browser
        TicketFlowJourneys.output = output
        suite = (unittest.defaultTestLoader.loadTestsFromName(args.test, TicketFlowJourneys)
                 if args.test else unittest.defaultTestLoader.loadTestsFromTestCase(TicketFlowJourneys))
        ReportResult.records = []
        result = unittest.TextTestRunner(verbosity=2, resultclass=ReportResult).run(suite)
        report.update(status='passed' if result.wasSuccessful() else 'failed', tests=result.records,
                      executed=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped))
        code = 0 if result.wasSuccessful() else 1
    except Exception as exc:
        import traceback
        report.update(status='blocked', error=f'{type(exc).__name__}: {exc}', traceback=traceback.format_exc())
        print('QA BLOCKED:', report['error'], file=sys.stderr)
    finally:
        if browser:
            browser.close()
        if playwright:
            playwright.stop()
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for stream in streams:
            stream.close()
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        rows = ''.join(f'<tr><td>{html.escape(item["test"])}</td><td>{item["status"]}</td></tr>' for item in report['tests'])
        page = ('<!doctype html><html><meta charset="utf-8"><title>TicketFlow QA</title>'
                '<style>body{font:15px/1.6 system-ui;max-width:1100px;margin:50px auto;padding:20px}table{border-collapse:collapse;width:100%}td{padding:12px;border-bottom:1px solid #ddd}pre{white-space:pre-wrap}a{color:#2853e8}</style>'
                f'<h1>TicketFlow QA — {report["status"].upper()}</h1><p>Browser: {args.browser} · Isolated SQLite</p>'
                f'<pre>{html.escape(report.get("error", ""))}</pre><table>{rows}</table>'
                '<p><a href="report.json">Full JSON report</a> · Screenshots and traces are stored alongside this report.</p></html>')
        (output / 'report.html').write_text(page, encoding='utf-8')
        latest = ROOT / '.tmp' / 'qa' / 'latest.json'
        latest.write_text(json.dumps({'report': str(output / 'report.json'), 'status': report['status']}, indent=2), encoding='utf-8')
        print('QA report:', output / 'report.html')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
