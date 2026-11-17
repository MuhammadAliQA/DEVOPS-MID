"""Explicit single-host release/rollback; no schema reversal or volume deletion.

Run on the deployment host: python deploy/release.py --image ghcr.io/org/repo@sha256:...
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
IMAGE = re.compile(r'^ghcr\.io/[a-z0-9._/-]+@sha256:[a-f0-9]{64}$')


def compose(env_file, image):
    if not IMAGE.fullmatch(image): raise ValueError('Use the immutable GHCR image digest produced by the release workflow.')
    if not env_file.is_file(): raise ValueError('Production environment file is missing.')
    return ['docker', 'compose', '--env-file', str(env_file), '-f', str(ROOT / 'compose.production.yaml')], {**os.environ, 'APP_IMAGE': image}


def run(command, env, **kwargs):
    return subprocess.run(command, env=env, check=True, **kwargs)


def backup(command, env, directory):
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    # Binary files use Python file handles, never PowerShell redirection.
    with (directory / 'database.dump').open('wb') as output:
        run(command + ['exec', '-T', 'db', 'pg_dump', '-U', 'ticketflow', '-d', 'ticketflow', '-Fc'], env, stdout=output)
    with (directory / 'uploads.tar.gz').open('wb') as output:
        run(command + ['run', '--rm', '--no-deps', '-T', 'web', 'tar', '-czf', '-', '-C', '/app/uploads', '.'], env, stdout=output)
    # Validate archive readability; a full restore drill is a separate command.
    with (directory / 'database.dump').open('rb') as source:
        run(command + ['exec', '-T', 'db', 'pg_restore', '--list'], env, stdin=source, stdout=subprocess.DEVNULL)
    print('Backup saved:', directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--image')
    choice.add_argument('--rollback', action='store_true', help='Use previous image; retains current database schema.')
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env.production')
    parser.add_argument('--verify-url', help='Optional public HTTPS readiness URL; failure fails the release.')
    args = parser.parse_args()
    state_path = ROOT / 'release-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    image = state.get('previous') if args.rollback else args.image
    if not image: parser.error('Supply --image, or --rollback after a recorded successful release.')
    command, env = compose(args.env_file.resolve(), image)
    if args.verify_url and not args.verify_url.startswith('https://'): parser.error('--verify-url must use HTTPS.')
    lock = ROOT / '.release.lock'
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    stopped = False
    try:
        run(command + ['config', '--quiet'], env)
        run(command + ['pull', 'web', 'payment', 'expiry-worker', 'db', 'cache', 'proxy'], env)
        run(command + ['up', '-d', '--wait', '--wait-timeout', '120', 'db', 'cache'], env)
        # A short maintenance window prevents writes during backup + schema upgrade.
        run(command + ['stop', 'web', 'expiry-worker'], env)
        stopped = True
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup(command, env, ROOT / 'backups' / stamp)
        if not args.rollback:
            run(command + ['run', '--rm', 'migrate'], env)
            run(command + ['run', '--rm', '--no-deps', 'web', 'python', 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'], env)
        run(command + ['up', '-d', '--wait', '--wait-timeout', '180', 'web', 'payment', 'expiry-worker', 'proxy'], env)
        if args.verify_url:
            with urlopen(args.verify_url, timeout=20) as response:
                if response.status != 200: raise RuntimeError('Public readiness failed')
        new_state = {'current': image, 'previous': state.get('current'), 'released_at': stamp, 'backup': str(ROOT / 'backups' / stamp)}
        temporary = state_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(new_state, indent=2), encoding='utf-8')
        temporary.replace(state_path)
        print('Release healthy:', image)
    except Exception:
        print('Release failed. No database rollback was attempted. Inspect logs and schema compatibility before recovery.', file=sys.stderr)
        if stopped: print('Web/worker may be stopped or unhealthy. See deploy/README.md recovery procedure.', file=sys.stderr)
        raise
    finally:
        lock.unlink()


if __name__ == '__main__': main()
