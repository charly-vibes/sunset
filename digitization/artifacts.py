# Purpose: Retain and verify immutable recorded recognition attempts for reuse.
# Responsibilities: Address requests/outputs by canonical hashes, publish append-
#   only attempts atomically, and preserve first selection across fresh imports.
# Rationale: sunset-rmx.3 separates operation identity from variable responses;
#   no output is reused without digest and response-schema verification.
import hashlib
import os
from pathlib import Path
import tempfile
import uuid

from dsc03 import validator


class CacheIntegrityError(ValueError):
    """A cache entry cannot be verified; do not silently replace it."""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return validator.canonical(value) + b'\n'


def validate_response(response):
    if (not isinstance(response, dict) or not isinstance(response.get('raw_text'), str)
            or not isinstance(response.get('unresolved'), list)
            or any(not isinstance(reason, str) or not reason for reason in response['unresolved'])):
        raise ValueError('recorded recognition must contain text and unresolved reason strings')
    encoded(response)  # Unicode and finite-number validation before admission.
    return response


class OperationCache:
    """A local append-only recognition cache; the first default never changes."""

    def __init__(self, root):
        self.root = Path(root).resolve()

    def _path(self, relative):
        path = self.root / relative
        if not path.resolve().is_relative_to(self.root):
            raise CacheIntegrityError('cache path escapes root')
        return path

    def _publish(self, relative, raw):
        path = self._path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Linking a complete temporary file makes concurrent publication exclusive
        # without exposing partially written requests, responses or pointers.
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            name = temporary.name
            temporary.write(raw)
            temporary.flush()
            os.fsync(temporary.fileno())
        try:
            os.link(name, path)
            return True
        except FileExistsError:
            return False
        finally:
            Path(name).unlink()

    def _json(self, relative):
        try:
            return validator.loads(self._path(relative).read_text(encoding='utf-8'))
        except (OSError, ValueError, validator.Duplicate) as error:
            raise CacheIntegrityError(f'invalid cache artifact: {relative}') from error

    def response_bytes(self, attempt):
        try:
            ref = attempt['output']
            if ref['path'] != 'blobs/' + ref['sha256']:
                raise ValueError('invalid response reference')
            raw = self._path(ref['path']).read_bytes()
            if sha(raw) != ref['sha256']:
                raise ValueError('response digest mismatch')
            validate_response(validator.loads(raw.decode('utf-8')))
            return raw
        except (OSError, KeyError, TypeError, ValueError, validator.Duplicate) as error:
            raise CacheIntegrityError('cached response failed integrity/schema verification') from error

    def read_response(self, attempt):
        return validator.loads(self.response_bytes(attempt).decode('utf-8'))

    def _attempts(self, key):
        attempts = []
        directory = self._path('operations/' + key)
        for path in sorted(directory.glob('*.attempt.json')):
            identifier = path.name.removesuffix('.attempt.json')
            try:
                raw = path.read_bytes()
                body = validator.loads(raw.decode('utf-8'))
                if sha(raw) != identifier or body['operation_key'] != key or body['version'] != '1':
                    raise ValueError('attempt identity mismatch')
                attempt = {'id': identifier, **body}
                self.read_response(attempt)
                attempts.append(attempt)
            except (OSError, KeyError, TypeError, ValueError, validator.Duplicate) as error:
                raise CacheIntegrityError('invalid cached attempt') from error
        return attempts

    def resolve(self, request, produce, *, fresh=False, selected=None):
        raw_request = encoded(request)
        key = sha(raw_request)
        directory = 'operations/' + key + '/'
        request_path = self._path(directory + 'request.json')
        if not self._publish(directory + 'request.json', raw_request):
            if request_path.read_bytes() != raw_request:
                raise CacheIntegrityError('operation request bytes are corrupt')
        attempts = self._attempts(key)
        pointer = self._path(directory + 'selected.json')
        cache_hit = False
        if selected is not None:
            if fresh:
                raise ValueError('fresh and explicit selection are mutually exclusive')
            if not any(a['id'] == selected for a in attempts):
                raise ValueError('selected attempt is unavailable for this operation')
            chosen = selected
            cache_hit = True
        elif not fresh and pointer.exists():
            try:
                chosen = self._json(directory + 'selected.json')['id']
            except (KeyError, TypeError) as error:
                raise CacheIntegrityError('invalid default selection') from error
            if not any(a['id'] == chosen for a in attempts):
                raise CacheIntegrityError('default selected attempt is missing')
            cache_hit = True
        else:
            response = validate_response(produce())
            raw_response = encoded(response)
            output_hash = sha(raw_response)
            output_path = 'blobs/' + output_hash
            if not self._publish(output_path, raw_response):
                if self._path(output_path).read_bytes() != raw_response:
                    raise CacheIntegrityError('existing response bytes are corrupt')
            body = {'version': '1', 'operation_key': key, 'nonce': uuid.uuid4().hex,
                    'output': {'path': output_path, 'sha256': output_hash}}
            raw_attempt = encoded(body)
            chosen = sha(raw_attempt)
            self._publish(directory + chosen + '.attempt.json', raw_attempt)
            # Fresh runs pin their own output, but never overwrite this pointer.
            self._publish(directory + 'selected.json', encoded({'id': chosen}))
            attempts = self._attempts(key)
        attempt = next(a for a in attempts if a['id'] == chosen)
        return {'key': key, 'request': request, 'selected_attempt': chosen,
                'selected_output': attempt['output']['sha256'], 'cache_hit': cache_hit,
                'attempts': attempts, 'response': self.read_response(attempt),
                'fresh_determinism': 'not-claimed'}
