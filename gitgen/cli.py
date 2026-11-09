import argparse
import json
import os
import sys
from . import api
from .config import load_dotenv
from .git import collect, GitError
from .safety import mask, prepare
from .formatting import instructions, validate, render


def parser():
    root = argparse.ArgumentParser(description='Git 변경으로 한국어 커밋/PR 초안을 생성합니다.')
    sub = root.add_subparsers(dest='command', required=True)
    for name in ('commit', 'pr'):
        p = sub.add_parser(name)
        p.add_argument('--staged', action='store_true', help='스테이징 변경만 분석')
        p.add_argument('--model', default='gpt-5-mini')
        p.add_argument('--temperature', type=float, default=None, help='temperature를 지원하는 모델에만 전달')
        p.add_argument('--max-tokens', type=int, default=1500)
        p.add_argument('--why', default='', help='변경 이유')
        p.add_argument('--safe-mode', action=argparse.BooleanOptionalAction, default=True)
    return root


def main(argv=None):
    load_dotenv()
    p = parser()
    args = p.parse_args(argv)
    if (args.temperature is not None and not 0 <= args.temperature <= 2) or args.max_tokens < 1 or not args.model.strip():
        p.error('temperature는 0~2, max-tokens는 양수, model은 비어 있지 않아야 합니다.')
    calls = 0
    try:
        changes = collect(args.staged)
        print(f'[INFO] Git status 수집 완료: {changes.count}개 파일 변경 감지')
        if changes.untracked:
            print(f'[INFO] 미추적 파일 {len(changes.untracked)}개: 분석하려면 git add로 선택하세요.')
        if not changes.patches:
            print('[INFO] 선택한 범위의 diff가 없습니다.' if changes.count else '[INFO] 변경 사항이 없습니다.')
            return 0
        diff, omitted = prepare(changes.patches, args.safe_mode)
        if omitted:
            print('[INFO] 안전 정책으로 일부 변경이 생략되었습니다. 초안은 전송된 변경만 설명합니다.')
        if not diff.strip():
            print('[INFO] 안전 처리 후 분석할 변경이 없습니다.')
            return 0
        if not args.safe_mode:
            print('[INFO] 안전 모드 OFF: 선택한 diff를 마스킹·제한 없이 전송합니다.')
        key = os.environ.get('OPENAI_API_KEY', '').strip()
        if not key:
            raise api.APIError('OPENAI_API_KEY 환경변수가 설정되지 않았습니다.')
        why = mask(args.why) if args.safe_mode else args.why
        context = json.dumps({'diff': diff, 'why': why, 'omitted': omitted}, ensure_ascii=False)
        prompt = instructions(args.command)
        for attempt in range(2):
            calls += 1
            print(f'[INFO] AI API 요청 중... ({calls}/2)')
            raw = api.generate(key, args.model, args.temperature, args.max_tokens, prompt, context)
            try:
                data = validate(raw, args.command, why)
                break
            except ValueError as exc:
                if attempt:
                    raise api.APIError('재생성 후 형식 검증 실패: ' + str(exc)) from None
                prompt += '\n이전 생성의 형식 오류를 수정하세요: ' + str(exc)
        print(render(data, args.command))
        if args.command == 'commit' and len(data['title']) > 50:
            print('[INFO] 제목이 권장 길이 50자를 넘습니다. 최대 72자 규칙은 충족합니다.')
        print('[DONE] 초안 생성 완료. 변경 사실과 테스트 제안을 검토한 뒤 적용하세요.')
        return 0
    except (GitError, api.APIError) as exc:
        print('[ERROR] ' + str(exc), file=sys.stderr)
        return 1
    finally:
        print(f'[INFO] API 호출 횟수: {calls}', file=sys.stderr)
