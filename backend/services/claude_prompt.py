"""The prompt to give Claude for one episode: the visual-script rules plus the playlist's context.

The rules live in data/examples/claude-visual-prompt.md (everything after its "---" line), so the
prompt a person copies by hand and the one the studio builds are always the same.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / 'data/examples/claude-visual-prompt.md'
WORDS_PER_MINUTE = 140


def rules():
    text = TEMPLATE.read_text(encoding='utf-8')
    return text.split('\n---\n', 1)[1].strip()


def episode_prompt(topic, minutes=4, playlist=None, topics=(), audience='beginners'):
    """The full prompt for `topic`; with a playlist, Claude also gets the episode's place in the series."""
    topic = topic.strip()
    words = max(150, min(1600, round(minutes * WORDS_PER_MINUTE)))
    body = rules().replace('<TOPIC>', topic).replace('Audience: beginners.', f'Audience: {audience}.')
    body = body.replace('about <N> words (140 words is about 1 minute)', f'about {words} words (about {minutes:g} minutes)')
    topics = [t.strip() for t in topics if t.strip()]
    if not playlist or not topics:
        return body
    known = [t.casefold() for t in topics]
    index = known.index(topic.casefold()) if topic.casefold() in known else None
    lines = [f'SERIES CONTEXT',
             f'- This video is part of the YouTube playlist "{playlist}".']
    if index is not None:
        earlier, later = topics[:index], topics[index + 1:]
        lines.append(f'- It is episode {index + 1} of {len(topics)}: "{topic}".')
        if earlier:
            lines.append(f'- Earlier episodes covered: {"; ".join(earlier)}. Do not re-teach them; mention one in a single sentence only when it helps.')
        else:
            lines.append('- It is the first episode: open by saying what the whole playlist will teach, in one sentence.')
        if later:
            lines.append(f'- The next episode is "{later[0]}". End the recap paragraph with one sentence that sets it up.')
        else:
            lines.append('- It is the final episode: close the recap by connecting everything the playlist covered.')
    lines += ['- Keep the visual language identical across episodes: yellow = the model or main idea, cyan = data and inputs,',
              '  pink = outputs and predictions, green = correct or good, red = errors and risks. Reuse the same kind of',
              '  picture for the same idea in every episode (for example, data is always points on a plot).',
              f'- Use "{topic}" as the title idea in the first paragraph.']
    return body + '\n\n' + '\n'.join(lines)
