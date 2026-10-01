import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.services.script_check import MODEL_PLANNING_LIMIT, check, phonemize, read_as_word

CLEAN = '\n\n'.join([
    'Embeddings turn meaning into numbers that AI systems can compare with each other.',
    'Think of embeddings as points in a huge mathematical space. If two concepts are similar in meaning, their vectors '
    'tend to be closer together. "Cat" and "Dog" may appear close together. "King" and "Queen" may also be close. '
    'But "Banana" may be much farther away from "Database."',
    'So embeddings let AI systems represent meaning as geometry and find the right information for every question.'])


def messages(report, level=None):
    return [i['message'] for i in report['issues'] if level is None or i['level'] == level]


class ScriptCheckTests(unittest.TestCase):
    def test_clean_script_reports_counts_and_planned_animations(self):
        report = check(CLEAN)
        self.assertEqual(messages(report, 'error') + messages(report, 'warning'), [])
        self.assertGreaterEqual(report['scenes'], 2)
        self.assertAlmostEqual(report['minutes'], report['words'] / 140, places=1)
        self.assertIn('embedding_map', [h['kind'] for h in report['highlights']])

    def test_spoken_symbols_and_stage_directions_are_flagged_with_a_fix(self):
        script = CLEAN + '\n\n' + ('Narrator: Pick a store. [pause] Chroma vs. Pinecone, e.g. for 10M vectors, see https://example.com -> pick one. '
                                   'It is a 50/50 call, and #1 costs $5 a month.')
        found = ' '.join(messages(check(script), 'warning'))
        for expected in ('square brackets', 'Speaker labels', '"vs."', '"e.g."', '"10M"', 'Web addresses', 'Arrows',
                         'Slashes', '"#1"', '"$5"'):
            self.assertIn(expected, found)

    def test_symbols_the_voice_reads_correctly_are_not_flagged(self):
        script = CLEAN + '\n\n' + 'Accuracy rose by 42% in 2026. Find the user where id = 42 & the score is 3.14 for C++ code.'
        self.assertEqual(messages(check(script), 'warning'), [])

    def test_long_unmatched_and_repeated_sentences(self):
        long_sentence = ' '.join(['word'] * 45) + '.'
        script = CLEAN + '\n\n' + long_sentence + ' He said "hello there.\n\n' + 'Embeddings turn meaning into numbers that AI systems can compare with each other.'
        found = ' '.join(messages(check(script)))
        self.assertIn('Long sentence (45 words)', found)
        self.assertIn('Unmatched quote', found)
        self.assertIn('also appears in scene 1', found)

    def test_errors_for_unusable_scripts(self):
        self.assertIn('Paste the words', messages(check('   '))[0])
        self.assertIn('Only 3 words', messages(check('Too short here.'))[0])

    def test_single_line_text_is_never_read_as_a_file_path(self):
        with tempfile.TemporaryDirectory() as d:
            secret = Path(d) / 'secret.txt'
            secret.write_text(' '.join(['private'] * 40), encoding='utf-8')
            report = check(str(secret))
        self.assertNotIn('private', json.dumps(report))

    def test_long_scripts_are_told_visuals_will_be_rule_based(self):
        paragraphs = [f'Topic {n} covers a separate idea about storage, search, ranking and filtering in enough words to stand alone as a scene.'
                      for n in range(MODEL_PLANNING_LIMIT + 4)]
        report = check('\n\n'.join(paragraphs))
        if report['scenes'] > MODEL_PLANNING_LIMIT:
            self.assertTrue(any('rule-based visuals' in m for m in messages(report, 'info')))

    def test_markdown_is_checked_after_conversion(self):
        report = check('# Embeddings\n\n- Embeddings turn meaning into numbers.\n- Similar ideas sit close together in space.\n'
                       '- Retrieval uses that geometry to find the right information for every question you ask.\n\n'
                       '## Search\n\nA query becomes a vector, and the database returns the closest chunks to answer it well.')
        self.assertTrue(report['converted'])
        self.assertNotIn('#', ' '.join(i.get('excerpt', '') for i in report['issues']))


@unittest.skipIf(phonemize('test') is None, 'voice phonemizer not installed')
class AcronymTests(unittest.TestCase):
    def test_acronyms_are_judged_in_their_own_sentence(self):
        self.assertTrue(read_as_word('ANN', 'It uses Approximate Nearest Neighbor search, or ANN.'))
        self.assertFalse(read_as_word('ANN', 'The query is compared with ANN search.'))
        self.assertFalse(read_as_word('LLM', 'The LLM answers.'))


class CheckScriptHTTPTests(unittest.TestCase):
    def test_endpoint_requires_token_and_returns_the_report(self):
        from backend.scripts.review_app import make_server
        with tempfile.TemporaryDirectory() as directory:
            server = make_server(0, directory=Path(directory)/'store')
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f'http://127.0.0.1:{server.server_port}'
            try:
                token = json.loads(urlopen(url + '/api/config', timeout=10).read())['token']
                def post(headers, body):
                    request = Request(url + '/api/check-script', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', **headers})
                    try:
                        with urlopen(request, timeout=30) as response:
                            return response.status, json.loads(response.read())
                    except HTTPError as exc:
                        exc.read()
                        return exc.code, None
                self.assertEqual(post({}, {'text': CLEAN})[0], 403)
                status, report = post({'X-Editor-Token': token}, {'text': CLEAN, 'title': 'Embeddings'})
                self.assertEqual(status, 200)
                self.assertEqual(report['title'], 'Embeddings')
                self.assertEqual(post({'X-Editor-Token': token}, {'text': 5})[0], 400)
            finally:
                server.editor_jobs.close()
                server.shutdown()
                server.server_close()


if __name__ == '__main__':
    unittest.main()
