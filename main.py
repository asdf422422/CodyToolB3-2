from gitgen.cli import main
import sys

if __name__ == '__main__':
    # Keep Korean output readable when redirected on Windows as well.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main())
