"""Wait for actual Compose health, never infer success from a valid YAML file."""
import json
import subprocess
import time

required = {'db', 'cache', 'web', 'payment', 'expiry-worker'}
deadline = time.monotonic() + 180
while time.monotonic() < deadline:
    output = subprocess.check_output(['docker', 'compose', 'ps', '--all', '--format', 'json'], text=True).strip()
    records = json.loads(output) if output.startswith('[') else [json.loads(line) for line in output.splitlines() if line]
    statuses = {record['Service']: record for record in records}
    migration = statuses.get('migrate')
    if migration and migration.get('State') == 'exited' and int(migration.get('ExitCode', 0)) != 0:
        raise SystemExit('Migration service failed.')
    healthy = all(statuses.get(name, {}).get('Health') == 'healthy' for name in required)
    migrated = migration and migration.get('State') == 'exited' and int(migration.get('ExitCode', 1)) == 0
    if healthy and migrated:
        print('PASS: PostgreSQL, Redis, web, payment, expiry heartbeat and migration job')
        break
    time.sleep(2)
else:
    raise SystemExit('Compose health did not converge within 180 seconds.')
