"""Create a reviewable teaching script without changing an existing episode."""
from pathlib import Path
import sys
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.services.editor_store import EditorStore, validate_document, quality
from backend.services.workspaces import Workspaces
from backend.services.choreography import compile_scene
from backend.services.script_generator import write_json_atomic

LESSON = [
('Why does a chatbot lose the thread?', 'Two ideas explain how text reaches a model.', 'Welcome to VisualForge AI. Tokens are the pieces a language model processes, and the context window limits the information available for a response. Together, these ideas explain why a long conversation can lose important details. Let us follow the text from your question to the answer.'),
('Text must become model input', 'A tokenizer converts text into a sequence.', 'Start with input text, such as a question typed into a chat box. A tokenizer converts that input text into tokens. The resulting sequence is the representation the model receives before further numerical processing. Text that looks simple to us can therefore occupy several positions in that sequence.'),
('Tokens are not always words', 'The vocabulary determines the pieces.', 'Tokens can represent whole words, word pieces, or punctuation. Spaces may also be included in a token piece. The boundaries depend on the tokenizer and its vocabulary, so counting words is not the same as counting tokens. There is no single universal conversion that works for every sentence and language.'),
('Watch a real tokenizer', 'The example uses the installed local model.', 'Consider the input text, "The sky is". Watch the tokenizer split this text into its measured token pieces. Now the token IDs appear below those pieces. These identifiers come from the installed local model, so another model may divide the same text differently and assign different identifiers.'),
('An identifier is not a definition', 'IDs select entries; embeddings provide representations.', 'Token IDs are identifiers in a vocabulary, not definitions of the text. The model maps tokens to numerical representations called embeddings. Those representations participate in the model computation. A larger identifier does not mean a word is more important, more positive, or more similar to another word.'),
('Different text uses different space', 'Measure with the tokenizer you actually use.', 'A tokenizer may represent a familiar phrase compactly while splitting unusual text into more tokens. Code, numbers, punctuation, and different languages can behave differently. When planning a request, measure its complete formatted input with the correct tokenizer rather than relying only on the visible word count.'),
('The context window', 'Available context is finite.', 'The context window is the bounded amount of sequence information available to the model during a request. Instructions, conversation history, and the current question can all occupy that space. Our diagram shows categories inside a boundary, not their measured sizes. Equal spacing here does not mean equal token counts.'),
('What goes into a request?', 'The application assembles the model input.', 'Instructions tell the model how to respond. Conversation history supplies earlier exchanges, and the current question adds the immediate task. The application packages these parts into model input. Extra formatting and special tokens can contribute to the total, so the visible chat text may not be the entire input.'),
('Documents also use context', 'Retrieved passages become part of the request.', 'Retrieved documents can add relevant evidence to the context window. They do not provide a separate unlimited channel to the model. Their text becomes part of the request alongside instructions and the current question. Selecting useful passages matters because irrelevant material consumes space and can distract from the task.'),
('Leave room for the answer', 'Input capacity and output limits must be checked.', 'The generated answer also needs an output budget. For many autoregressive models, input tokens and generated tokens share a total sequence limit, while a service may impose additional output limits. Check the particular model and runtime. Do not assume every advertised context size permits an equally long answer.'),
('A small planning example', 'A toy budget makes the tradeoff visible.', 'Imagine a toy model with a context window of 1,000 tokens. Reserve 200 tokens for the generated answer, leaving at most 800 tokens for input under that shared limit. These numbers illustrate a budget calculation only. They are not the limits of the model running on your laptop.'),
('Growth across a conversation', 'History competes with the next question.', 'Conversation history grows as messages and answers accumulate. If the application includes that entire history again, it occupies more of the context window on the next request. A short current question can therefore produce a large input. What matters is the assembled request, not only the latest message.'),
('What happens at the boundary?', 'The application decides how to handle excess input.', 'When a request exceeds the context window, behavior depends on the application and runtime. It may reject the request, shorten it, or select a smaller subset. A sliding-window diagram is only one possible policy. There is no universal rule that every chatbot silently removes its oldest message.'),
('Watch information leave the request', 'One explicit truncation policy, not universal behavior.', 'Suppose an application chooses to remove older messages. Those older messages move outside the context window for this request, while the current question remains inside. The removed detail is no longer directly supplied to the model. This can explain why a previous instruction stops influencing the answer.'),
('Context is not permanent memory', 'Visible input and learned parameters are different.', 'The context window contains information supplied for the current computation. Model weights contain parameters learned during training. Adding a message to the context window does not ordinarily update those model weights. Keeping these mechanisms separate prevents the mistaken idea that every conversation permanently teaches the underlying model new facts.'),
('Applications can store information separately', 'Stored data must be supplied again when needed.', 'Persistent memory is an application feature when information is stored outside the immediate request. To affect a later answer, relevant evidence generally needs to be selected and supplied again. A database can retain a detail even when it is absent from the current context window. Storage and active context are different.'),
('Long context does not guarantee recall', 'Capacity does not prove reliable use.', 'A larger context window allows more input, but it does not guarantee reliable use of every detail. Relevant evidence may be surrounded by distracting or contradictory text. Performance depends on the model, the task, and the placement and quality of information. More available space is not a substitute for clear instructions.'),
('Keep the task explicit', 'State the question and relevant constraints clearly.', 'Make the current question specific and keep instructions consistent. Include relevant evidence that supports the task, and remove unrelated material when possible. This helps the application use its context window purposefully. It does not guarantee a correct answer, so important outputs still need checking against the supplied evidence.'),
('Summaries compress with tradeoffs', 'A summary saves space but may omit details.', 'A summary can replace some conversation history with a shorter description. That creates room in the context window, but compression may omit details or introduce errors. Preserve essential requirements and verify the summary. Treat it as a useful working note rather than a perfect copy of the original conversation.'),
('Retrieval selects instead of including everything', 'Bring in relevant evidence for each question.', 'Retrieval searches stored material for relevant evidence before the answer is generated. The selected passages enter the context window with the current question. This is useful when all available documents would be too large to include. Retrieval quality still matters: selecting an unrelated passage will not make the answer reliable.'),
('Follow one support question', 'Relevant evidence connects the request to a source.', 'Imagine asking a company assistant about its leave policy. The current question identifies the task, and retrieval selects relevant evidence from the policy documents. Those passages enter the context window. The model then generates an answer using the supplied input; it should not invent a policy that the evidence does not support.'),
('Generation extends the sequence', 'Each new token changes the available sequence.', 'During generation, the model predicts a next token from the available sequence, then appends that token. The updated sequence conditions the following prediction. A generated answer emerges through repeated steps. This process is distinct from retrieving a stored document or changing model weights through training.'),
('Try a useful comparison', 'Check the effect of including the missing detail.', 'To investigate a lost detail, compare two requests with the same current question. Supply the relevant evidence explicitly in one request and omit it from the other. Inspect whether the answers differ, while remembering that generation settings can also affect results. This experiment illustrates context dependence, not a guarantee about every model.'),
('Recap: pieces, capacity, selection', 'Three distinctions to remember.', 'To recap, tokens are the pieces used to represent text. The context window bounds the sequence available for a request. Relevant evidence must actually reach that request to be directly available during generation. Token counting, context management, and checking the answer are separate jobs that work together.'),
('See it, understand it, build it', 'Continue from tokens to numerical representations.', 'Thanks for watching VisualForge AI. Tokens identify text pieces, while the context window limits the information available at a time. Next, embeddings explain how token identities become numerical representations. Subscribe for more explanations that connect each visual demonstration to the idea being spoken.'),
]


def make_document():
    document={'title':'Tokens and Context Windows','topic':'Tokens and Context Windows','scenes':[]}
    for title,body,narration in LESSON:
        scene={'uid':uuid.uuid4().hex[:12],'headline':title,'body':body,'narration':narration,'visual':{'kind':'explanation','items':[],'directed':True}}
        spec=compile_scene(scene)
        if spec:scene['visual']['choreography']=spec
        document['scenes'].append(scene)
    example=document['scenes'][3]
    example['visual']={'kind':'example','items':[],'directed':True,'worked':{'input':'The sky is','label':'Local tokenizer example','steps':[{'action':'tokens','sentence':1},{'action':'ids','sentence':2}]}}
    validate_document(document)
    return document


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    marker=root/'data/tokens-director-project.txt'
    if marker.exists():
        print(marker.read_text().strip());sys.exit(0)
    document=make_document()
    store=EditorStore(root/'data/editor');spaces=Workspaces(store)
    project=store.create(document['topic'],document,source={'mode':'script','automatic':True,'approval_required':True,'profile':'draft','minutes':sum(len(s['narration'].split()) for s in document['scenes'])/135,'minimum_seconds':0})
    workspace=spaces.create({'name':'Tokens and Context Windows - Visual director','kind':'single','brand':'VISUALFORGE AI','show_intro':True,'show_outro':True})
    spaces.attach(workspace['id'],project['id'])
    marker.write_text(project['id'],encoding='utf-8')
    write_json_atomic(store.folder(project['id'])/'quality.json',quality(document))
    (root/'data/tokens-context-script.md').write_text('# Tokens and Context Windows\n\n'+'\n\n'.join('## '+s['headline']+'\n\n'+s['narration'] for s in document['scenes']),encoding='utf-8')
    print(project['id'])
