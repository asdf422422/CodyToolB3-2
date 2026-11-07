# CodyTool3-2 — Git 변경 설명 생성기

Git 변경을 OpenAI API에 전달해 한국어 변경 요약, 커밋 메시지와 PR 초안을 만드는 Python CLI입니다. 실제 커밋, push, PR 등록은 사용자가 검토 후 직접 수행합니다.

## 설치

Python 3.10 이상과 Git이 필요합니다. Python 표준 라이브러리만 사용하므로 pip 설치는 필요 없습니다.

```sh
git clone https://github.com/asdf422422/CodyTool3-2.git
cd CodyTool3-2
python --version
python main.py --help
```

Windows에서 `python`이 실행되지 않으면 Python을 설치하고 PATH를 설정하거나 설치된 Python 실행 파일의 전체 경로를 사용하세요.

## API 키 설정

OpenAI API에서 사용 가능한 키와 API 사용 잔액/권한이 필요합니다. 키를 코드나 Git에 넣지 마세요. `.env` 파일은 자동으로 읽지 않습니다.

PowerShell에서 키를 명령 기록에 남기지 않고 현재 터미널 환경에 설정:

```powershell
$secureKey = Read-Host 'OpenAI API key' -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $secureKey).Password
```

bash에서 설정:

```bash
read -rs -p 'OpenAI API key: ' OPENAI_API_KEY; echo
export OPENAI_API_KEY
```

키는 해당 셸과 자식 프로세스에 전달됩니다. 다른 터미널/이미 실행된 앱에는 자동 반영되지 않습니다.

## 실행

분석할 Git 프로젝트의 **루트**에서 실행합니다. 이 저장소에 변경이 없다면 정상적으로 변경 없음 안내가 나옵니다. 다른 저장소를 분석하려면 그 저장소 루트에서 이 도구의 `main.py` 전체 경로를 실행하세요.

```sh
python main.py commit
python main.py pr --why "리뷰 작성 시간을 줄이기 위해 변경 설명 생성을 자동화"
python main.py commit --staged
python main.py pr --model gpt-4.1-mini --temperature 0.3 --max-tokens 1500
```

| 옵션 | 기본값 | 의미 |
| --- | --- | --- |
| `--staged` | 꺼짐 | `git add`한 변경만 분석 |
| `--model` | `gpt-4.1-mini` | OpenAI 모델 ID |
| `--temperature` | `0.3` | 0~2, 낮으면 표현이 비교적 일정하고 높으면 다양해짐 |
| `--max-tokens` | `1500` | Responses API의 `max_output_tokens`, 출력 토큰 상한 |
| `--why` | 빈 문자열 | 사용자가 알고 있는 변경 배경 |
| `--safe-mode` | 켜짐 | 민감 파일 제외, 마스킹, 전송량 제한 |
| `--no-safe-mode` | — | 마스킹·파일/줄 제한 없이 전송 |

일부 모델은 temperature나 JSON 출력 옵션을 지원하지 않습니다. 이 경우 HTTP 400 안내를 확인하고 지원 모델/옵션으로 실행하세요. 출력 토큰이 너무 작으면 결과가 미완료 상태로 종료될 수 있습니다.

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
- API 호출에는 비용이 발생할 수 있습니다. 제한된 diff와 낮은 출력 상한으로 시작하고 공급자의 사용량 대시보드를 확인하세요. `store: false`를 요청하지만 이를 데이터 보관이 전혀 없다는 의미로 해석하면 안 됩니다.
- 생성 텍스트는 stdout, 오류와 API 호출 횟수는 stderr에 출력됩니다. 성공·변경 없음은 종료 코드 0, 실행 실패는 1, 잘못된 CLI 인수는 2입니다.

## 구조와 검증

```text
main.py               CLI 진입점
gitgen/cli.py         옵션과 전체 실행 흐름
gitgen/git.py         읽기 전용 Git 수집
gitgen/safety.py      제외·마스킹·전송량 제한
gitgen/api.py         Responses REST 요청과 오류 처리
gitgen/formatting.py  프롬프트·검증·출력
tests/test_gitgen.py  임시 Git 저장소 및 모의 API 테스트
```

```sh
python -m unittest discover -s tests -v
```

테스트는 임시 저장소에서 새 파일, 스테이징 혼합, 한글 경로, 이름 변경, 삭제, 충돌과 루트 제한을 검증합니다. 모의 API로 인증/HTTP/네트워크 오류, 응답 파싱, 형식 재생성 상한을 확인합니다. 네트워크나 실제 API 키는 필요 없습니다.

실제 API 확인은 작은 코드 변경을 만든 후 위 환경변수를 설정하고 `commit`과 `pr`을 각각 실행하세요. 검증 상태는 [VALIDATION.md](VALIDATION.md)에 기록합니다.

## API 참고

- [OpenAI Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [GPT-4.1 mini 모델](https://developers.openai.com/api/docs/models/gpt-4.1-mini)

REST 요청은 Bearer 인증과 JSON 본문으로 구성하고 응답의 `output` 메시지에서 텍스트를 추출합니다. `temperature`는 표현 다양성을, `max_output_tokens`는 최대 응답량을 제어합니다. 프롬프트에는 출력 JSON 구조, 제목 길이, 한국어 컨벤션과 사용자 변경 이유를 포함합니다. diff 내부 문장은 실행 지시가 아닌 분석 자료로 취급합니다.
