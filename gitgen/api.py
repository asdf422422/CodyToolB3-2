import json
import socket
import urllib.error
import urllib.request


class APIError(Exception):
    pass


def generate(key, model, temperature, max_tokens, instructions, context):
    payload = {'model': model, 'temperature': temperature,
               'max_output_tokens': max_tokens, 'store': False,
               'instructions': instructions, 'input': context,
               'text': {'format': {'type': 'json_object'}}}
    request = urllib.request.Request('https://api.openai.com/v1/responses',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        reasons = {400: '요청 오류: 모델·파라미터 지원 여부를 확인하세요.',
                   401: '인증 실패: OPENAI_API_KEY를 확인하세요.',
                   403: '접근 권한이 없습니다.', 404: '모델을 찾을 수 없습니다.',
                   429: '요청 한도 또는 API 사용 잔액을 확인하세요.'}
        raise APIError(f'HTTP {exc.code}: ' + reasons.get(exc.code, 'API 서버 오류가 발생했습니다.')) from None
    except (TimeoutError, socket.timeout):
        raise APIError('API 요청 시간이 초과되었습니다.') from None
    except urllib.error.URLError as exc:
        reason = 'API 요청 시간이 초과되었습니다.' if isinstance(exc.reason, (TimeoutError, socket.timeout)) else '네트워크 연결 또는 TLS 인증서를 확인하세요.'
        raise APIError(reason) from None
    except (ValueError, UnicodeError):
        raise APIError('API 응답이 올바른 JSON이 아닙니다.') from None
    except OSError:
        raise APIError('API 응답을 읽는 중 연결이 끊겼습니다.') from None
    if not isinstance(data, dict) or data.get('status') != 'completed':
        raise APIError('API 응답이 완료되지 않았습니다. 출력 토큰 한도와 모델 상태를 확인하세요.')
    try:
        texts = [part['text'] for item in data['output'] if item.get('type') == 'message'
                 for part in item['content'] if part.get('type') == 'output_text']
        if not texts:
            raise ValueError()
        return '\n'.join(texts)
    except (KeyError, TypeError, AttributeError, ValueError):
        raise APIError('API 응답에 유효한 생성 텍스트가 없습니다.') from None
