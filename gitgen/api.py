import json
import os
import re
import socket
import urllib.error
import urllib.request


class APIError(Exception):
    pass


DEFAULT_BASE_URL = 'https://copa.codyssey.kr/v1'


def generate(key, model, temperature, max_tokens, instructions, context):
    payload = {'model': model,
               'max_completion_tokens': max_tokens,
               'messages': [
                   {'role': 'system', 'content': instructions},
                   {'role': 'user', 'content': context},
               ]}
    if temperature is not None:
        payload['temperature'] = temperature
    base_url = os.environ.get('COPA_API_BASE_URL', DEFAULT_BASE_URL).strip().rstrip('/')
    if not base_url:
        base_url = DEFAULT_BASE_URL
    request = urllib.request.Request(base_url + '/chat/completions',
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
        detail = ''
        try:
            response_body = exc.read()
            try:
                error_data = json.loads(response_body)
                error = error_data.get('error')
                message = (error.get('message') or error.get('detail') or error.get('code')) if isinstance(error, dict) else error
                if not isinstance(message, str):
                    message = error_data.get('message') or error_data.get('detail') or error_data.get('msg')
            except (ValueError, UnicodeError):
                message = response_body.decode('utf-8', errors='replace').strip()
            if isinstance(message, str):
                if key:
                    message = message.replace(key, '[REDACTED]')
                message = re.sub(r'(?i)bearer\s+\S+', 'Bearer [REDACTED]', message)
                message = re.sub(r'\bsk-[A-Za-z0-9_-]+', '[REDACTED KEY]', message)
                if message:
                    detail = ' (' + message[:240] + ')'
        except (ValueError, UnicodeError, TypeError, AttributeError):
            pass
        raise APIError(f'HTTP {exc.code}: ' + reasons.get(exc.code, 'API 서버 오류가 발생했습니다.') + detail) from None
    except (TimeoutError, socket.timeout):
        raise APIError('API 요청 시간이 초과되었습니다.') from None
    except urllib.error.URLError as exc:
        reason = 'API 요청 시간이 초과되었습니다.' if isinstance(exc.reason, (TimeoutError, socket.timeout)) else '네트워크 연결 또는 TLS 인증서를 확인하세요.'
        raise APIError(reason) from None
    except (ValueError, UnicodeError):
        raise APIError('API 응답이 올바른 JSON이 아닙니다.') from None
    except OSError:
        raise APIError('API 응답을 읽는 중 연결이 끊겼습니다.') from None
    try:
        content = data['choices'][0]['message']['content']
        if not isinstance(content, str) or not content.strip():
            raise ValueError()
        return content
    except (KeyError, TypeError, AttributeError, ValueError):
        raise APIError('API 응답에 유효한 생성 텍스트가 없습니다.') from None
