import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from gitgen.git import collect, GitError
from gitgen.safety import prepare, mask
from gitgen.formatting import validate, render
from gitgen.cli import main
from gitgen import api


GOOD = json.dumps({'summary': ['변경 요약'], 'title': 'feat: 변경 추가', 'body': ['핵심 변경 추가']})


class RepoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = Path.cwd()
        os.chdir(self.temp.name)
        self.addCleanup(self.cleanup)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        Path('한글.txt').write_text('before\n', encoding='utf-8')
        self.git('add', '.')
        self.git('commit', '-m', 'initial')

    def cleanup(self):
        os.chdir(self.previous)
        self.temp.cleanup()

    def git(self, *args, check=True):
        return subprocess.run(['git', *args], check=check, capture_output=True)

    def invoke(self, args, side_effect=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}), patch('gitgen.api.generate', side_effect=side_effect, return_value=GOOD) as mock:
            code = main(args)
        return code, out.getvalue() + err.getvalue(), mock

    def test_clean_and_untracked_no_api(self):
        code, text, mock = self.invoke(['commit'])
        self.assertEqual(code, 0)
        self.assertIn('변경 사항이 없습니다', text)
        mock.assert_not_called()
        Path('new.txt').write_text('new')
        code, text, mock = self.invoke(['commit'])
        self.assertIn('git add', text)
        mock.assert_not_called()
        self.git('add', 'new.txt')
        self.assertIn('new', collect().patches[0][1])

    def test_staged_and_unstaged(self):
        Path('한글.txt').write_text('stage\n', encoding='utf-8')
        self.git('add', '.')
        Path('한글.txt').write_text('worktree\n', encoding='utf-8')
        self.assertIn('+stage', collect(True).patches[0][1])
        self.assertNotIn('+worktree', collect(True).patches[0][1])
        self.assertIn('+worktree', collect().patches[0][1])

    def test_rename_delete_and_literal_path(self):
        self.git('mv', '한글.txt', 'renamed.txt')
        self.assertEqual(set(collect().patches[0][0]), {'한글.txt', 'renamed.txt'})
        self.git('commit', '-m', 'rename')
        Path('renamed.txt').unlink()
        self.assertIn('deleted file', collect().patches[0][1])
        Path('[abc].txt').write_text('literal')
        self.git('add', '--', '[abc].txt')
        self.assertTrue(any('literal' in p for _, p in collect().patches))

    def test_conflict(self):
        self.git('checkout', '-b', 'other')
        Path('한글.txt').write_text('other\n')
        self.git('commit', '-am', 'other')
        self.git('checkout', 'main')
        Path('한글.txt').write_text('main\n')
        self.git('commit', '-am', 'main')
        self.git('merge', 'other', check=False)
        with self.assertRaisesRegex(GitError, '충돌'):
            collect()

    def test_root_required(self):
        Path('sub').mkdir()
        os.chdir('sub')
        with self.assertRaisesRegex(GitError, '루트'):
            collect()

    def test_initial_repo_staged_file(self):
        Path('fresh').mkdir()
        os.chdir('fresh')
        self.git('init')
        Path('new.py').write_text('print(1)')
        self.git('add', '.')
        self.assertIn('print(1)', collect(True).patches[0][1])

    def test_retry_and_call_limit(self):
        Path('한글.txt').write_text('updated')
        code, text, mock = self.invoke(['commit'], ['bad', GOOD])
        self.assertEqual(code, 0)
        self.assertEqual(mock.call_count, 2)
        code, text, mock = self.invoke(['commit'], ['bad', 'bad'])
        self.assertEqual(code, 1)
        self.assertEqual(mock.call_count, 2)
        self.assertIn('형식 검증 실패', text)

    def test_api_error_no_retry(self):
        Path('한글.txt').write_text('updated')
        code, text, mock = self.invoke(['commit'], api.APIError('인증 실패'))
        self.assertEqual(code, 1)
        self.assertEqual(mock.call_count, 1)

    def test_sensitive_only_no_api(self):
        Path('.env').write_text('TOKEN=secret')
        self.git('add', '.env')
        code, text, mock = self.invoke(['pr'])
        self.assertIn('분석할 변경이 없습니다', text)
        mock.assert_not_called()

    def test_missing_key(self):
        Path('한글.txt').write_text('updated')
        changes = collect()
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), patch('gitgen.cli.collect', return_value=changes), patch('gitgen.api.generate') as mock:
            self.assertEqual(main(['commit']), 1)
            mock.assert_not_called()


class SafetyTests(unittest.TestCase):
    def test_mask_and_limits(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'actual-secret'}):
            text = mask('actual-secret sk-example123 user@example.com api_key="hello"')
        for secret in ['actual-secret', 'sk-example123', 'user@example.com', 'hello']:
            self.assertNotIn(secret, text)
        patches = [([f'{i}.py'], '\n'.join(['+line'] * 30)) for i in range(12)]
        text, omitted = prepare(patches)
        self.assertTrue(omitted)
        self.assertEqual(sum(line == '+line' for line in text.splitlines()), 200)
        text, omitted = prepare([([f'{i}.py'], '+line') for i in range(12)])
        self.assertEqual(text.count('+line'), 10)
        self.assertTrue(omitted)

    def test_sensitive_rename_and_off(self):
        patches = [(['renamed.txt', '.env'], 'TOKEN=secret')]
        self.assertEqual(prepare(patches), ('', True))
        self.assertEqual(prepare(patches, False), ('TOKEN=secret', False))

    def test_private_key_masked_before_truncation(self):
        private = '-----BEGIN PRIVATE KEY-----\n' + 'secretmaterial\n' * 250 + '-----END PRIVATE KEY-----'
        text, _ = prepare([(['source.py'], private)])
        self.assertNotIn('secretmaterial', text)

    def test_why_masked_in_request(self):
        from gitgen.git import Changes
        with patch('gitgen.cli.collect', return_value=Changes([(['x.py'], '+change')], [], 1)), patch.dict(os.environ, {'OPENAI_API_KEY': 'secret'}), patch('gitgen.api.generate', return_value=GOOD) as mock, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['commit', '--why', 'user@example.com']), 0)
            self.assertNotIn('user@example.com', mock.call_args.args[-1])


class FormatTests(unittest.TestCase):
    def test_commit_boundary(self):
        data = json.loads(GOOD)
        data['title'] = 'feat: ' + '가' * 66
        validate(json.dumps(data), 'commit', '')
        data['title'] += '가'
        with self.assertRaises(ValueError):
            validate(json.dumps(data), 'commit', '')

    def test_pr_sections_and_missing_background(self):
        data = {'summary': ['요약'], 'title': '가' * 80, 'why': ['추측'], 'what': ['변경'], 'tests': ['테스트 실행 제안']}
        result = validate(json.dumps(data), 'pr', '')
        text = render(result, 'pr')
        for header in ['## Why\n- ', '## What\n- ', '## How to Test\n- ']:
            self.assertIn(header, text)
        self.assertNotIn('추측', text)
        self.assertIn('미실행', text)
        data['title'] += '가'
        with self.assertRaises(ValueError):
            validate(json.dumps(data), 'pr', '')
        data['title'] = 'title'
        data['what'] = []
        with self.assertRaises(ValueError):
            validate(json.dumps(data), 'pr', '')


class APITests(unittest.TestCase):
    def call(self):
        return api.generate('secret', 'gpt-5-mini', None, 1500, 'JSON', 'context')

    def test_request_and_response(self):
        response = {'choices': [{'message': {'content': GOOD}}]}
        with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as mock:
            self.assertEqual(self.call(), GOOD)
            body = json.loads(mock.call_args.args[0].data)
            self.assertEqual(mock.call_args.args[0].full_url, 'https://copa.codyssey.kr/v1/chat/completions')
            self.assertEqual(body['max_completion_tokens'], 1500)
            self.assertNotIn('response_format', body)
            self.assertNotIn('temperature', body)
            self.assertEqual(mock.call_args.kwargs['timeout'], 60)

    def test_http_errors_hide_body(self):
        for status in [400, 401, 403, 404, 429, 500]:
            error = urllib.error.HTTPError('url', status, 'secret', {}, io.BytesIO(b'secret'))
            with patch('urllib.request.urlopen', side_effect=error), self.assertRaises(api.APIError) as raised:
                self.call()
            self.assertNotIn('secret', str(raised.exception))
            self.assertIn(str(status), str(raised.exception))

    def test_network_timeout_and_malformed(self):
        for exc in [TimeoutError(), urllib.error.URLError('secret')]:
            with patch('urllib.request.urlopen', side_effect=exc), self.assertRaises(api.APIError):
                self.call()
        for body in [b'not json', b'{}', b'{"status":"incomplete"}', b'{"status":"completed","output":null}']:
            with patch('urllib.request.urlopen', return_value=io.BytesIO(body)), self.assertRaises(api.APIError):
                self.call()


if __name__ == '__main__':
    unittest.main()
