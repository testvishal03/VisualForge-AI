/* Estimated stage progress. Only a completed backend job reaches 100%. */
function generationProgress(job,previous=0) {
  const phase=job.phase||'',logs=(job.progress||[]).join('\n');
  let stage=0,pct=2,label='Planning your video';
  const frames=[...logs.matchAll(/Rendered\s+(\d+)\s*\/\s*(\d+)/gi)].at(-1);
  if(/draft|script/.test(phase)){stage=1;pct=12;label='Writing the explanation';}
  if(/visual|worked/.test(phase)){stage=2;pct=37;label='Building the visuals';}
  if(phase==='audio'){stage=3;pct=50;label='Recording the narration';}
  if(phase==='render'||phase==='preview'){stage=4;pct=67;label='Rendering your video';if(frames&&Number(frames[2])>0)pct=67+27*Math.min(1,Number(frames[1])/Number(frames[2]));}
  if(/validate/.test(phase)){stage=5;pct=97;label='Checking video and audio';}
  if(job.chapter_total&&Number.isInteger(job.chapter_index)&&['audio','render','validate'].includes(phase)){
    const local=phase==='audio'?0.1:phase==='validate'?.98:frames?0.2+.75*Number(frames[1])/Number(frames[2]):.2;
    pct=45+50*(job.chapter_index+Math.min(1,local))/job.chapter_total;
    label+=` · Chapter ${job.chapter_index+1} of ${job.chapter_total}`;
  }
  pct=Math.min(99,Math.max(previous,Math.floor(pct)));
  if(job.status==='complete'){pct=100;label='Generation complete';stage=6;}
  if(job.status==='failed')label='Generation needs attention';
  if(job.status==='cancelled')label='Generation cancelled';
  return {pct,stage,label};
}
if(typeof module!=='undefined')module.exports={generationProgress};
