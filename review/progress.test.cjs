const {test}=require('node:test');
const assert=require('node:assert/strict');
const {generationProgress}=require('./progress.js');
test('render counters determine progress, validation cannot reach 100',()=>{
  const p=generationProgress({status:'running',phase:'render',progress:['Rendered 50/100']});
  assert.equal(p.pct,80);
  assert.equal(generationProgress({status:'running',phase:'validate'}).pct,97);
  assert.equal(generationProgress({status:'complete'}).pct,100);
});
test('publishing extras come after the checked video and never reach 100',()=>{
  const p=generationProgress({status:'running',phase:'thumbnail'},97);
  assert.equal(p.pct,98);assert.match(p.label,/thumbnail/i);
});
test('progress stays monotonic and is not based on elapsed time',()=>{
  assert.equal(generationProgress({status:'running',phase:'audio',elapsed_seconds:50000},70).pct,70);
  assert.equal(generationProgress({status:'failed',phase:'render'},80).pct,80);
});
test('chapter render progress leaves room for remaining chapters',()=>{
  const p=generationProgress({status:'running',phase:'render',chapter_index:0,chapter_total:4,progress:['Rendered 100/100']});
  assert.ok(p.pct<60);assert.match(p.label,/Chapter 1 of 4/);
});
