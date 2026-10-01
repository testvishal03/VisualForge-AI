"""A quiet, generated music bed under the narration, ducked whenever someone is speaking.

The bed is synthesized here (soft sine chords with slow swells), so it is deterministic and has
no licensing questions. Under speech it sits about 24 dB below the levelled narration (voice RMS
0.1, bed 0.006): on a real 25-scene video the worst scene's narration correlation stayed at 0.994,
against the render check's 0.98 (0.987 at a 0.01 bed was too close). In the intro, the outro and
longer pauses it rises a little. Short sentence pauses stay ducked, so
the bed never pumps between sentences.
"""
import numpy as np

# I - vi - IV - V in C, voiced low and close, one chord every eight seconds.
CHORDS = [(130.81, 164.81, 196.00, 246.94), (110.00, 130.81, 164.81, 196.00),
          (87.31, 130.81, 174.61, 220.00), (98.00, 123.47, 146.83, 196.00)]
CHORD_SECONDS = 8.0
CROSSFADE = 2.0
UNDER_SPEECH, IN_GAPS = .006, .018   # target RMS of the bed
ATTACK, RELEASE = .08, 1.6            # seconds: duck fast, recover slowly
FADE_IN, FADE_OUT = 2.0, 3.0


def bed(seconds, rate):
    """Unit-RMS chord pad of `seconds`, identical for the same length and rate."""
    n = max(1, round(seconds * rate))
    t = np.arange(n) / rate
    out = np.zeros(n)
    chord_len, overlap = round(CHORD_SECONDS * rate), round(CROSSFADE * rate)
    for index, start in enumerate(range(0, n, chord_len)):
        end = min(n, start + chord_len + overlap)
        local = t[start:end] - t[start]
        # Equal-power crossfade: this chord fades in while the previous one fades out, so the
        # level stays steady across chord changes instead of dipping every few seconds.
        gain = np.ones(end - start)
        if index:
            rise = min(overlap, end - start)
            gain[:rise] = np.sin(np.pi / 2 * np.arange(rise) / overlap)
        tail = end - (start + chord_len)
        if tail > 0:
            gain[-tail:] *= np.cos(np.pi / 2 * np.arange(tail) / overlap)
        # A slow breath keeps the held chord from sounding static.
        gain *= 1 + .12 * np.sin(2 * np.pi * local / 5.3)
        for k, f in enumerate(CHORDS[index % len(CHORDS)]):
            out[start:end] += gain * (np.sin(2 * np.pi * f * local + k) + .18 * np.sin(4 * np.pi * f * local + 2 * k)) / (1 + .35 * k)
    rms = np.sqrt(np.mean(out ** 2))
    return out / rms if rms else out


def envelope(voice, rate):
    """Per-sample bed level: UNDER_SPEECH while speaking (including short pauses), IN_GAPS otherwise."""
    block = max(1, rate // 100)
    padded = np.pad(np.abs(voice), (0, (-len(voice)) % block))
    speaking = (padded.reshape(-1, block).max(axis=1) > .01).astype(float)
    level = np.empty_like(speaking)
    current, up, down = 0.0, 1 - np.exp(-1 / (ATTACK * 100)), 1 - np.exp(-1 / (RELEASE * 100))
    for i, target in enumerate(speaking):
        current += (target - current) * (up if target > current else down)
        level[i] = current
    level = np.repeat(level, block)[:len(voice)]
    return IN_GAPS + (UNDER_SPEECH - IN_GAPS) * level


def mix(voice, rate):
    """Narration with the music bed added underneath; the voice samples themselves are unchanged."""
    voice = np.asarray(voice, dtype=float)
    music = bed(len(voice) / rate, rate) * envelope(voice, rate)
    fade = np.ones(len(voice))
    fi, fo = min(len(voice), round(FADE_IN * rate)), min(len(voice), round(FADE_OUT * rate))
    fade[:fi] = np.linspace(0, 1, fi)
    if fo:
        fade[-fo:] = np.minimum(fade[-fo:], np.linspace(1, 0, fo))
    return np.clip(voice + music * fade, -1, 1)
