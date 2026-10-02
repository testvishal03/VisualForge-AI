import {continueRender, delayRender} from 'remotion';
import regular from './fonts/selawk.woff2';
import semibold from './fonts/selawksb.woff2';
import bold from './fonts/selawkb.woff2';

/**
 * Selawik is Microsoft's open-source (SIL OFL 1.1) fallback for Segoe UI with matching widths.
 * Windows renders with Segoe UI as before; Linux servers have no Segoe UI, so the font stacks
 * name Selawik next ("'Segoe UI', Selawik, ..."), keeping label widths and line breaks the same.
 */

const faces = [[regular, '400'], [semibold, '600'], [bold, '700']] as const;
if (typeof document !== 'undefined' && typeof FontFace !== 'undefined') {
  const handle = delayRender('Loading Selawik');
  Promise.all(faces.map(([url, weight]) => new FontFace('Selawik', `url(${url}) format('woff2')`, {weight}).load()))
    .then(loaded => {loaded.forEach(face => (document.fonts as unknown as {add(f: FontFace): void}).add(face)); continueRender(handle);})
    .catch(() => continueRender(handle));
}
