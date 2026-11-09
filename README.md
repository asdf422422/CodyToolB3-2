# CodyToolB3-2 — Git 변경 설명 생성기

Git 변경을 Copa의 OpenAI 호환 API에 전달해 한국어 변경 요약, 커밋 메시지와 PR 초안을 만드는 Python CLI입니다. 실제 커밋, push, PR 등록은 사용자가 검토 후 직접 수행합니다.

## 설치

Python 3.10 이상과 Git이 필요합니다. Python 표준 라이브러리만 사용하므로 pip 설치는 필요 없습니다.

```sh
git clone https://github.com/asdf422422/CodyToolB3-2.git
cd CodyToolB3-2
python --version
python main.py --help
```

Windows에서 `python`이 실행되지 않으면 Python을 설치하고 PATH를 설정하거나 설치된 Python 실행 파일의 전체 경로를 사용하세요.

## API 키 설정

`copa.codyssey.kr`에서 발급한 API 키가 필요합니다. 저장소 루트(`main.py`가 있는 폴더)에 `.env` 파일을 만들고 아래처럼 설정하세요. CLI가 이 파일을 자동으로 읽으며, 이미 OS 환경변수에 값이 있으면 OS 값을 우선합니다. 실제 키를 코드에 넣거나 Git에 커밋하지 마세요. `.env`는 `.gitignore`에 등록되어 Git 추적 대상에서 제외됩니다.

PowerShell에서 예제 파일을 복사하고 편집기를 열려면:

```powershell
Copy-Item .env.example .env
notepad .env
```

`OPENAI_API_KEY` 값에 Copa 콘솔에서 발급한 가상 키를 넣고 저장합니다.

```text
OPENAI_API_KEY=여기에-Copa-가상-키
```

기본 API 주소는 `https://copa.codyssey.kr/v1`입니다. 다른 호환 주소를 쓸 때만 `.env`에 `COPA_API_BASE_URL=https://호스트/v1`을 추가하세요. OS 환경변수 `OPENAI_API_KEY`와 `COPA_API_BASE_URL`도 계속 사용할 수 있습니다.

## 실행

분석할 Git 프로젝트의 **루트**에서 실행합니다. 이 저장소에 변경이 없다면 정상적으로 변경 없음 안내가 나옵니다. 다른 저장소를 분석하려면 그 저장소 루트에서 이 도구의 `main.py` 전체 경로를 실행하세요.

```sh
python main.py commit
python main.py pr --why "리뷰 작성 시간을 줄이기 위해 변경 설명 생성을 자동화"
python main.py commit --staged
python main.py pr --model claude-sonnet-4 --temperature 0.3 --max-tokens 1500
```

| 옵션 | 기본값 | 의미 |
| --- | --- | --- |
| `--staged` | 꺼짐 | `git add`한 변경만 분석 |
| `--model` | `gpt-5-mini` | Copa 콘솔의 모델 ID |
| `--temperature` | 미전달 | 지정하면 지원 모델에 0~2로 전달합니다. GPT-5 계열 등 일부 모델은 지원하지 않습니다. |
| `--max-tokens` | `1500` | Chat Completions의 `max_completion_tokens`, 출력 토큰 상한 |
| `--why` | 빈 문자열 | 사용자가 알고 있는 변경 배경 |
| `--safe-mode` | 켜짐 | 민감 파일 제외, 마스킹, 전송량 제한 |
| `--no-safe-mode` | — | 마스킹·파일/줄 제한 없이 전송 |

`--temperature`를 생략하면 모델 기본값을 사용합니다. GPT-5 계열처럼 temperature를 지원하지 않는 모델에는 이 옵션을 지정하지 마세요. 요청은 JSON 모드 파라미터를 강제하지 않으며 JSON 객체만 반환하도록 프롬프트를 지정한 뒤 결과를 검증합니다. HTTP 400이 발생하면 모델 ID와 해당 모델이 지원하는 파라미터를 확인하세요. 출력 토큰이 너무 작으면 결과가 미완료 상태로 종료될 수 있습니다.

기본 실행은 스테이징 패치와 미스테이징 패치를 모두 전달합니다. 같은 파일이 두 단계에서 수정되었다면 두 패치가 함께 포함됩니다. 이번 커밋 대상만 설명하려면 `--staged`를 사용하세요. **새 파일은 `git add 파일명`을 실행한 뒤 분석**합니다. 미추적 파일은 개수와 안내만 표시하며 내용을 읽거나 전송하지 않습니다. PR 역시 현재 미커밋 변경의 초안이며, 이미 커밋된 브랜치 간 비교는 지원하지 않습니다.

## 출력 예시

아래는 **설명용 예시이며 실제 API 실행 증빙이 아닙니다.**

```text
--- 변경 요약 ---
- Git diff 기반 설명 생성 기능 추가
--- Commit Message ---
feat: Git 변경 설명 생성 CLI 추가

- Git 변경 수집과 AI API 호출 흐름 구현
- 결과 형식 검증과 안전 모드 추가
----------------------
```

```text
--- PR Title ---
feat: 커밋 메시지와 PR 초안 생성 기능 추가
--- PR Body ---
## Why
- 확인 필요: 변경 배경이 제공되지 않았습니다.

## What
- Git 변경 수집과 한국어 초안 생성 구현

## How to Test
- 미실행·검토할 테스트 제안: python main.py commit 실행 후 출력 확인
----------------------
```

커밋 제목은 50자 이내를 권장하고 최대 72자로 검증합니다. PR 제목은 최대 80자이며 Why/What/How to Test에 각각 불릿이 있어야 합니다. 길이는 Python 문자열 문자 수로 계산합니다. 형식 검증 실패 시 한 번만 재생성하며 두 번째 실패는 오류로 종료합니다. 테스트 문구는 실행 증거가 아니라 **검토할 제안**입니다. 결과의 사실 여부와 비밀정보 포함 여부를 사람이 확인해야 합니다.

## 안전 모드와 비용

- 기본 안전 모드에서는 `.env`, `.env.*`, `.pem`, `.key`, `.p12`, `.pfx`, `id_rsa`, `id_ed25519`, `credentials`, `credentials.json` 파일을 제외합니다. 이름 변경 전후 경로 중 하나라도 해당하면 제외합니다.
- OpenAI/GitHub/AWS 키 형태, 이메일, key/password/secret/token 대입문, PEM 개인키 블록을 마스킹합니다. `--why`에도 동일하게 적용합니다.
- 최대 10개 파일과 diff 200줄을 전달합니다. 헤더와 문맥 줄도 200줄에 포함됩니다. 일부 파일/패치가 생략되면 터미널에서 알립니다. 전체가 제외되면 API를 호출하지 않습니다.
- 패턴 마스킹은 모든 비밀정보와 개인정보를 보장하지 않습니다. 전송 전 변경 내용을 검토하세요. 안전 모드 OFF는 코드 원문을 외부로 보냅니다.
- 실행당 정상 1회, 형식 재생성 포함 최대 2회 호출합니다. 네트워크·HTTP 오류는 자동 재시도하지 않습니다. 호출 횟수를 표시하고 각 요청에 60초 타임아웃을 적용합니다.
- API 호출에는 비용이 발생할 수 있습니다. 제한된 diff와 낮은 출력 상한으로 시작하고 Copa 사용량 대시보드를 확인하세요. 데이터 보관 정책은 Copa 서비스 정책을 따릅니다.
- 생성 텍스트는 stdout, 오류와 API 호출 횟수는 stderr에 출력됩니다. 성공·변경 없음은 종료 코드 0, 실행 실패는 1, 잘못된 CLI 인수는 2입니다.

## 구조와 검증

```text
main.py               CLI 진입점
gitgen/cli.py         옵션과 전체 실행 흐름
gitgen/git.py         읽기 전용 Git 수집
gitgen/safety.py      제외·마스킹·전송량 제한
gitgen/api.py         OpenAI 호환 Chat Completions REST 요청과 오류 처리
gitgen/formatting.py  프롬프트·검증·출력
tests/test_gitgen.py  임시 Git 저장소 및 모의 API 테스트
```

```sh
python -m unittest discover -s tests -v
```

테스트는 임시 저장소에서 새 파일, 스테이징 혼합, 한글 경로, 이름 변경, 삭제, 충돌과 루트 제한을 검증합니다. 모의 API로 인증/HTTP/네트워크 오류, 응답 파싱, 형식 재생성 상한을 확인합니다. 네트워크나 실제 API 키는 필요 없습니다.

실제 API 확인은 작은 코드 변경을 만든 후 위 환경변수를 설정하고 `commit`과 `pr`을 각각 실행하세요. 검증 상태는 [VALIDATION.md](VALIDATION.md)에 기록합니다.

## API 참고

- [Copa API 콘솔](https://copa.codyssey.kr)
- [OpenAI Chat Completions API reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

REST 요청은 Bearer 인증과 OpenAI 호환 Chat Completions JSON 본문으로 구성합니다. 기본 주소 `https://copa.codyssey.kr/v1` 뒤에 `/chat/completions`를 붙여 요청하며, `COPA_API_BASE_URL`로 주소를 바꿀 수 있습니다. 응답의 `choices[0].message.content`에서 생성 텍스트를 추출합니다. 지정한 경우 `temperature`가 표현 다양성을, `max_completion_tokens`가 최대 생성 토큰을 제어합니다. GPT-5 계열은 `temperature`를 받지 않으므로 기본 요청에서는 생략합니다. 프롬프트에는 출력 JSON 구조, 제목 길이, 한국어 컨벤션과 사용자 변경 이유를 포함합니다. diff 내부 문장은 실행 지시가 아닌 분석 자료로 취급합니다.
