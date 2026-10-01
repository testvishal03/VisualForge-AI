import re
import unittest

from backend.services.director import build_direction, script_to_video
from backend.services.editor_store import document_from_video
from backend.services.explainers import plan
from backend.services.page_script import page_to_script

PAGE = '''# Generative AI, explained.

The tech that makes text, pics, music & code out of thin air. Kinda. Let's break it down.

## Old AI judges. Gen AI creates.

**Old-school AI**"Is this pic a cat or a dog?"\\
Sorts stuff into boxes.

→

**Generative AI**"Draw me a cat in a hoodie."\\
Makes brand new stuff.

## Secret: it's a next-word guesser

the cat sat on the

It picks the most likely next piece (a "token"), then repeats. Thousands of times. That's a whole essay.

## How it gets so good

**1. Feed it**Billions of texts, images, code

→

**2. It finds patterns**Millions of tiny dials (parameters) get tuned

→

**3. You prompt it**It remixes patterns into something new

## Images? Noise → art

prompt: "a heart"

Image models start with static and clean it up step by step until it matches your prompt.

## Real talk, though

**It can be wrong**Confidently making stuff up = "hallucination"

**It copies bias**Learns from human data, flaws included

**You're the editor**Fact-check it. Add your own taste. ✨
'''


class PageScriptTests(unittest.TestCase):
    def setUp(self):
        self.result = page_to_script(PAGE)
        self.script = self.result['script']

    def test_markdown_becomes_clean_speech_in_the_authors_words(self):
        self.assertEqual(self.result['title'], 'Generative AI, explained')
        for symbol in ('**', '#', '→', '✨', '\\\\', '&'):
            self.assertNotIn(symbol, self.script, f'{symbol!r} would be read aloud or is markup')
        for phrase in ('Sorts stuff into boxes.', 'Makes brand new stuff.', 'It picks the most likely next piece',
                       'Image models start with static and clean it up step by step', 'Learns from human data, flaws included.'):
            self.assertIn(phrase, self.script, 'the author’s sentences are kept')
        self.assertIn('music and code', self.script)

    def test_steps_examples_and_quotes_read_naturally(self):
        self.assertRegex(self.script, r'First, feed it\. Billions of texts, images, code\.')
        self.assertIn('Next, it finds patterns.', self.script)
        self.assertIn('Finally, you prompt it.', self.script)
        self.assertIn('For example, "the cat sat on the".', self.script)
        self.assertIn('Prompt: "a heart".', self.script)
        self.assertIn('Old-school AI: "Is this pic a cat or a dog?"', self.script)

    def test_each_section_becomes_a_scene_with_its_explainer(self):
        video = script_to_video(self.result['title'], self.script)
        document = document_from_video(video, build_direction(video))
        kinds = [(plan(s) or {}).get('kind') for s in document['scenes']]
        self.assertEqual(kinds, [None, 'contrast', 'next_token', 'steps', 'denoise', 'caveats'])
        self.assertEqual(self.result['scenes'], len(document['scenes']))

    def test_short_sections_join_the_next_and_empty_input_is_rejected(self):
        result = page_to_script('# T\n\n## Hi\n\nShort.\n\n## Main idea\n\nThis section has plenty of words to stand on its own as a scene today.')
        self.assertEqual(result['scenes'], 1)
        self.assertTrue(result['script'].startswith('Hi. Short. Main idea.'))
        for bad in ('', '   ', '# Only a title'):
            with self.assertRaises(ValueError):
                page_to_script(bad)


class PageScriptHTTPTests(unittest.TestCase):
    def test_endpoint_requires_token_and_returns_narration(self):
        import json, tempfile, threading
        from pathlib import Path
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen
        from backend.scripts.review_app import make_server
        with tempfile.TemporaryDirectory() as directory:
            server = make_server(0, directory=Path(directory)/'store')
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f'http://127.0.0.1:{server.server_port}'
            try:
                token = json.loads(urlopen(url + '/api/config', timeout=10).read())['token']
                def post(headers):
                    request = Request(url + '/api/page-to-script', data=json.dumps({'text': PAGE}).encode(),
                                      headers={'Content-Type': 'application/json', **headers})
                    try:
                        with urlopen(request, timeout=10) as response:
                            return response.status, json.loads(response.read())
                    except HTTPError as exc:
                        return exc.code, None
                self.assertEqual(post({})[0], 403)
                status, result = post({'X-Editor-Token': token})
                self.assertEqual(status, 200)
                self.assertTrue(re.search(r'Finally, you prompt it', result['script']))
            finally:
                server.editor_jobs.close()
                server.shutdown()
                server.server_close()


if __name__ == '__main__':
    unittest.main()


PRODUCTION = '''# Vector Databases — How AI Searches by Meaning

**VisualForge AI — Generative AI Series**
**Video 5 \| Target duration: 8–10 minutes**

------------------------------------------------------------------------

## Scene 1 — Hook

**Voiceover**

Imagine you have 100,000 documents.

A user asks:

“What is our work-from-home policy?”

How can an AI system find the right information from all those documents
in just a few moments?

In this video, we’ll understand what a vector database is and how vector search works.

**Visual**

Show a huge stack of documents with a search bar.

## Scene 2 — Options

**Voiceover**

Examples include:

Pinecone.

Weaviate.

```
User Query
    ↓
Answer
```

## Key Takeaway

> **Embeddings represent meaning.**
> **Vector databases make those representations searchable.**
'''


class ProductionScriptTests(unittest.TestCase):
    def test_only_the_voiceover_is_read(self):
        result = page_to_script(PRODUCTION)
        script = result['script']
        self.assertEqual(result['title'], 'Vector Databases — How AI Searches by Meaning')
        for silent in ('Target duration', 'Scene 1', 'Hook', 'Voiceover', 'Show a huge stack', 'User Query', '↓'):
            self.assertNotIn(silent, script)
        self.assertIn('A user asks: "What is our work-from-home policy?"', script)
        self.assertIn('from all those documents in just a few moments?', script, 'wrapped lines are rejoined')
        self.assertIn('Examples include: Pinecone.', script)
        self.assertIn('Embeddings represent meaning. Vector databases make those representations searchable.', script)
        self.assertIn("In this video, we'll understand", script, 'the author’s own introduction is kept')
        self.assertTrue(any('Production script' in n for n in result['notes']))

    def test_markdown_is_detected_but_plain_scripts_are_not(self):
        from pathlib import Path
        from backend.services.page_script import looks_like_markdown
        self.assertTrue(looks_like_markdown(PRODUCTION))
        self.assertTrue(looks_like_markdown(PAGE))
        root = Path(__file__).resolve().parents[2]
        self.assertFalse(looks_like_markdown((root/'data/examples/generative-ai-explained.txt').read_text(encoding='utf-8')))
        self.assertFalse(looks_like_markdown('A user asks: what is a vector?\n\nThe answer is embeddings.'))


class ScriptImportRegressionTests(unittest.TestCase):
    def test_number_lists_never_break_headlines_and_filler_openings_do_not_become_titles(self):
        from backend.schemas.video_schema import words
        from backend.services.director import headline_for, script_to_video
        self.assertLessEqual(len(words(headline_for('0.21, 0.84, minus 0.13, 0.52, 0.77, and so on.'))), 10)
        script = ('In the previous video, we learned that text becomes tokens before a model can process it.\n\n'
                  'An embedding converts a word or sentence into a list of numbers called a vector.\n\n'
                  '0.21, 0.84, minus 0.13, 0.52, 0.77, 0.12, and so on. A real embedding can contain hundreds of values.\n\n'
                  'Similar embeddings sit close together, so embeddings let us compare meaning with geometry.')
        video = script_to_video(None, script)
        self.assertIn(video.title, ('Embedding', 'Embeddings'), 'the most-mentioned concept, in its most frequent form')
        self.assertEqual(video.scenes[2].headline, 'A real embedding can contain hundreds of values')


if __name__ == '__main__':
    unittest.main()
