# Copyright 2026 Trieflow LLC. MIT.
"""Bind reviewed native sources and the exact current public application tree."""
import hashlib
import re
import subprocess
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from msix_qualification import file_record, _regular_stream

SOURCE_PAGE = 'https://duplisift.trieflow.com/source'
RELEASE_URL = 'https://github.com/hashfunction/twinquay/releases/tag/native-sources-2026-09-12'
DOWNLOAD_ROOT = RELEASE_URL.replace('/tag/', '/download/') + '/'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def utc(value):
    require(isinstance(value, str), 'Missing UTC publication verification time')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, 'Verification time must be UTC')
    except ValueError as error:
        raise ValueError('Invalid UTC publication verification time') from error


def validate_publication(record, plan_path):
    import json
    with _regular_stream(plan_path) as stream:
        plan = json.load(stream)
    require(record.get('schema_version') == 1 and record.get('product') == 'DupliSift'
            and record.get('publication_verified') is True
            and record.get('source_page') == SOURCE_PAGE and record.get('release_url') == RELEASE_URL,
            'Native source publication is absent, unverified or for another release')
    utc(record.get('verified_at_utc'))
    expected = {item['filename']: {key: item[key] for key in ('bytes', 'sha256')} for item in plan['assets']}
    require(len(expected) == len(plan['assets']) == 71, 'Expected exact reviewed 71 native source archives')

    def check(item, name, measured):
        require(item.get('filename') == name and all(item.get(key) == value for key,value in measured.items()),
                'Published source bytes differ from reviewed archive: ' + name)
        require(item.get('url') == DOWNLOAD_ROOT + name, 'Source needs an exact fixed release asset URL: ' + name)
        final = urlsplit(item.get('final_url', ''))
        require(final.scheme == 'https' and bool(final.hostname) and not final.username and not final.password,
                'Source lacks an anonymously verified final HTTPS URL: ' + name)
        utc(item.get('verified_at_utc'))

    assets = record.get('assets', [])
    require(isinstance(assets, list) and len(assets) == len(expected), 'Incomplete native source publication')
    seen = set()
    for item in assets:
        name = item.get('filename')
        require(name in expected and name not in seen, 'Duplicate or unexpected published source')
        check(item, name, expected[name]); seen.add(name)
    check(record.get('manifest', {}), 'source-release-assets.json', file_record(plan_path))
    return record


def download(url, destination, limit):
    """Unauthenticated HTTPS bytes, bounded in size and time; never reuse HEAD metadata."""
    require(urlsplit(url).scheme == 'https', 'Source download requires HTTPS')
    started = time.monotonic()
    digest = hashlib.sha256(); size = 0
    with urlopen(Request(url, headers={'User-Agent': 'DupliSift-source-verification'}), timeout=30) as response:
        require(response.status == 200 and urlsplit(response.url).scheme == 'https', 'Anonymous source download failed')
        with destination.open('xb') as target:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                require(size <= limit and time.monotonic() - started < 180, 'Source download exceeded bound')
                target.write(chunk); digest.update(chunk)
        final_url = response.url
    return dict(url=url, final_url=final_url, bytes=size, sha256=digest.hexdigest(),
                verified_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))


def git(source, *arguments):
    return subprocess.check_output(['git', '-C', str(source), *arguments], timeout=30)


def verify_application_archive(archive, source, commit):
    require(re.fullmatch('[0-9a-f]{40}', commit or ''), 'Current source needs an exact Git commit')
    expected = {}
    for row in git(source, 'ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if not row: continue
        metadata, raw_name = row.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split(' ')
        require(kind == 'blob' and mode in ('100644', '100755', '120000'), 'Unsupported source tree entry')
        expected[raw_name.decode('utf-8')] = (mode, blob)
    seen = set(); prefix = None; total = 0
    with tarfile.open(archive, 'r:gz') as stream:
        for member in stream:
            parts = PurePosixPath(member.name).parts
            require(parts and not member.name.startswith('/') and '..' not in parts, 'Unsafe source archive path')
            prefix = prefix or parts[0]
            require(parts[0] == prefix, 'Source archive has multiple roots')
            if member.isdir(): continue
            name = '/'.join(parts[1:])
            require(name in expected and name not in seen, 'Missing, extra or duplicate source archive member')
            mode, blob = expected[name]
            if mode == '120000':
                require(member.issym(), 'Source archive symlink mode changed')
                data = member.linkname.encode('utf-8')
            else:
                require(member.isfile() and bool(member.mode & 0o111) == (mode == '100755'), 'Source file mode changed')
                require(0 <= member.size <= 64 * 1024 * 1024, 'Oversized application source member')
                data = stream.extractfile(member).read()
            total += len(data)
            require(total <= 256 * 1024 * 1024, 'Application source archive is too large')
            actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            require(actual == blob, 'Public application source bytes differ from Git: ' + name)
            seen.add(name)
    require(seen == set(expected) and bool(seen), 'Public application archive omits tracked source')
    return dict(source_commit=commit, git_tree=git(source, 'rev-parse', commit+'^{tree}').decode().strip(),
                verified_tracked_files=len(seen), verified_source_bytes=total)


def verify_public_sources(record, plan_path, source, commit):
    validate_publication(record, plan_path)
    with tempfile.TemporaryDirectory(prefix='duplisift-public-source-') as temporary:
        temporary = Path(temporary).resolve()
        plan_copy = temporary / 'source-release-assets.json'
        fetched = download(record['manifest']['url'], plan_copy, 1024 * 1024)
        require(file_record(plan_copy) == file_record(plan_path), 'Public native source manifest bytes changed')
        archive = temporary / 'current-app.tar.gz'
        url = 'https://github.com/hashfunction/twinquay/archive/' + commit + '.tar.gz'
        current = download(url, archive, 64 * 1024 * 1024)
        current.update(verify_application_archive(archive, source, commit))
    return dict(native_source_manifest=fetched, application_source=current,
                native_assets_verified=len(record['assets']), source_page=SOURCE_PAGE, release_url=RELEASE_URL)
