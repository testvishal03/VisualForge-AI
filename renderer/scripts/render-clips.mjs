// Render many scene clips with one browser: node render-clips.mjs <jobs.json>
// jobs.json: {"bundle", "props", "scale", "concurrency", "clips": [{"from", "to", "out"}]}
// Starting Node and Chrome once instead of once per clip saves about 5 s per clip. A clip whose
// output already exists (from an earlier, interrupted batch) is skipped. Progress is printed as
// "Rendered done/total" over all frames, which the studio's progress bar and stall check read.
import {existsSync, readFileSync, renameSync, statSync} from 'node:fs';
import {openBrowser, selectComposition, renderMedia} from '@remotion/renderer';

const job = JSON.parse(readFileSync(process.argv[2], 'utf-8'));
const inputProps = JSON.parse(readFileSync(job.props, 'utf-8'));
const pending = job.clips.filter(c => !(existsSync(c.out) && statSync(c.out).size > 0));
const total = pending.reduce((sum, c) => sum + c.to - c.from + 1, 0);
let finished = 0, lastPrinted = -1;
const browser = await openBrowser('chrome');
try {
  const composition = await selectComposition({serveUrl: job.bundle, id: 'VisualForgeVideo', inputProps, puppeteerInstance: browser});
  for (const [i, clip] of pending.entries()) {
    const temporary = clip.out.replace(/\.mp4$/, '.part.mp4');
    await renderMedia({
      serveUrl: job.bundle, composition, inputProps, codec: 'h264', outputLocation: temporary, frameRange: [clip.from, clip.to],
      muted: true, concurrency: job.concurrency, scale: job.scale, puppeteerInstance: browser, overwrite: true,
      onProgress: ({renderedFrames}) => {
        const done = finished + renderedFrames;
        if (done - lastPrinted >= 30 || done === total) {console.log(`Rendered ${done}/${total}`); lastPrinted = done;}
      },
    });
    renameSync(temporary, clip.out);
    finished += clip.to - clip.from + 1;
    console.log(`Clip ${i + 1}/${pending.length} done`);
  }
} finally {
  await browser.close({silent: true});
}
