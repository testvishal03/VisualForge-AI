import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {test} from 'node:test';
import {buildTimeline, FPS, SCENE_END_PADDING_SECONDS, validateVideoData} from '../src/timeline.ts';
import {environmentFor} from '../src/motion.ts';
import {captionPhrases,sceneTransition,palette} from '../src/presentation.ts';
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
