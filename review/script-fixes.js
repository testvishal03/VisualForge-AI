"use strict";
/**
 * Apply script-checker fixes to the pasted text. Each fix names its sentence, found whitespace-
 * tolerantly (the box may wrap lines mid-sentence); a sentence changed by an earlier fix is
 * tracked so a second fix in the same sentence still applies. Returns the new text and how many
 * fixes applied; fixes whose sentence or text has since changed are skipped.
 */
function applyFixes(text, fixes){
  const escape=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const pending=fixes.map(f=>({...f}));
  let applied=0;
  for(const fix of pending){
    const found=new RegExp(fix.sentence.trim().split(/\s+/).map(escape).join('\\s+')).exec(text);
    if(!found)continue;
    const edge=/^\w/.test(fix.find)?'(?<![\\w-])':'',tail=/\w$/.test(fix.find)?'(?![\\w-])':'';
    const target=new RegExp(edge+escape(fix.find)+tail).exec(found[0]);
    if(!target)continue;
    let before=found[0].slice(0,target.index),after=found[0].slice(target.index+fix.find.length);
    // A removed direction or label takes one neighbouring space with it.
    if(!fix.replace&&(!before||/\s$/.test(before)))after=after.replace(/^\s+/,'');
    const updated=before+fix.replace+after;
    text=text.slice(0,found.index)+updated+text.slice(found.index+found[0].length);
    applied++;
    const normalized=updated.replace(/\s+/g,' ').trim();
    for(const later of pending)if(later!==fix&&later.sentence===fix.sentence)later.sentence=normalized;
  }
  return {text,applied};
}
if(typeof module!=='undefined')module.exports={applyFixes};
