"""WSGI server for returning static pages.

The deployment expects a WSGI module, so that's what we give it, even if
we're not using it to its potential (yet).
"""

import base64
import datetime
import mimetypes
import os
import re
import struct
import sys
from typing import List, Tuple

# Number of hours to use in the expires header
EXPIRE_HOURS = 1


def root_path():
    "Return the directory containing this very module"
    return os.path.dirname(sys.modules[__name__].__file__)


sys.path.append(os.path.join(root_path(), 'application', 'python'))


INDEX_PATH = 'index.html'
CHARSET = 'UTF-8'
SAFE_PATH = re.compile(r'^[-_/.a-zA-Z0-9]+$')


def get_static_path(fn: str) -> str:
    return os.path.join(root_path(), fn.lstrip('/'))


def get_static(fn: str) -> bytes:
    try:
        with open(get_static_path(fn), 'rb') as f:
            output = f.read()
    except FileNotFoundError:
        output = 'ERROR: cannot find static file\n'.encode(CHARSET)
    return output


def get_static_headers(fn: str) -> List[Tuple[str, str]]:
    response_headers = []
    (mime, encoding) = mimetypes.guess_type(get_static_path(fn))
    if mime:
        response_headers.append(('Content-Type', f'{mime}; charset={CHARSET}'))

    stat = os.stat(get_static_path(fn))
    mtimestr = datetime.datetime.fromtimestamp(stat.st_mtime).strftime(
            '%a, %d %b %Y %H:%M:%S GMT')
    response_headers.append(('Last-Modified', mtimestr))

    expstr = (datetime.datetime.now(tz=datetime.timezone.utc)
              + datetime.timedelta(hours=EXPIRE_HOURS)).strftime('%a, %d %b %Y %H:%M:%S GMT')
    response_headers.append(('Expires', expstr))

    # Create an ETag based on size, mtime and inode number
    tagval = struct.pack('>qqq', stat.st_size, int(stat.st_mtime), stat.st_ino)
    tagshort = tagval.lstrip(b'\0')  # These left-justified zeros from the size add only bulk
    response_headers.append(('ETag', '"' + base64.b85encode(tagshort).decode('US-ASCII') + '"'))
    return response_headers


def safe_path(path: str) -> bool:
    """Only allow safe paths to be served.

    In production, this can just be "return path == '/'" because all the other "safe" paths are
    served directly by Apache, but serving the rest here as well makes testing easier.
    This goes a bit overboard in checking for safety since the WSGI server does
    much of the sanity checking for us. But, it's better to be safe than sorry (we really don't
    want to accidentally serve /etc/passwd).
    """
    parts = path.split('/', 2)
    return (parts[0] == ''
            and parts[1] in frozenset(
                ('index.html', 'images', 'static', 'robots.txt', 'version.txt'))
            and path.count('.') <= 1 and path.count('/') <= 2 and SAFE_PATH.match(path) is not None
            and os.path.isfile(get_static_path(path)))


def application(environ, start_response) -> List[bytes]:
    path = environ['PATH_INFO']
    if path == '/':
        path = '/' + INDEX_PATH
    if safe_path(path):
        status = '200 OK'
        response_headers = get_static_headers(path)
        start_response(status, response_headers)
        output = get_static(path)
    else:
        status = '404 Not found'
        response_headers = [('Content-Type', f'text/plain; charset={CHARSET}')]
        start_response(status, response_headers)
        output = 'Page not found\n'.encode(CHARSET)
    return [output]


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    with make_server("", 8000, application) as httpd:
        print("Serving on port 8000...")

        # Serve until process is killed
        httpd.serve_forever()
