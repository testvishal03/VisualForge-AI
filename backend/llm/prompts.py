import json
import math
import re

SYSTEM_PROMPT = "You write accurate educational video scripts in simple English. Respond with one valid JSON object only."

FACTUAL_GUIDANCE = (
    "Keep related AI mechanisms distinct when relevant: retrieval finds existing reference information BEFORE an answer is generated; "
    "training changes model parameters. "
    "Retrieved information is supplied as context to the language model. Retrieval depends on source relevance and reliability, "
    "not simply on having a huge corpus. It does not guarantee a correct answer. An AI example must show how the model uses retrieved information to compose a response; a phrase bank alone is not the entire process. Use these distinctions only when relevant to the topic."
)


def factual_guidance(topic: str) -> str:
    if re.search(r"tokens?|tokeni[sz]|context window", topic, re.IGNORECASE):
        return ("Explain tokenizer-specific pieces and IDs; token counts are not word counts. "
                "Context is finite request information, not permanently learned weights. "
                "Distinguish input/output budgets, application truncation, summarization and retrieval. "
                "Never claim every runtime drops oldest messages or that larger context guarantees recall. "
                "Use an engaging opening question and end with a short recap. Keep illustrative counts explicitly hypothetical.")
    if re.search(r"\brag\b|retrieval[ -]+augmented[ -]+generation", topic, re.IGNORECASE):
        return FACTUAL_GUIDANCE
    if re.search(r"\b(llm|transformer|gpt|bert|tokeni[sz]|embedding|feedforward)\b", topic, re.IGNORECASE) \
            or re.search(r"large language model|language model|attention mechanism|self[- ]attention", topic, re.IGNORECASE):
        return (
            "Explain tokenisation, embedding spaces, attention weights, and feedforward layers as distinct mechanisms. "
            "Do not conflate training (weight updates via backpropagation) with inference (forward pass through the network). "
            "Do not claim models understand, know, or think - describe what the computation does. "
            "Attention computes weighted sums over sequence positions, not a human-like focus. "
            "Use established facts only; avoid invented claims about emergent behaviour."
        )
    if re.search(
        r"\b(neural network|deep learning|backpropagation|gradient descent|activation function|convolutional|recurrent|lstm|rnn|cnn)\b",
        topic, re.IGNORECASE,
    ):
        return (
            "Distinguish neurons, layers, weights, and activations clearly. "
            "Backpropagation computes gradients; gradient descent updates weights using those gradients. "
            "Do not claim neural networks work like the human brain. "
            "Describe what each layer computes, not anthropomorphic intent. "
            "Use established facts from the published literature."
        )
    if re.search(
        r"\b(quantum computing|qubit|superposition|entanglement|quantum gate|quantum algorithm|shor|grover)\b",
        topic, re.IGNORECASE,
    ):
        return (
            "Superposition means a qubit can be in a linear combination of basis states, not that it is classically both 0 and 1 simultaneously. "
            "Quantum speedup applies to specific problem classes, not all computation. "
            "Entanglement is a correlation between qubits, not faster-than-light communication. "
            "Use established complexity results; do not overstate quantum advantage."
        )
    if re.search(
        r"\b(sorting|algorithm|big.o|time complexity|space complexity|data structure|binary search|recursion|dynamic programming)\b",
        topic, re.IGNORECASE,
    ):
        return (
            "State time and space complexity accurately using established results (e.g. O(n log n) for merge sort). "
            "Show the algorithm's key decision or operation with a concrete small example. "
            "Do not invent complexity classes or claim optimality without basis."
        )
    if re.search(
        r"\b(machine learning|classification|regression|overfitting|underfitting|cross.validation|feature engineering|training data|test data)\b",
        topic, re.IGNORECASE,
    ):
        return (
            "Distinguish training data, model parameters, and inference clearly. "
            "Overfitting means the model has memorised noise in the training data, reducing generalisation. "
            "Describe what each technique actually computes; avoid anthropomorphic framing. "
            "Use established facts only."
        )
    return "Use established facts and explain the actual mechanism. Keep related concepts distinct. Avoid invented claims and guarantees."


def normalize_topic(topic: str) -> str:
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("Topic must not be empty or whitespace-only.")
    topic = ' '.join(topic.strip().split())
    if len(topic) > 500:
        topic = topic[:497] + '...'
    return topic


def scene_count(target_duration_minutes: float) -> int:
    if not math.isfinite(target_duration_minutes) or not 0.5 <= target_duration_minutes <= 4:
        raise ValueError("Target minutes must be between 0.5 and 4 for this small local model.")
    return max(3, min(12, round(target_duration_minutes * 4)))


def _structure_hint(topic: str) -> str:
    """Return a domain-specific scene-ordering suggestion to inject into the outline prompt."""
    if re.search(r"\b(llm|transformer|gpt|bert|embedding|attention)\b", topic, re.IGNORECASE) \
            or re.search(r"large language model|language model", topic, re.IGNORECASE):
        return (
            " Suggested scene flow for this topic: "
            "(1) what it is and why it matters, "
            "(2) how text becomes tokens and embeddings, "
            "(3) how attention selects relevant context, "
            "(4) what training does to the weights, "
            "(5) a concrete real-world use-case example, "
            "(6) key limitations and what it cannot do."
        )
    if re.search(r"\b(backprop|backpropagation)\b", topic, re.IGNORECASE) \
            or re.search(r"neural network|deep learning", topic, re.IGNORECASE):
        return (
            " Suggested scene flow: "
            "(1) what a single neuron computes, "
            "(2) how layers stack to build representations, "
            "(3) how backpropagation calculates gradients, "
            "(4) a concrete application such as image recognition or translation, "
            "(5) a common pitfall such as overfitting."
        )
    if re.search(r"\b(sorting|searching|algorithm|data structure)\b", topic, re.IGNORECASE):
        return (
            " Suggested scene flow: "
            "(1) the problem being solved, "
            "(2) the naive or brute-force approach and its cost, "
            "(3) the smarter approach and its key insight, "
            "(4) a step-by-step small example, "
            "(5) real-world uses."
        )
    return ""


def build_video_prompt(topic: str, target_duration_minutes: float = 2.0, audience: str = "beginner to intermediate") -> str:
    topic = normalize_topic(topic)
    count = scene_count(target_duration_minutes)
    order = ('Use exactly these three core points: scene 1 explains what it means; scene 2 explains how it works; scene 3 gives one concrete everyday example and ends with its takeaway. Scene 3 is the FINAL scene. Do not add a separate summary or fourth scene.'
             if count == 3 else 'Use four teaching points: meaning, mechanism, a concrete everyday example, and a takeaway. Do not add a fifth scene.'
             if count == 4 else 'Choose a logical order: meaning and context, mechanism, concrete everyday example, benefits, limitations, one final takeaway.')
    structure_hint = _structure_hint(topic)
    return f'''Plan a {target_duration_minutes:g}-minute educational video for a {audience} audience.
Topic: {json.dumps(topic, ensure_ascii=False)}
Create exactly {count} DIFFERENT teaching points, one per scene. The fixed scene count is the duration budget.
{order}{structure_hint} Each point must answer one useful viewer question and add new information. Move from a concrete problem to the mechanism, a worked example, and a useful conclusion. Reuse the same example where it helps connect adjacent points. Include a specific person doing a specific everyday task. Do not add separate lessons about other techniques mentioned in the accuracy guidance.
{factual_guidance(topic)}
Return ONLY one JSON object with exactly three keys: "title", "topic", "scenes". Each key appears ONCE. Put ALL scenes inside ONE "scenes" array. Never add a second array or repeat the "scenes" key.
"topic" must exactly equal {json.dumps(topic, ensure_ascii=False)}.
Each scene has ONLY "id" (integer starting at 1), "headline" (specific heading under 8 words), and "point" (one factual sentence to explain).
This is an outline, so do not write narration yet. No generic headings like "Concrete Example": name the actual example. No repeated points, hype, invented claims, or guarantees. End after the final scene, closing the array and object.'''


def build_scene_prompt(topic: str, scene: dict, field: str, body: str = "", word_range=(25, 40), audience='beginners', teaching_plan=None, previous_narration='') -> str:
    if field == "body":
        return f'''Write a short on-screen caption for this teaching point:
{scene['point']}
Audience: {json.dumps(audience)}.
Use 8 to 12 words in one sentence. Maximum 180 characters.
Return JSON with one key, like {{"body": ""}}, filling the string with your caption.'''
    if field != "narration":
        raise ValueError("Scene drafting field must be body or narration")
    context = (
        "Relevant references are retrieved first and passed as context to a language model, which generates an answer. Results depend on the sources and can be wrong."
        if re.search(r"\brag\b|retrieval[ -]+augmented[ -]+generation", topic, re.IGNORECASE)
        else factual_guidance(topic)
    )
    sentence_count = 'one or two' if word_range[1] <= 25 else 'two to four'
    return f'''You are speaking directly to an audience of {json.dumps(audience)} learning about {json.dumps(topic)}.
Background: {context}
Teaching sequence: {json.dumps(teaching_plan or [], ensure_ascii=False)}
Previous explanation: {json.dumps(previous_narration, ensure_ascii=False)}
Connect this point to the preceding explanation. Reuse its concrete example when relevant and avoid repeating its definition. Explain only the current point; later points have their own scenes.
Explain this one point: {scene['point']}
On-screen caption: {body}
Write {sentence_count} short spoken sentences, totaling {word_range[0]} to {word_range[1]} words. This word budget controls the video duration. Teach this point directly with useful detail: name the concrete input or situation, explain what changes and WHY, then give its observable consequence. Define a new technical term in plain language before using it. A worked example should show a small input, the operation, and the resulting output; mark hypothetical numbers as illustrative. If an analogy helps, state where it stops matching the real mechanism. Do not restate the caption or add rhetorical filler. Fit the existing word budget; depth comes from a specific cause and example, not extra words. For actual sequential steps, use First, Next, and Finally when accurate; do not force unrelated ideas into steps. Describe possible benefits using "can" or "may". Stop when this point is explained.
Return JSON with exactly one key: {{"narration": ""}}, filling the string with your spoken paragraph.'''


def build_retry_prompt(original: str, previous: str, failure: str, attempt: int = 2) -> str:
    return f'''{original}
Correction attempt {attempt}. Your previous response failed validation:
{failure[:1800]}
Write a fresh response that fixes these errors. Do not repeat earlier wording.
If a claim is too strong, replace it with a cautious statement using "may" and remove words such as "ensures" and "guarantees".
Return the entire corrected JSON object for this stage only. Keep all required fields.
'''
