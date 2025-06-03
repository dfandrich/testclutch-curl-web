#!/usr/bin/env python3
"""Collect Test Clutch job run times from the journal logs.

They are written in CSV format for easy graphing. The time values are in seconds and the fields are:
    time since 1970,job duration,job duration until abort,PR analysis duration,version,# comments
They may not be sorted by time.
"""

import functools
import multiprocessing
import os
import subprocess
import sys


# Dump the raw values at the end
DEBUG = False

# Only log version when it changes
VERSION_CHANGES = True

PR_REGEX = r'^(Starting|Completed|Aborted) PR analysis'
DAILY_REGEX = r'^(Starting|Completed|Aborted|Aborting) daily update'
VERSION_REGEX = r'^version \w+$'
COMMENT_REGEX = r'comment on PR'
ALL_REGEX = f'({PR_REGEX})|({DAILY_REGEX})|({VERSION_REGEX})|({COMMENT_REGEX})'

# This is the Python character map in which the logs are assumed. If any errors are encountered
# during decoding (such as if a binary file was displayed in a log dump), they will automatically
# be replaced with backslash escapes in the popen call.
LOG_CHARMAP = 'UTF-8'

# Largest possible job duration. Anything larger is an error.
MAX_DURATION = 24 * 3600


def process_log(regex: str, fn: str) -> list[tuple[float, int, str]]:
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
    lastversion = ''
    version = ''
    comment = 0
    for timestamp, session, message in times:
        if session == lastsess:
            if 'Completed' in message or 'Abort' in message:
                if VERSION_CHANGES and lastversion == version:
                    # Only write more version numbers when they change
                    version = ''
                duration = timestamp - lasttime
                if duration > MAX_DURATION:
                    # sanity check failed
                    print('duration too long:', timestamp, session, message, file=sys.stderr)
                    continue
                if comment:
                    print(f'{timestamp},,,,,{comment}')
                if 'PR analysis' in message:
                    print(f'{timestamp},,,{duration:.1f},{version},')
                elif 'Abort' in message:
                    # update
                    print(f'{timestamp},,{duration:.1f},,,{version},')

                    # Set lastversion only if we actually have a new version
                    if version:
                        # The new version stop being written only after we've logged a main job
                        lastversion = version
                else:
                    # update
                    print(f'{timestamp},{duration:.1f},,,{version},')

                    # Set lastversion only if we actually have a new version
                    if version:
                        # The new version kicks in only after we've written a main job duration
                        lastversion = version

                lastsess = -1
                lasttime = 0
            elif 'version' in message:
                version = message.split()[1]
            elif 'comment' in message:
                comment += 1
            elif timestamp == lasttime:
                # probably duplicated log files and two Starts in a row
                print('probable duplicate:', timestamp, session, message, file=sys.stderr)
            else:
                print('session mismatch:', timestamp, session, message, file=sys.stderr)
        elif 'Start' in message:
            lastsess = session
            lasttime = timestamp
            version = ''
            comment = 0
        else:
            # mismatched log entry (probably start of log file and missing "Start")
            print('mismatched entry:', timestamp, session, message, file=sys.stderr)


def main():
    with multiprocessing.Pool(processes=2 * len(os.sched_getaffinity(0))) as pool:
        logresults = pool.imap_unordered(functools.partial(process_log, ALL_REGEX), sys.argv[1:])
        # flatten the results into a single list
        times = [log for res in logresults for log in res]

    # Sort entries by month, then session ID, then time.
    # Sorting by month is to reduce the chance of problems due to duplicate session IDs across wide
    # ranges of time by grouping temporally-related log entries. This can cause entry mismatches
    # around the month transitions, though, but this happens frequently already due to journald
    # not storing the session ID for some entries.
    # Sorting by session ID keeps log entries in the same session together.
    times.sort(key=lambda x: (int(x[0] / (30 * 3600 * 24)), x[1], x[0]))
    analyze(times)
    if DEBUG:
        for timestamp, session, message in times:
            print(f'{timestamp}\t{session}\t{message}', file=sys.stderr)


if __name__ == '__main__':
    main()
