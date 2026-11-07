import subprocess
from dataclasses import dataclass


class GitError(Exception):
    pass


def run(*args):
    try:
        result = subprocess.run(['git', *args], capture_output=True, check=False)
    except OSError as exc:
        raise GitError('Git을 실행할 수 없습니다. 설치와 PATH를 확인하세요.') from exc
    if result.returncode:
        raise GitError('Git 명령 실행 실패: 저장소 상태와 접근 권한을 확인하세요.')
    return result.stdout.decode('utf-8', errors='replace')


@dataclass
class Changes:
    patches: list
    untracked: list
    count: int


def collect(staged=False):
    # status --porcelain avoids additional Git metadata commands.
    status = run('status', '--porcelain=v1', '-z', '--untracked-files=all')
    # --show-prefix is deliberately avoided: discover the root through .git.
    from pathlib import Path
    if not (Path.cwd() / '.git').exists():
        raise GitError('프로젝트 루트 디렉토리에서 실행하세요.')
    entries = status.split('\0')
    files, untracked = [], []
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry:
            continue
        code, path = entry[:2], entry[3:]
        old = None
        if 'R' in code or 'C' in code:
            old = entries[i]
            i += 1
        if code in {'DD', 'AU', 'UD', 'UA', 'DU', 'AA', 'UU'}:
            raise GitError('병합 충돌을 먼저 해결하세요.')
        if code == '??':
            untracked.append(path)
        else:
            files.append((code, path, old))
    patches = []
    for code, path, old in files:
        paths = [path] + ([old] if old else [])
        literal_paths = [':(literal)' + p for p in paths]
        parts = []
        if code[0] != ' ':
            parts.append(run('diff', '--cached', '--no-ext-diff', '--no-textconv', '--no-color', '--', *literal_paths))
        if not staged and code[1] != ' ':
            parts.append(run('diff', '--no-ext-diff', '--no-textconv', '--no-color', '--', *literal_paths))
        patch = '\n'.join(p for p in parts if p.strip())
        if patch:
            patches.append((paths, patch))
    return Changes(patches, untracked, len(files) + len(untracked))
