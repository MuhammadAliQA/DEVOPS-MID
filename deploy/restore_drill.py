"""Restore a dump into a temporary database, validate core invariants, then drop ONLY that test DB."""
import argparse
import os
from pathlib import Path
import subprocess
import uuid
from release import ROOT, compose, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump', type=Path)
    parser.add_argument('--image', required=True)
    parser.add_argument('--env-file', type=Path, default=ROOT / '.env.production')
    args = parser.parse_args()
    command, env = compose(args.env_file.resolve(), args.image)
    name = 'restore_drill_' + uuid.uuid4().hex
    db = command + ['exec', '-T', 'db']
    run(db + ['createdb', '-U', 'ticketflow', name], env)
    try:
        with args.dump.open('rb') as source:
            run(db + ['pg_restore', '-U', 'ticketflow', '--no-owner', '--no-acl', '--exit-on-error', '-d', name], env, stdin=source)
        query = """SELECT
          (SELECT count(*) FROM booking_booking b WHERE b.status='paid' AND NOT EXISTS (SELECT 1 FROM booking_payment p WHERE p.booking_id=b.id AND p.amount=b.total)) +
          (SELECT count(*) FROM booking_bookingseat i JOIN booking_booking b ON b.id=i.booking_id WHERE b.status='paid' AND NOT EXISTS (SELECT 1 FROM booking_ticket t WHERE t.item_id=i.id)) +
          (SELECT count(*) FROM booking_seat s JOIN booking_booking b ON b.id=s.reservation_id WHERE b.status NOT IN ('held','paid'));
        """
        result = run(db + ['psql', '-U', 'ticketflow', '-d', name, '-At', '-v', 'ON_ERROR_STOP=1', '-c', query], env, capture_output=True, text=True)
        if result.stdout.strip() != '0': raise RuntimeError('Restored booking/payment/seat invariants failed.')
        print('Isolated restore and invariants: PASS')
    finally:
        run(db + ['dropdb', '-U', 'ticketflow', name], env)


if __name__ == '__main__': main()
