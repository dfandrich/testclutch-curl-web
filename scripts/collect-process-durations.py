#!/usr/bin/env python3
"""Collect Test Clutch job run times from the journal logs.

They are written in CSV format for easy graphing.
"""

import functools
import multiprocessing
import os
import subprocess
import sys


DEBUG = False

PR_REGEX = r'^(Starting|Completed|Aborted) PR analysis'
DAILY_REGEX = r'^(Starting|Completed|Aborted|Aborting) daily update'
ALL_REGEX = f'({PR_REGEX})|({DAILY_REGEX})'

# This is the Python character map in which the logs are assumed. If any errors are encountered
# during decoding (such as if a binary file was displayed in a log dump), they will automatically
# be replaced with backslash escapes in the popen call.
LOG_CHARMAP = 'UTF-8'

# Largest possible job duration. Anything larger is an error.
MAX_DURATION = 24 * 3600


def process_log(regex: str, fn: str) -> list:
    proc = subprocess.Popen(
        ['journalctl', '-o', 'export', '-g', regex, '--file', fn],
        stdout=subprocess.PIPE,
        encoding=LOG_CHARMAP,
        errors='backslashreplace',
        text=True,
        shell=False
    )

    results = []
    message = ''
    timestamp = 0
    session = -1
    assert proc.stdout  # satisfy pytype
    while line := proc.stdout.readline():
        line = line.strip()
        if not line:
            # end of log entry
            if not timestamp or session < 0:
                print('invalid entry:', timestamp, session, message, file=sys.stderr)
            else:
                results.append((timestamp, session, message))
            message = ''
            timestamp = 0
            session = -1
        else:
            field, value = line.split('=', 1)
            if field == '__REALTIME_TIMESTAMP':
                timestamp = float(value) / 1e6
            elif field == '_AUDIT_SESSION':
                # Oddly, on occasion journald drops this field causing the later session check to
                # to log an invalid or mismatched entry error.
                session = int(value)
            elif field == 'MESSAGE':
                message = value
    proc.wait()
    return results


def analyze(times: list):
    lastsess = -1
    lasttime = 0
    for timestamp, session, message in times:
        if session == lastsess:
            if 'Completed' in message or 'Abort' in message:
                duration = timestamp - lasttime
                if duration > MAX_DURATION:
                    # sanity check failed
                    print('duration too long:', timestamp, session, message, file=sys.stderr)
                    continue
                if 'PR analysis' in message:
                    print(f'{timestamp},,,{duration:.1f}')
                elif 'Abort' in message:
                    # update
                    print(f'{timestamp},,{duration:.1f},,')
                else:
                    # update
                    print(f'{timestamp},{duration:.1f},,')

                lastsess = -1
                lasttime = 0
            elif timestamp == lasttime:
                # probably duplicated log files and two Starts in a row
                print('probable duplicate:', timestamp, session, message, file=sys.stderr)
            else:
                print('session mismatch:', timestamp, session, message, file=sys.stderr)
        elif 'Start' in message:
            lastsess = session
            lasttime = timestamp
        else:
            # mismatched log entry (probably start of log file and missing "Start")
            print('mismatched entry:', timestamp, session, message, file=sys.stderr)


def main():
    with multiprocessing.Pool(processes=2 * len(os.sched_getaffinity(0))) as pool:
        logresults = pool.imap_unordered(functools.partial(process_log, ALL_REGEX), sys.argv[1:])
        # flatten the results into a single list
        times = [log for res in logresults for log in res]

    # sort by session then time
    times.sort(key=lambda x: (x[1], x[0]))
    analyze(times)
    if DEBUG:
        for timestamp, session, message in times:
            print(f'{timestamp}\t{session}\t{message}')


if __name__ == '__main__':
    main()
