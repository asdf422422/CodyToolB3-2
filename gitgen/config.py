import os
from pathlib import Path


ENV_FILE = Path(__file__).resolve().parent.parent / '.env'
SUPPORTED_ENV_VARS = {'OPENAI_API_KEY', 'COPA_API_BASE_URL'}


def load_dotenv(path=ENV_FILE):
    """Load supported settings from the repository .env without overriding OS env vars."""
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except FileNotFoundError:
        return
    except OSError:
        return

    for line in lines:
        entry = line.strip()
        if not entry or entry.startswith('#'):
            continue
        if entry.startswith('export '):
            entry = entry[7:].lstrip()
        name, separator, value = entry.partition('=')
        name = name.strip()
        if not separator or name not in SUPPORTED_ENV_VARS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if not os.environ.get(name, '').strip():
            os.environ[name] = value
