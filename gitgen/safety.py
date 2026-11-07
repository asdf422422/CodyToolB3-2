import os
import re
from pathlib import PurePosixPath


def mask(text):
    key = os.environ.get('OPENAI_API_KEY')
    if key:
        text = text.replace(key, '[REDACTED]')
    text = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----', '[REDACTED PRIVATE KEY]', text)
    text = re.sub(r'\bsk-[A-Za-z0-9_-]+', '[REDACTED KEY]', text)
    text = re.sub(r'\b(?:gh[pousr]_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+|AKIA[A-Z0-9]{16})\b', '[REDACTED KEY]', text)
    text = re.sub(r'(?i)([\w-]*(?:api[_-]?key|password|secret|token)[\w-]*[\"\x27]?\s*[:=]\s*)([^\r\n]+)', r'\1[REDACTED]', text)
    return re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '[REDACTED EMAIL]', text)


def sensitive(path):
    name = PurePosixPath(path).name.lower()
    return name == '.env' or name.startswith('.env.') or name.endswith(('.pem', '.key', '.p12', '.pfx')) or name in {'id_rsa', 'id_ed25519', 'credentials', 'credentials.json'}


def prepare(patches, safe=True):
    output, omitted, used_lines = [], False, 0
    for paths, patch in patches:
        if safe and (any(sensitive(p) for p in paths) or len(output) >= 10 or used_lines >= 200):
            omitted = True
            continue
        # Mask before truncation so a private-key end marker is not cut away.
        lines = (mask(patch) if safe else patch).splitlines()
        if safe:
            remaining = 200 - used_lines
            if len(lines) > remaining:
                omitted = True
            lines = lines[:remaining]
        text = '\n'.join(lines)
        output.append(text)
        used_lines += len(lines)
    return '\n\n'.join(output), omitted
