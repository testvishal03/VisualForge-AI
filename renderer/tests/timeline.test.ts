import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {test} from 'node:test';
import {buildTimeline, FPS, SCENE_END_PADDING_SECONDS, validateVideoData} from '../src/timeline.ts';
import {environmentFor} from '../src/motion.ts';
import {activeWord,captionPhrases,sceneTransition,palette} from '../src/presentation.ts';
import {BRIDGE_HEADLINE_DELAY,BRIDGE_SECONDS,bridgedFrom,carriedLabels,lightCard,lightVideo,ENTER_SECONDS,enterProgress,EXIT_SECONDS,exitProgress,sceneSeconds,teaserWindow} from '../src/transitions.ts';
import {idleOffset,mentionPulse,mentionTimes,sceneDrift} from '../src/emphasis.ts';
import {fitLabel,objectScale,textWidth} from '../src/labels.ts';
import {along,chipKind} from '../src/flow.ts';
import {after,chipRows,inside,mapLayout,measuredLayout,noise} from '../src/explainer.ts';
import {iconFor} from '../src/icon-match.ts';
import {animationTiming,activeConcept,sharedConcept} from '../src/animation.ts';
import {isContextWindow,contextCues} from '../src/context-window.ts';
import {validateTeaching,teachingStage,type TeachingPlan} from '../src/teaching-plan.ts';
import {validateCodeExample,demonstrationStep} from '../src/code-example.ts';
import type {Scene} from '../src/types.ts';
import {semanticMotion,semanticProgress,semanticTransition,meaningGroups,validateVisualPlan} from '../src/semantic-motion.ts';

test('reviewed visual plans drive the renderer and reject mismatched narration cues',()=>{
  const scene:Scene={id:1,headline:'Tokens',body:'Text becomes tokens.',narration:'Text becomes tokens.',audio:'audio/scene-1.wav',duration:3,
    visual:{kind:'explanation',items:[],directed:true},beats:[{text:'Text becomes tokens.',start:0,end:3}],
    visualPlan:{kind:'tokens',title:'Text becomes tokens',view:'overview',carry:null,objects:['tokens'],steps:[{sentence:0,action:'split',text:'Text becomes tokens.'}],at:[0],transition:'fade'}};
  validateVisualPlan(scene);assert.equal(semanticMotion(scene),'tokens');
  for(const kind of ['context','attention','generation','vector-database']){scene.visualPlan!.kind=kind;assert.equal(semanticMotion(scene),kind);}
  scene.visualPlan!.at[0]=1;assert.throws(()=>validateVisualPlan(scene),/measured narration/);
  scene.visualPlan!.at[0]=0;scene.visualPlan!.objects=['invented'];assert.throws(()=>validateVisualPlan(scene),/objects/);
});

test('visual mechanisms follow narration rather than a repeated card or topic title',()=>{
  const scene=(narration:string)=>({id:1,body:'Example explanation',audio:'audio/example.wav',narration,headline:'Embeddings',duration:10,visual:{kind:'explanation',items:[],directed:true}} as Scene);
  assert.equal(semanticMotion(scene('An embedding converts text into a numerical vector.')),'encoding');
  assert.equal(semanticMotion(scene('Embedding vectors occupy a space where related meanings are closer.')),'meaning-space');
  assert.equal(semanticMotion(scene('Embedding vectors can have hundreds of dimensions.')),'dimensions');
  assert.equal(semanticMotion(scene('Semantic search compares the query with the closest matches.')),'retrieval');
  assert.equal(semanticMotion(scene('RAG retrieves documents into context before the language model answers.')),'rag');
  assert.equal(semanticMotion(scene('Water condenses into clouds and rain falls.')),undefined);
  const authored=scene('An embedding converts text into numbers.');authored.visual!.kind='chart';
  assert.equal(semanticMotion(authored),undefined);
  const timed=scene('Embedding vectors encode text.');timed.beats=[{text:timed.narration,start:3,end:7}];
  assert.equal(semanticProgress(timed,2,/vector/),0);
  assert.equal(semanticProgress(timed,5,/vector/),.5);
  assert.equal(semanticProgress(timed,9,/vector/),1);
  timed.beats.push({text:'Compare vectors.',start:8,end:10});
  assert.equal(semanticProgress(timed,6.5,/vector/),.5);
  assert.deepEqual(meaningGroups(scene('King and queen have related embeddings, unlike a banana.')),['banana','king / queen']);
  assert.equal(semanticTransition('meaning-space','meaning-space'),'continuous');
  assert.equal(semanticTransition('dimensions','encoding'),'zoom');
});

test('computed Python and SQL traces reject changed results and code',()=>{
  const fixtures:Scene[]=JSON.parse(readFileSync(new URL('./computed-examples.json',import.meta.url),'utf8'));
  for(const fixture of fixtures){
    validateCodeExample(fixture);
    assert.equal(demonstrationStep(fixture.demonstration!,100),fixture.demonstration!.steps.length-1);
    const corrupted=structuredClone(fixture);
    corrupted.demonstration!.steps[0].line=99;
    assert.throws(()=>validateCodeExample(corrupted),/computed Python/);
    const wrongCode=structuredClone(fixture);wrongCode.demonstration!.code[0]='different code';
    assert.throws(()=>validateCodeExample(wrongCode),/computed Python/);
    const wrongResult=structuredClone(fixture);
    if(wrongResult.demonstration!.output)wrongResult.demonstration!.output=['999'];
    else wrongResult.demonstration!.rows=[];
    assert.throws(()=>validateCodeExample(wrongResult),/computed Python/);
  }
});

test('teaching demos require source cues and accurately calculated illustrative data',()=>{
  const plan:TeachingPlan={version:1,component:'vector_search',question:'How are vectors compared?',objective:'Compare vector direction.',takeaway:'Cosine similarity compares directions.',evidence:'illustrative',
    steps:[{sentence:0,action:'encode',label:'vector'},{sentence:1,action:'compare',label:'similarity'}],at:[0,3],
    example:{query:[1,0],points:[{label:'A',vector:[1,0],cosine:1},{label:'B',vector:[.8,.6],cosine:.8},{label:'C',vector:[0,1],cosine:0}],metric:'cosine',provenance:'illustrative'}};
  const sample={id:1,duration:6,headline:'Vector comparison',body:'Compare directions.',narration:'An embedding is a vector. Cosine similarity compares directions.',audio:'audio/scene-1.wav',teaching:plan,
    beats:[{text:'An embedding is a vector.',start:0,end:3},{text:'Cosine similarity compares directions.',start:3,end:6}]};
  validateTeaching(sample);
  assert.equal(teachingStage(plan,2),0);assert.equal(teachingStage(plan,3),1);
  const bad=structuredClone(sample);bad.teaching.example!.points[1].cosine=.9;
  assert.throws(()=>validateTeaching(bad),/teaching plan/);
  const wrongCue=structuredClone(sample);wrongCue.teaching.at[1]=4;
  assert.throws(()=>validateTeaching(wrongCue),/teaching plan/);
  const invented=structuredClone(sample);invented.teaching.steps[0].label='invented fact';
  assert.throws(()=>validateTeaching(invented),/teaching plan/);
});

test('context inventory requires named categories and preserves shared sentence cues',()=>{
  const example={id:1,duration:10,headline:'Shared context',body:'Input and output share available space.',audio:'audio/test.wav',narration:'The context contains input tokens and output tokens.',visual:{kind:'components' as const,items:['input tokens','output tokens'],revealAt:[2,2]}};
  assert.equal(isContextWindow(example),true);
  assert.deepEqual(contextCues(example),[2,2]);
  assert.equal(isContextWindow({...example,narration:'A library contains books.'}),false);
  assert.equal(isContextWindow({...example,visual:{...example.visual,items:['unrelated object','output tokens']}}),false);
});

const generated: unknown = JSON.parse(readFileSync(new URL('../../data/video.generated.json', import.meta.url), 'utf8'));
const source = JSON.parse(readFileSync(new URL('../../data/video.json', import.meta.url), 'utf8'));
const scene = (id: number, duration: number) => ({id, duration, headline: 'Title', body: 'Description', narration: 'Spoken text.', audio: `audio/scene-${id}.wav`});

test('animation pacing respects distinct sentence cues and leaves audio timeline unchanged',()=>{
  const s={...scene(1,10),visual:{kind:'process' as const,items:['Input','Transform','Output'],revealAt:[0,3,7],motion:'assemble' as const}};
  assert.deepEqual(animationTiming(s),[0,3,7]);assert.equal(activeConcept(s,4),1);
  const paced=animationTiming({...s,visual:{...s.visual,revealAt:[0,0,0]}});
  assert.ok(paced[0]<paced[1]&&paced[1]<paced[2]&&paced[2]<s.duration);
  for(const motion of ['flow','assemble','focus','reveal'] as const){
    assert.equal(buildTimeline({title:'Motion',scenes:[{...s,visual:{...s.visual,motion}}]},30).durationInFrames,315);
  }
});

test('subject illustrations preserve charts and distinguish cloud computing from weather',()=>{
  const base=scene(1,10);
  assert.equal(environmentFor({...base,headline:'Cloud computing',narration:'Remote servers process requests.'}),null);
  assert.equal(environmentFor({...base,headline:'Roots absorb water',narration:'Water eventually forms clouds.'}),'plant');
  assert.equal(environmentFor({...base,headline:'Surface runoff',narration:'Rain falls before water reaches soil.'}),'ground');
  assert.equal(environmentFor({...base,headline:'Rainfall',narration:'Water droplets fall.'}),'rain');
  assert.equal(environmentFor({...base,headline:'Water use',visual:{kind:'chart',items:['Homes','Farms'],values:[30,70]}}),null);
  assert.equal(environmentFor({...base,headline:'Surface runoff',narration:'Rain falls before water reaches soil.',visual:{kind:'relationship',items:['Rain','Soil'],planned:true}}),null);
});

test('visual layouts preserve audio timing and reject malformed diagram data', () => {
  const base = scene(1, 4.125);
  const layouts = [
    {kind: 'title', items: []}, {kind: 'explanation', items: []},
    {kind: 'process', items: ['Input', 'Transform', 'Output']},
    {kind: 'comparison', items: ['Benefits', 'Limitations']},
    {kind: 'example', items: []}, {kind: 'takeaway', items: []},
  ];
  for (const visual of layouts) {
    const data = {title: 'Layouts', scenes: [{...base, visual}]};
    validateVideoData(data);
    assert.equal(buildTimeline(data, FPS).durationInFrames, Math.ceil(4.625*FPS));
  }
  for (const visual of [{kind: 'unknown', items: []}, {kind: 'process', items: ['Only one']}, {kind: 'comparison', items: ['', 'B']}]) {
    assert.throws(() => validateVideoData({title: 'Bad visual', scenes: [{...base, visual}]}), /visual/);
  }
});

test('generated scene metadata matches source and real WAV sample counts', () => {
  validateVideoData(generated);
  assert.equal(generated.scenes.length, source.scenes.length);
  assert.ok(generated.scenes.length > 0);
  generated.scenes.forEach((item, index) => {
    const input = source.scenes[index];
    for (const key of ['id', 'headline', 'body', 'narration'] as const) assert.equal(item[key], input[key]);
    const path = new URL(`../public/${item.audio}`, import.meta.url);
    assert.ok(existsSync(path), `Missing ${item.audio}`);
    const wav = readFileSync(path);
    assert.equal(wav.toString('ascii', 0, 4), 'RIFF');
    assert.equal(wav.toString('ascii', 8, 12), 'WAVE');
    let bytesPerSecond = 0;
    let dataBytes = 0;
    for (let offset = 12; offset + 8 <= wav.length;) {
      const name = wav.toString('ascii', offset, offset + 4);
      const size = wav.readUInt32LE(offset + 4);
      assert.ok(offset + 8 + size <= wav.length, 'WAV chunk is truncated');
      if (name === 'fmt ') bytesPerSecond = wav.readUInt32LE(offset + 16);
      if (name === 'data') dataBytes = size;
      offset += 8 + size + (size % 2);
    }
    assert.ok(dataBytes > 0 && bytesPerSecond > 0);
    assert.equal(item.duration, dataBytes / bytesPerSecond);
  });
});

test('audio-aware scenes are contiguous with complete narration and end padding', () => {
  validateVideoData(generated);
  const timeline = buildTimeline(generated, FPS);
  let expectedStart = 0;
  timeline.scenes.forEach(({scene: item, from, durationInFrames}) => {
    assert.equal(from, expectedStart);
    assert.ok(durationInFrames / FPS >= item.duration + SCENE_END_PADDING_SECONDS);
    assert.ok(durationInFrames / FPS < item.duration + SCENE_END_PADDING_SECONDS + 1 / FPS);
    expectedStart += Math.ceil((item.duration + SCENE_END_PADDING_SECONDS) * FPS);
  });
  assert.equal(timeline.durationInFrames, expectedStart);
});

test('arbitrary scene counts, narration lengths and FPS use upward rounding', () => {
  for (const fps of [24, 30, 60]) {
    const scenes = [scene(1, 1.001), scene(2, 2.25), scene(3, 3), scene(4, 0.1)];
    const timeline = buildTimeline({title: 'Custom', scenes}, fps);
    assert.equal(timeline.scenes.length, 4);
    assert.equal(timeline.durationInFrames, scenes.reduce((sum, s) => sum + Math.ceil((s.duration + SCENE_END_PADDING_SECONDS) * fps), 0));
    const longer = buildTimeline({title: 'Longer', scenes: [scene(1, 10), ...scenes.slice(1)]}, fps);
    assert.ok(longer.scenes[1].from > timeline.scenes[1].from);
  }
});

test('invalid inputs fail before rendering', () => {
  assert.throws(() => buildTimeline({title: 'Empty', scenes: []}, FPS), /at least one/);
  assert.throws(() => buildTimeline({title: 'Duplicate', scenes: [scene(1, 1), scene(1, 2)]}, FPS), /unique/);
  for (const duration of [0, -1, NaN, Infinity]) assert.throws(() => buildTimeline({title: 'Bad', scenes: [scene(1, duration)]}, FPS), /positive/);
  for (const narration of ['', ' ', undefined]) assert.throws(() => validateVideoData({title: 'Bad', scenes: [{...scene(1, 1), narration}]}), /narration/);
  for (const audio of ['', '../secret.wav', 'https://host/a.wav', 'C:\\scene.wav']) assert.throws(() => validateVideoData({title: 'Bad', scenes: [{...scene(1, 1), audio}]}), /audio/);
});

test('directed reveals use measured sentence boundaries without changing audio scheduling', () => {
  const directed = {...scene(1, 3.24), narration:'First sentence. Second sentence. Third sentence.',
    beats:[{text:'First sentence.',start:0,end:1},{text:'Second sentence.',start:1.12,end:2.12},{text:'Third sentence.',start:2.24,end:3.24}],
    visual:{kind:'process' as const,items:['Input','Work','Result'],directed:true,revealAt:[0,1.12,2.24]}};
  const data={title:'Directed',scenes:[directed]};
  assert.equal(buildTimeline(data,30).durationInFrames,113);
  for (const times of [[0,1,2.24],[0,2.24,1.12],[0,1.12,9]]) {
    assert.throws(()=>validateVideoData({...data,scenes:[{...directed,visual:{...directed.visual,revealAt:times}}]}),/reveal timing/);
  }
  assert.throws(()=>validateVideoData({...data,scenes:[{...directed,beats:directed.beats.slice(1)}]}),/beats/);
  validateVideoData({...data,scenes:[{...directed,visual:{kind:'relationship',items:['Cause','leads to effect'],directed:true,revealAt:[0,0]}}]});
});

test('new diagrams validate their geometry inputs and retain the exact speech timeline',()=>{
  for(const kind of ['cycle','components','timeline','water_cycle'] as const){
    const count=kind==='water_cycle'?4:3;
    const data={title:'Diagram',style:{theme:'forest' as const,brand:'Science'},scenes:[{...scene(1,4),visual:{kind,variant:1,items:Array.from({length:count},(_,i)=>`Label ${i}`),icons:Array(count).fill('water')}}]};
    assert.equal(buildTimeline(data,30).durationInFrames,135);
    assert.throws(()=>validateVideoData({...data,scenes:[{...data.scenes[0],visual:{...data.scenes[0].visual,items:['One']}}]}));
    assert.throws(()=>validateVideoData({...data,scenes:[{...data.scenes[0],visual:{...data.scenes[0].visual,variant:9}}]}));
  }
  assert.throws(()=>validateVideoData({title:'Bad style',style:{theme:'unknown',brand:'Brand'},scenes:[scene(1,4)]}));
});


test('continuity retains the previous object only for a shared label',()=>{
  const a={...scene(1,6),visual:{kind:'relationship' as const,items:['Tokens','Context'],icons:['chip','book']}};
  const b={...scene(2,6),visual:{kind:'relationship' as const,items:[' context ','Output'],icons:['idea','chart']}};
  assert.deepEqual(sharedConcept(a,b),{label:'Context',icon:'book'});
  assert.equal(sharedConcept(a,{...b,visual:{...b.visual,items:['Different','Subject']}}),undefined);
});

test('compositions validate meaning and do not change narration duration',()=>{
  const combinations=[['process','pipeline',3],['relationship','branching',3],['components','layers',4],['comparison','contrast',2],['timeline','timeline',3],['components','detail',2]] as const;
  for(const [kind,layout,n] of combinations){
    const data={title:'Stage',scenes:[{...scene(1,8),visual:{kind,layout,items:Array.from({length:n},(_,i)=>String(i))}}]};
    validateVideoData(data);assert.equal(buildTimeline(data,30).durationInFrames,255);
  }
  assert.throws(()=>validateVideoData({title:'Bad',scenes:[{...scene(1,8),visual:{kind:'chart',layout:'branching',items:['A','B'],values:[10,90]}}]}),/composition/);
});


test('bookends shift complete narration and extend the composition at any FPS',()=>{
  for(const fps of [24,30,60]){
    const data={title:'Lesson',style:{theme:'forest' as const,brand:'Learn',showIntro:true,showOutro:true},scenes:[scene(1,4),scene(2,6)]};
    const timeline=buildTimeline(data,fps);
    assert.equal(timeline.scenes[0].from,3*fps);
    assert.equal(timeline.scenes[1].from,7.5*fps);
    assert.equal(timeline.outroFrom,14*fps);
    assert.equal(timeline.durationInFrames,19*fps);
  }
});

test('statistic and code scenes reject invented numbers and empty code',()=>{
  const base={...scene(1,5),narration:'The sample contains 12.5 percent and 100 records.'};
  validateVideoData({title:'Data',scenes:[{...base,visual:{kind:'stat_card',items:['Percent','Records'],values:[12.5,100]}}]});
  assert.throws(()=>validateVideoData({title:'Data',scenes:[{...base,visual:{kind:'stat_card',items:['A','B'],values:[65,80]}}]}),/literal/);
  assert.throws(()=>validateVideoData({title:'Code',scenes:[{...base,visual:{kind:'code',items:[]}}]}),/authored/);
  validateVideoData({title:'Code',scenes:[{...base,visual:{kind:'code',items:[],codeLines:['print("Hello")']}}]});
});


test('measured word timing drives caption phrases and the spoken word',()=>{
  const text='Text becomes tokens.';
  const words=[{text:'Text',start:.2,end:.5},{text:'becomes',start:.6,end:1.1},{text:'tokens.',start:1.3,end:1.9}];
  const s={...scene(1,2),narration:text,beats:[{text,start:0,end:2,wordTiming:'model' as const,words}]};
  validateVideoData({title:'Words',scenes:[s]});
  const [phrase]=captionPhrases(s);
  assert.deepEqual([phrase.start,phrase.end],[0,2]);
  assert.equal(activeWord(phrase.words,.1),-1);
  assert.equal(activeWord(phrase.words,1.2),1);
  assert.equal(activeWord(phrase.words,1.3),2);
  for(const bad of [words.slice(1),[{...words[0],text:'Txt'},...words.slice(1)],[words[0],{...words[1],start:.1},words[2]],[words[0],words[1],{...words[2],end:2.5}]])
    assert.throws(()=>validateVideoData({title:'Words',scenes:[{...s,beats:[{...s.beats[0],words:bad}]}]}),/word timing/);
  const long=Array.from({length:20},(_,i)=>`w${i}`);
  const timed=long.map((w,i)=>({text:w,start:i*.5,end:i*.5+.4}));
  const phrases=captionPhrases({...scene(1,10),narration:long.join(' '),beats:[{text:long.join(' '),start:0,end:10,words:timed}]});
  assert.equal(phrases.length,2);
  assert.equal(phrases[1].start,timed[10].start);
  assert.equal(phrases[0].end,phrases[1].start);
});

test('visual cues may sit inside a sentence only when its words were measured',()=>{
  const text='Input becomes tokens.';
  const words=[{text:'Input',start:.1,end:.5},{text:'becomes',start:.6,end:1},{text:'tokens.',start:1.2,end:1.8}];
  const base={...scene(1,2),narration:text,visual:{kind:'relationship' as const,items:['Input','tokens'],directed:true,revealAt:[0,1.05]}};
  validateVideoData({title:'Cue',scenes:[{...base,beats:[{text,start:0,end:2,words}]}]});
  assert.throws(()=>validateVideoData({title:'Cue',scenes:[{...base,beats:[{text,start:0,end:2}]}]}),/reveal timing/);
  const choreography={layout:'sequence' as const,note:'Illustrative diagram; not measured model output',
    objects:[{label:'Input',sentence:0,at:0},{label:'tokens',sentence:0,at:1.05}],
    steps:[{sentence:0,action:'reveal' as const,targets:[0,1],start:0,end:2},{sentence:0,action:'connect' as const,targets:[0,1],start:1.05,end:2}]};
  const s={...scene(1,2),narration:text,beats:[{text,start:0,end:2,words}],choreography};
  validateVideoData({title:'Cue',scenes:[s]});
  assert.equal(objectState(choreography,1,1).visible,false);
  assert.equal(objectState(choreography,1,1.05).visible,true);
  assert.equal(objectState(choreography,0,.5).visible,true);
  assert.throws(()=>validateVideoData({title:'Cue',scenes:[{...s,beats:[{text,start:0,end:2}]}]}),/grounded|cues/);
  assert.throws(()=>validateVideoData({title:'Cue',scenes:[{...s,choreography:{...choreography,objects:[choreography.objects[0],{label:'tokens',sentence:0,at:3}]}}]}),/grounded/);
});

test('action motion waits for its spoken verb',()=>{
  const s={...scene(1,4),actions:{form:'flow' as const,beats:[{sentence:0,text:'Input becomes tokens.',verb:'transform' as const,targets:[1,0],start:0,end:4,at:1.5}]}};
  assert.equal(activeAction(s,1.4)!.started,false);
  assert.equal(activeAction(s,1.4)!.progress,0);
  assert.equal(activeAction(s,1.5)!.started,true);
  assert.ok(activeAction(s,2)!.progress>0);
});

test('scene changes exit inside the padding, then enter; shared objects carry across',()=>{
  const a={...scene(1,10)},total=sceneSeconds(a,30);
  assert.equal(exitProgress(total-EXIT_SECONDS-.01,total),0);
  assert.equal(exitProgress(total,total),1);
  assert.ok(total-EXIT_SECONDS>=a.duration,'content never leaves while narration is still speaking');
  assert.equal(enterProgress(0,.12,false),0);assert.equal(enterProgress(0,.12,true),1);
  assert.equal(enterProgress(.12+ENTER_SECONDS,.12,false),1);
  const plan=(labels:string[])=>({layout:'sequence' as const,note:'',steps:[],objects:labels.map(label=>({label,sentence:0}))});
  assert.deepEqual([...carriedLabels({...a,choreography:plan(['input text','tokens'])},{...a,choreography:plan(['Tokens','word pieces'])})],['tokens']);
  assert.equal(teaserWindow(a,undefined,30),null);
  assert.equal(teaserWindow({...a,duration:6},a,30),null);
  const w=teaserWindow(a,a,30)!;assert.ok(w.start>=a.duration*.6&&w.start<a.duration&&w.end===total);
  assert.equal(bridgedFrom(a,a,30,true),true);
  assert.equal(bridgedFrom(a,a,30,false),false,'no bridge when the topic map is off');
  assert.equal(bridgedFrom({...a,duration:6},a,30,true),false,'no bridge when the previous scene had no teaser');
  assert.ok(BRIDGE_HEADLINE_DELAY<BRIDGE_SECONDS);
});

test('named-again objects pulse on their measured words; nothing is guessed without words',()=>{
  const text='Tokens matter. Here the tokens split.';
  const s={...scene(1,6),narration:text,beats:[
    {text:'Tokens matter.',start:0,end:2,words:[{text:'Tokens',start:.1,end:.6},{text:'matter.',start:.7,end:1.5}]},
    {text:'Here the tokens split.',start:2.2,end:6,words:[{text:'Here',start:2.3,end:2.6},{text:'the',start:2.7,end:2.9},{text:'tokens',start:3,end:3.5},{text:'split.',start:3.6,end:4.2}]}]};
  const times=mentionTimes(s,'token');assert.deepEqual(times,[.1,3]);
  assert.equal(mentionPulse(times,.3,0),0,'the introduction is not a re-mention');
  assert.ok(mentionPulse(times,3.2,0)>.5);
  assert.equal(mentionPulse(times,4.5,0),0);
  assert.deepEqual(mentionTimes({...s,beats:s.beats.map(({words,...b})=>b)},'tokens'),[]);
  assert.ok(Math.abs(idleOffset(1,0,false))<=3&&Math.abs(idleOffset(1,0,true))<=5);
  assert.equal(sceneDrift(0,10),1);assert.ok(Math.abs(sceneDrift(10,10)-1.03)<1e-9);
});

test('labels fit their shapes without truncation',()=>{
  const short=fitLabel('tokens',190,24);assert.deepEqual(short,{lines:['tokens'],fontSize:24});
  const long=fitLabel('conversation history',160,24,16);
  assert.equal(long.lines.join(' '),'conversation history');
  assert.ok(long.lines.every(line=>textWidth(line,long.fontSize)<=160));
  assert.equal(fitLabel('current question',175,24,16).lines.join(' '),'current question');
  assert.ok(objectScale(2)>objectScale(3)&&objectScale(3)>objectScale(6));
  assert.throws(()=>validateVideoData({title:'T',style:{theme:'ocean' as const,brand:'B',topicMap:'yes' as unknown as boolean},scenes:[scene(1,2)]}),/bookend/);
});

test('without authored shots the camera closes in on a single focused object and widens for several',()=>{
  const plan={layout:'sequence' as const,note:'Illustrative diagram; not measured model output',
    objects:[{label:'prompt',sentence:0,at:0},{label:'history',sentence:1,at:3}],
    steps:[{sentence:0,action:'reveal' as const,targets:[0],start:0,end:3},{sentence:1,action:'reveal' as const,targets:[1],start:3,end:6},
      {sentence:2,action:'focus' as const,targets:[0],start:6,end:9},{sentence:3,action:'focus' as const,targets:[0,1],start:9,end:12}]};
  const s={...scene(1,12),choreography:plan};
  assert.equal(cameraAt(s,1).scale,1);
  assert.ok(Math.abs(cameraAt(s,7).scale-1.05)<1e-9,'single-object focus is a close-up');
  assert.ok(cameraAt(s,6.4).scale>1&&cameraAt(s,6.4).scale<1.05,'the move is eased');
  assert.equal(cameraAt(s,10).scale,1,'several objects widen again');
  assert.equal(cameraAt({...scene(1,5)},2).scale,1);
});

test('items travel the connection curve and look like what they become',()=>{
  assert.deepEqual(along([0,0],[50,-50],[100,0],0),[0,0]);
  assert.deepEqual(along([0,0],[50,-50],[100,0],1),[100,0]);
  assert.deepEqual(along([0,0],[50,-50],[100,0],.5),[50,-25]);
  assert.equal(chipKind('tokens'),'chip');assert.equal(chipKind('Token IDs'),'chip');
  assert.equal(chipKind('retrieved documents'),'page');
  assert.equal(chipKind('video ideas'),'dot','no accidental match on "id" inside words');
});

test('explainer animations validate their cues and draw recognisable shapes',()=>{
  const base={...scene(1,8),narration:'It is a next-word guesser.'};
  const next={kind:'next_token' as const,prompt:'the cat sat on the',source:'example' as const,candidates:['mat','floor','sofa'],at:{type:0,guess:1,repeat:4},end:8};
  validateVideoData({title:'E',scenes:[{...base,explainer:next}]});
  for(const bad of [{...next,candidates:['a','b','c','d']},{...next,at:{guess:9}},{...next,end:20}])
    assert.throws(()=>validateVideoData({title:'E',scenes:[{...base,explainer:bad}]}),/explainer/);
  assert.throws(()=>validateVideoData({title:'E',scenes:[{...base,explainer:{kind:'denoise',subject:'dragon',named:true,at:{},end:8}}]}),/explainer/);
  validateVideoData({title:'E',scenes:[{...base,explainer:{kind:'caveats',cards:[{key:'wrong',title:'Can be wrong'},{key:'bias',title:'Copies bias'}],at:{wrong:1,bias:3},end:8}}]});
  assert.ok(inside('heart',0,0)&&!inside('heart',.95,.95));
  assert.ok(inside('star',0,0)&&!inside('star',.9,.9));
  assert.equal(noise(3,4,7),noise(3,4,7),'noise is deterministic per frame');
  assert.notEqual(noise(3,4,7),noise(3,4,8),'and churns between frames');
  assert.equal(after(1,undefined),0);assert.equal(after(2,1,.5),1);
});

test('mostly light videos keep their title and takeaway cards light',()=>{
  const plain=(kind:string)=>({...scene(1,4),visual:{kind:kind as 'title',items:[]}});
  const board={...scene(2,4),explainer:{kind:'caveats' as const,cards:[{key:'wrong' as const,title:'Can be wrong'},{key:'bias' as const,title:'Copies bias'}],at:{},end:4}};
  assert.equal(lightVideo([plain('title'),board,board,plain('takeaway')]),true);
  assert.equal(lightCard(plain('title'),true),true);
  assert.equal(lightCard(plain('explanation'),true),false,'only title and takeaway cards switch');
  assert.equal(lightVideo([plain('title'),plain('explanation'),plain('process'),board]),false);
});

test('pack two explainers accept only faithful data',()=>{
  const base={...scene(1,8),narration:'Text is broken into tokens.'};
  const tokens={kind:'tokens' as const,text:'Embeddings work',pieces:['Emb','eddings',' work'],ids:[1,2,3],model:'Qwen3',at:{split:1,ids:3},end:8};
  validateVideoData({title:'E',scenes:[{...base,explainer:tokens}]});
  for(const bad of [{...tokens,pieces:['Emb','edding',' work']},{...tokens,ids:[1,2]},{...tokens,ids:[1,-2,3]}])
    assert.throws(()=>validateVideoData({title:'E',scenes:[{...base,explainer:bad}]}),/explainer/);
  const map={kind:'embedding_map' as const,points:[{label:'Cat',group:0},{label:'Dog',group:0},{label:'King',group:1},{label:'Banana',group:2}],at:{},end:8};
  validateVideoData({title:'E',scenes:[{...base,explainer:map}]});
  assert.throws(()=>validateVideoData({title:'E',scenes:[{...base,explainer:{...map,points:map.points.slice(0,3)}}]}),/explainer/);
  validateVideoData({title:'E',scenes:[{...base,explainer:{kind:'retrieval',stages:[{key:'question',title:'Question'},{key:'embedding',title:'Embedding'},{key:'chunks',title:'Closest chunks'},{key:'answer',title:'Answer'}],at:{},end:8}}]});
  const placed=mapLayout([0,0,1,2]);
  const d=(a:number[],b:number[])=>Math.hypot(a[0]-b[0],a[1]-b[1]);
  assert.ok(d(placed[0],placed[1])<d(placed[0],placed[2]),'grouped points sit closer than other groups');
  assert.equal(chipRows([500,500,500],1200)[2].y>0,true,'chips wrap to a new row');
});

test('measured maps keep real positions and links between real points',()=>{
  const base={...scene(1,8),narration:'Cat and Dog are close.'};
  const xy:[number,number][]=[[-.5,-.1],[-.4,-.05],[.5,.1],[.3,.2]];
  const map={kind:'embedding_map' as const,points:['Cat','Dog','King','Banana'].map((label,i)=>({label,group:i>1?i-1:0,xy:xy[i]})),
    links:[{a:0,b:1,sim:.73},{a:2,b:3,sim:.61}],measured:true,model:'bge-small-en-v1.5',at:{},end:8};
  validateVideoData({title:'E',scenes:[{...base,explainer:map}]});
  for(const bad of [{...map,links:[{a:0,b:9,sim:.5}]},{...map,links:undefined},{...map,points:map.points.map(({xy:_,...p})=>p)},{...map,model:''}])
    assert.throws(()=>validateVideoData({title:'E',scenes:[{...base,explainer:bad}]}),/explainer/);
  const {places,sides}=measuredLayout(xy,{x:0,y:0,w:900,h:300});
  assert.deepEqual([Math.min(...places.map(p=>p[0])),Math.max(...places.map(p=>p[0]))],[0,900],'x fills the plot');
  assert.deepEqual([Math.min(...places.map(p=>p[1])),Math.max(...places.map(p=>p[1]))],[0,300],'y fills the plot');
  assert.equal(sides[0],'left','a label with a close neighbour on its right sits on the left');
  assert.equal(sides[1],'right');
  assert.equal(sides[2],'right','points without a close neighbour keep their label on the right');
});

test('caption phrases preserve every word within measured sentence boundaries',()=>{
  const text=Array.from({length:35},(_,i)=>`word${i}`).join(' ');
  const phrases=captionPhrases({...scene(1,12),narration:text,beats:[{text,start:0,end:12}]});
  assert.equal(phrases.map(p=>p.text).join(' '),text);
  assert.ok(phrases.every(p=>p.text.split(' ').length<=12&&p.end>p.start));
  assert.equal(phrases[0].start,0);assert.equal(phrases.at(-1)!.end,12);
  assert.equal(sceneTransition('fade',.5).opacity,.5);
  assert.equal(sceneTransition('zoom',1).transform,'scale(1)');
  assert.notEqual(palette('forest').accent,palette('sunset').accent);
});


test('worked examples require measured output and ordered narration cues',async()=>{
  const {validateWorkedScene,exampleStage}=await import('../src/worked-example.ts');
  const scene={id:1,headline:'Tokens',body:'Example',narration:'Split text. Generate output.',audio:'audio/scene-1.wav',duration:4,
    beats:[{text:'Split text.',start:0,end:2},{text:'Generate output.',start:2,end:4}],
    visual:{kind:'explanation' as const,items:[],worked:{input:'Hi',label:'Example',steps:[{action:'tokens' as const,sentence:0},{action:'generate' as const,sentence:1}]},
      workedData:{input:'Hi',tokens:[{id:42,piece:[72,105]}],generated_ids:[7],prefixes:[' there'],continuation:' there',model:{model:'fixture'},mode:'raw_completion' as const}}};
  validateWorkedScene(scene);
  assert.equal(exampleStage(scene,1).action,'tokens');assert.equal(exampleStage(scene,2).action,'generate');
  assert.equal(exampleStage(scene,4).progress,1);
  const bad=structuredClone(scene);bad.visual.workedData.tokens[0].piece=[72];assert.throws(()=>validateWorkedScene(bad));
  const duplicate=structuredClone(scene);duplicate.visual.worked.steps[1].sentence=0;assert.throws(()=>validateWorkedScene(duplicate));
  const missing=structuredClone(scene);delete (missing.visual as Partial<typeof scene.visual>).workedData;assert.throws(()=>validateWorkedScene(missing));
});
import {objectState,validateChoreography} from '../src/choreography.ts';
import {cameraAt,shotPosition,validateShots} from '../src/shot-direction.ts';
import {activeAction,validateVisualActions,actionPosition} from '../src/visual-actions.ts';
test('directed visuals reveal and remove only at measured narration cues',()=>{
  const s={...scene(1,8),narration:'Instructions enter. Older messages leave.',beats:[{text:'Instructions enter.',start:0,end:3},{text:'Older messages leave.',start:3.2,end:8}],
    choreography:{layout:'workspace' as const,note:'Illustrative diagram; not measured model output',objects:[{label:'Instructions',sentence:0},{label:'Older messages',sentence:1}],steps:[{sentence:0,action:'reveal' as const,targets:[0],start:0,end:3},{sentence:1,action:'reveal' as const,targets:[1],start:3.2,end:8}]}};
  validateChoreography(s);
  assert.equal(objectState(s.choreography,1,3).visible,false);
  assert.equal(objectState(s.choreography,1,3.3).visible,true);
  const bad=structuredClone(s);bad.choreography.steps[1].start=0;assert.throws(()=>validateChoreography(bad),/measured/);
  const falseLabel=structuredClone(s);falseLabel.choreography.objects[0].label='Training data';assert.throws(()=>validateChoreography(falseLabel),/grounded/);
});

test('shot camera changes at measured sentence cues and rejects invented focus',()=>{
  const s={...scene(1,8),narration:'Input text appears. The tokenizer converts input text.',beats:[{text:'Input text appears.',start:0,end:3},{text:'The tokenizer converts input text.',start:3,end:8}],
    choreography:{layout:'sequence' as const,note:'Illustrative diagram; not measured model output',objects:[{label:'Input text',sentence:0},{label:'tokenizer',sentence:1}],steps:[{sentence:0,action:'reveal' as const,targets:[0],start:0,end:3},{sentence:1,action:'reveal' as const,targets:[1],start:3,end:8}]},
    shots:[{sentence:0,text:'Input text appears.',mode:'wide' as const,focus:0,label:'Input text',start:0,end:3},{sentence:1,text:'The tokenizer converts input text.',mode:'detail' as const,focus:1,label:'tokenizer',start:3,end:8}]};
  validateShots(s);
  assert.equal(cameraAt(s,2.9).scale,1);
  assert.equal(cameraAt(s,3).scale,1);
  assert.ok(cameraAt(s,3.5).scale>1);
  const bad=structuredClone(s);bad.shots[1].focus=0;assert.throws(()=>validateShots(bad),/Shot must match/);
});

test('follow and detail views keep edge illustrations inside the stage',()=>{
  const base={...scene(1,8),narration:'First appears. Last appears.',beats:[{text:'First appears.',start:0,end:3},{text:'Last appears.',start:3,end:8}],
    choreography:{layout:'sequence' as const,note:'Illustrative diagram',objects:[
      {label:'First',sentence:0},{label:'Middle',sentence:0},{label:'Another',sentence:0},{label:'Last',sentence:1}],steps:[]},
    shots:[{sentence:0,text:'First appears.',mode:'detail' as const,focus:0,label:'First',start:0,end:3},
      {sentence:1,text:'Last appears.',mode:'follow' as const,focus:3,label:'Last',start:3,end:8}]};
  for(const t of [1,4]){
    const camera=cameraAt(base,t);
    for(let i=0;i<4;i++){
      const [x]=shotPosition('sequence',i,4);
      const center=camera.x+x*camera.scale;
      assert.ok(center-92>6&&center+92<1594,`object ${i} cropped at ${t}s`);
    }
  }
});

test('topic visual actions retain sentence timing and reject unsupported changes',()=>{
  const s={...scene(1,7),narration:'Input text appears. Tokens split from text.',
    beats:[{text:'Input text appears.',start:0,end:3},{text:'Tokens split from text.',start:3,end:7}],
    choreography:{layout:'sequence' as const,note:'Illustrative diagram; not measured model output',objects:[{label:'Input text',sentence:0},{label:'Tokens',sentence:1}],steps:[
      {sentence:0,action:'reveal' as const,targets:[0],start:0,end:3},{sentence:1,action:'reveal' as const,targets:[1],start:3,end:7}]},
    actions:{form:'split' as const,beats:[{sentence:0,text:'Input text appears.',verb:'reveal' as const,targets:[0],start:0,end:3},
      {sentence:1,text:'Tokens split from text.',verb:'split' as const,targets:[0,1],start:3,end:7}]}};
  validateVisualActions(s);
  assert.equal(activeAction(s,2)?.verb,'reveal');
  assert.equal(activeAction(s,4)?.verb,'split');
  assert.notDeepEqual(actionPosition('split',0,2),actionPosition('split',1,2));
  const altered=structuredClone(s);altered.actions.beats[1].start=2;assert.throws(()=>validateVisualActions(altered),/spoken sentence/);
});

test('concept icons: specific concepts get a fitting icon, vague or unknown words get none',()=>{
  const nodes=JSON.parse(readFileSync(new URL('../node_modules/lucide-static/icon-nodes.json',import.meta.url),'utf-8'));
  const expected:Record<string,string|null>={
    'vector database':'database','ten million documents':'files','similarity search':'search','language model':'brain-circuit',
    'question':'message-circle-question-mark','LLM answer':'message-square-text','cluster centers':'boxes','Metadata':'tags',
    'build an index':'list-tree','library':'library','cat':'cat','King':'crown',
    // Vague, verb-like or unknown labels keep the neutral glyph rather than a misleading icon.
    'smarter trick':null,'tiny bit':null,'built':null,'brute force':null,'single':null,'meaning lines':null,'HNSW':null,'Chroma':null};
  for(const [label,icon] of Object.entries(expected))assert.equal(iconFor(label,nodes),icon,label);
  for(const icon of Object.values(expected))if(icon)assert.ok(nodes[icon],`${icon} exists in this Lucide version`);
});
