const {test}=require('node:test');
const assert=require('node:assert/strict');
const {applyFixes}=require('./script-fixes.js');

// Fixes exactly as the script checker returned them for this text.
const TEXT=`Narrator: Pick a store for your vectors. [pause] Chroma vs. Pinecone, e.g. for 10M
vectors, is the #1 question. Hosting costs $5 a month, i.e. very little.

So vector databases use a smarter trick called Approximate Nearest Neighbor search, or ANN.`;
const FIXES=[{"find": "e.g.", "replace": "for example", "sentence": "Pinecone, e.g. for 10M vectors, is the #1 question."}, {"find": "i.e.", "replace": "that is", "sentence": "Hosting costs $5 a month, i.e. very little."}, {"find": "vs.", "replace": "versus", "sentence": "Narrator: Pick a store for your vectors. [pause] Chroma vs."}, {"find": "#1", "replace": "number 1", "sentence": "Pinecone, e.g. for 10M vectors, is the #1 question."}, {"find": "$5", "replace": "5 dollars", "sentence": "Hosting costs $5 a month, i.e. very little."}, {"find": "10M", "replace": "10 million", "sentence": "Pinecone, e.g. for 10M vectors, is the #1 question."}, {"find": "[pause]", "replace": "", "sentence": "Narrator: Pick a store for your vectors. [pause] Chroma vs."}, {"find": "Narrator:", "replace": "", "sentence": "Narrator: Pick a store for your vectors. [pause] Chroma vs."}, {"find": "ANN", "replace": "A-N-N", "sentence": "So vector databases use a smarter trick called Approximate Nearest Neighbor search, or ANN."}].filter(f=>TEXT.replace(/\s+/g,' ').includes(f.sentence));

test('every fix applies, including several in one sentence across a wrapped line',()=>{
  const {text,applied}=applyFixes(TEXT,FIXES);
  assert.equal(applied,FIXES.length);
  assert.equal(text,`Pick a store for your vectors. Chroma versus Pinecone, for example for 10 million
vectors, is the number 1 question. Hosting costs 5 dollars a month, that is very little.

So vector databases use a smarter trick called Approximate Nearest Neighbor search, or A-N-N.`);
});
test('a fix only changes whole words in its own sentence',()=>{
  const text='ANNA met ANN. Later, the search used ANN.';
  const fix={find:'ANN',replace:'A-N-N',sentence:'Later, the search used ANN.'};
  assert.equal(applyFixes(text,[fix]).text,'ANNA met ANN. Later, the search used A-N-N.');
});
test('fixes for text that has since changed are skipped',()=>{
  const fix={find:'e.g.',replace:'for example',sentence:'Tools, e.g. Chroma, work.'};
  assert.deepEqual(applyFixes('Tools such as Chroma work.',[fix]),{text:'Tools such as Chroma work.',applied:0});
});
