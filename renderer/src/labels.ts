/** Approximate width of bold Segoe UI text; conservative so labels stay inside their shapes. */
export const textWidth = (text:string, fontSize:number) => text.length*fontSize*.58;

function balancedLines(label:string) {
  const words = label.split(/\s+/);
  let best = [label], widest = Infinity;
  for (let i = 1; i < words.length; i++) {
    const lines = [words.slice(0, i).join(' '), words.slice(i).join(' ')];
    const size = Math.max(...lines.map(l => l.length));
    if (size < widest) { widest = size; best = lines; }
  }
  return best;
}

/**
 * Fit a label inside `maxWidth`: one line if it stays readable, else two balanced
 * lines, shrinking the font down to `minFont`. Never truncates the label.
 */
export function fitLabel(label:string, maxWidth:number, maxFont:number, minFont = 16) {
  const oneLineFloor = Math.max(minFont, Math.round(maxFont*.82));
  for (let size = maxFont; size >= oneLineFloor; size--)
    if (textWidth(label, size) <= maxWidth) return {lines:[label], fontSize:size};
  const lines = balancedLines(label);
  for (let size = maxFont; size >= minFont; size--)
    if (lines.every(line => textWidth(line, size) <= maxWidth)) return {lines, fontSize:size};
  return {lines, fontSize:minFont};
}

/** Few objects get larger shapes so a sparse stage is not mostly empty space. */
export const objectScale = (count:number) => count <= 2 ? 1.25 : count === 3 ? 1.12 : 1;

/** Font size that keeps a scene headline on one line across `width`, down to `minFont`. */
export const headlineFont = (text:string, width = 1730, maxFont = 65, minFont = 44) => {
  for (let size = maxFont; size > minFont; size--) if (textWidth(text, size)*.92 <= width) return size;
  return minFont;
};
