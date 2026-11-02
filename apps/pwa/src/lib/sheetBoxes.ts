// Put boxes on a kept answer-sheet photo: one around the question and one around the answer that showed the
// mistake. The printed paper has a black square mark in each corner (services/papers/render.py) and its layout
// map gives every box in millimetres, so: find the four marks in the photo, work out how the page was
// tilted (a homography), and draw each box where the map says it is. All of it runs on this phone, on the
// picture that is already there; nothing is sent anywhere.
//
// Best effort. If the four marks are not found, or the paper has more than one page, no boxes are drawn and
// the caller says so: the photo is still shown, and the question and the answer are written beside it.

export interface LayoutBox {
  id: string;
  kind: string;
  page: number;
  x: number;
  y: number;
  w: number;
  h: number;
}
export interface LayoutMap {
  pages: number;
  page: { w: number; h: number };
  boxes: LayoutBox[];
  marks: LayoutBox[];
}
export interface Pt {
  x: number;
  y: number;
}

/** Solve the 3x3 projective map from four points to four points (the eight unknowns by Gauss-Jordan). */
export function homography(from: Pt[], to: Pt[]): number[] | null {
  if (from.length !== 4 || to.length !== 4) return null;
  const a: number[][] = [];
  for (let i = 0; i < 4; i++) {
    const f = from[i] as Pt;
    const t = to[i] as Pt;
    a.push([f.x, f.y, 1, 0, 0, 0, -t.x * f.x, -t.x * f.y, t.x]);
    a.push([0, 0, 0, f.x, f.y, 1, -t.y * f.x, -t.y * f.y, t.y]);
  }
  for (let c = 0; c < 8; c++) {
    let best = c;
    for (let r = c + 1; r < 8; r++) if (Math.abs((a[r] as number[])[c] as number) > Math.abs((a[best] as number[])[c] as number)) best = r;
    const pivot = (a[best] as number[])[c] as number;
    if (Math.abs(pivot) < 1e-9) return null;
    [a[c], a[best]] = [a[best] as number[], a[c] as number[]];
    const row = a[c] as number[];
    for (let k = c; k < 9; k++) row[k] = (row[k] as number) / pivot;
    for (let r = 0; r < 8; r++) {
      if (r === c) continue;
      const other = a[r] as number[];
      const f = other[c] as number;
      if (f !== 0) for (let k = c; k < 9; k++) other[k] = (other[k] as number) - f * (row[k] as number);
    }
  }
  return [...a.map((r) => r[8] as number), 1];
}

export function apply(h: number[], p: Pt): Pt {
  const [a, b, c, d, e, f, g, hh] = h as [number, number, number, number, number, number, number, number, number];
  const w = g * p.x + hh * p.y + 1;
  return { x: (a * p.x + b * p.y + c) / w, y: (d * p.x + e * p.y + f) / w };
}

interface Blob2 {
  cx: number;
  cy: number;
  w: number;
  h: number;
  area: number;
}

/** Dark, square, filled blobs of the size a corner mark has: the candidates for the four marks. */
export function darkSquares(gray: Uint8ClampedArray, width: number, height: number): Blob2[] {
  // a pixel is dark when it is clearly under the average of its neighbourhood (an integral image)
  const stride = width + 1;
  const sum = new Float64Array(stride * (height + 1));
  for (let y = 0; y < height; y++) {
    let row = 0;
    for (let x = 0; x < width; x++) {
      row += gray[y * width + x] as number;
      sum[(y + 1) * stride + x + 1] = (sum[y * stride + x + 1] as number) + row;
    }
  }
  const r = Math.max(8, Math.round(Math.min(width, height) / 25));
  const dark = new Uint8Array(width * height);
  for (let y = 0; y < height; y++) {
    const y0 = Math.max(0, y - r);
    const y1 = Math.min(height, y + r + 1);
    for (let x = 0; x < width; x++) {
      const x0 = Math.max(0, x - r);
      const x1 = Math.min(width, x + r + 1);
      const total = (sum[y1 * stride + x1] as number) - (sum[y0 * stride + x1] as number) - (sum[y1 * stride + x0] as number) + (sum[y0 * stride + x0] as number);
      const mean = total / ((x1 - x0) * (y1 - y0));
      const v = gray[y * width + x] as number;
      if (v < mean * 0.7 && v < 110) dark[y * width + x] = 1;
    }
  }
  const seen = new Uint8Array(width * height);
  const out: Blob2[] = [];
  const stack: number[] = [];
  const side = Math.min(width, height);
  for (let start = 0; start < dark.length; start++) {
    if (!dark[start] || seen[start]) continue;
    let minX = width, maxX = 0, minY = height, maxY = 0, area = 0, sx = 0, sy = 0;
    stack.push(start);
    seen[start] = 1;
    while (stack.length) {
      const p = stack.pop() as number;
      const x = p % width;
      const y = (p - x) / width;
      area++;
      sx += x;
      sy += y;
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
      if (x > 0 && dark[p - 1] && !seen[p - 1]) {
        seen[p - 1] = 1;
        stack.push(p - 1);
      }
      if (x < width - 1 && dark[p + 1] && !seen[p + 1]) {
        seen[p + 1] = 1;
        stack.push(p + 1);
      }
      if (y > 0 && dark[p - width] && !seen[p - width]) {
        seen[p - width] = 1;
        stack.push(p - width);
      }
      if (y < height - 1 && dark[p + width] && !seen[p + width]) {
        seen[p + width] = 1;
        stack.push(p + width);
      }
    }
    const w = maxX - minX + 1;
    const h = maxY - minY + 1;
    const fill = area / (w * h);
    const aspect = w / h;
    // a 5 mm mark on A4 is about 2.4% of the page width: allow 0.8% to 7% of the photo's short side
    if (w >= side * 0.008 && w <= side * 0.07 && aspect > 0.55 && aspect < 1.8 && fill > 0.7) out.push({ cx: sx / area, cy: sy / area, w, h, area });
  }
  return out;
}

/** The four marks as top-left, top-right, bottom-left, bottom-right, or null when they are not all there. */
export function pickCorners(blobs: Blob2[], width: number, height: number): Pt[] | null {
  const corners: Pt[] = [
    { x: 0, y: 0 },
    { x: width, y: 0 },
    { x: 0, y: height },
    { x: width, y: height },
  ];
  const chosen: Pt[] = [];
  for (const c of corners) {
    let best: Blob2 | null = null;
    let bestD = Infinity;
    for (const b of blobs) {
      // inside this corner's quarter of the photo, and the closest to the corner
      if ((c.x === 0 ? b.cx > width / 2 : b.cx < width / 2) || (c.y === 0 ? b.cy > height / 2 : b.cy < height / 2)) continue;
      const d = Math.hypot(b.cx - c.x, b.cy - c.y);
      if (d < bestD) {
        best = b;
        bestD = d;
      }
    }
    if (!best) return null;
    chosen.push({ x: best.cx, y: best.cy });
  }
  // the four must make a sensible page: a convex four-sided shape with a good share of the photo
  const [tl, tr, bl, br] = chosen as [Pt, Pt, Pt, Pt];
  const area = Math.abs((tr.x - tl.x) * (bl.y - tl.y) - (bl.x - tl.x) * (tr.y - tl.y)) / 2 + Math.abs((tr.x - br.x) * (bl.y - br.y) - (bl.x - br.x) * (tr.y - br.y)) / 2;
  if (area < width * height * 0.2) return null;
  if (!(tl.x < tr.x && bl.x < br.x && tl.y < bl.y && tr.y < br.y)) return null;
  return chosen;
}

/** The box round a question (its number and its numbers) and the one round its answer, in page mm. */
export function boxesFor(layout: LayoutMap, n: number): { question: LayoutBox | null; answer: LayoutBox | null } {
  const pick = (id: string) => layout.boxes.find((b) => b.id === id) ?? null;
  const parts = [pick(`label-${n}`), pick(`top-${n}`), pick(`bottom-${n}`)].filter((b): b is LayoutBox => b !== null);
  const question =
    parts.length === 0
      ? null
      : {
          id: `question-${n}`,
          kind: "question",
          page: (parts[0] as LayoutBox).page,
          x: Math.min(...parts.map((b) => b.x)) - 1,
          y: Math.min(...parts.map((b) => b.y)) - 1,
          w: Math.max(...parts.map((b) => b.x + b.w)) - Math.min(...parts.map((b) => b.x)) + 2,
          h: Math.max(...parts.map((b) => b.y + b.h)) - Math.min(...parts.map((b) => b.y)) + 2,
        };
  return { question, answer: pick(`answer-${n}`) };
}

export interface Annotated {
  url: string; // a data URL of the photo (with the boxes when they could be placed)
  placed: boolean;
}

function loadImage(blob: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("image"));
    };
    img.src = url;
  });
}

const DARK = "#7a1a14"; // a dark red: it shows on a colour print and still reads on a black-and-white one

/** The photo with a box round the question and the answer of each listed question. When the page cannot be
 *  found in the photo the picture comes back as it is, `placed` false. */
export async function annotate(photo: Blob, layout: LayoutMap | null, questions: number[]): Promise<Annotated> {
  const img = await loadImage(photo);
  const scale = Math.min(1, 1600 / Math.max(img.naturalWidth, img.naturalHeight));
  const W = Math.round(img.naturalWidth * scale);
  const H = Math.round(img.naturalHeight * scale);
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  if (!ctx) return { url: URL.createObjectURL(photo), placed: false };
  ctx.drawImage(img, 0, 0, W, H);
  const done = (placed: boolean): Annotated => ({ url: canvas.toDataURL("image/jpeg", 0.85), placed });
  if (!layout || layout.pages !== 1 || layout.marks.length < 4) return done(false);

  // find the marks on a smaller copy, then scale the points back up
  const f = Math.min(1, 700 / Math.max(W, H));
  const sw = Math.round(W * f);
  const sh = Math.round(H * f);
  const small = document.createElement("canvas");
  small.width = sw;
  small.height = sh;
  const sctx = small.getContext("2d");
  if (!sctx) return done(false);
  sctx.drawImage(img, 0, 0, sw, sh);
  const rgba = sctx.getImageData(0, 0, sw, sh).data;
  const gray = new Uint8ClampedArray(sw * sh);
  for (let i = 0; i < gray.length; i++) gray[i] = 0.299 * (rgba[i * 4] as number) + 0.587 * (rgba[i * 4 + 1] as number) + 0.114 * (rgba[i * 4 + 2] as number);
  const found = pickCorners(darkSquares(gray, sw, sh), sw, sh);
  if (!found) return done(false);

  const mm = (k: string): Pt => {
    const m = layout.marks.find((b) => b.id.startsWith(`mark-${k}-`)) as LayoutBox;
    return { x: m.x + m.w / 2, y: m.y + m.h / 2 };
  };
  const h = homography([mm("tl"), mm("tr"), mm("bl"), mm("br")], found.map((p) => ({ x: p.x / f, y: p.y / f })));
  if (!h) return done(false);

  const draw = (b: LayoutBox, label: string, dashed: boolean) => {
    const poly = [
      { x: b.x, y: b.y },
      { x: b.x + b.w, y: b.y },
      { x: b.x + b.w, y: b.y + b.h },
      { x: b.x, y: b.y + b.h },
    ].map((p) => apply(h, p));
    ctx.beginPath();
    poly.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
    ctx.closePath();
    ctx.setLineDash(dashed ? [14, 8] : []);
    ctx.lineWidth = Math.max(4, W / 220);
    ctx.strokeStyle = DARK;
    ctx.stroke();
    ctx.setLineDash([]);
    const first = poly[0] as Pt;
    ctx.font = `bold ${Math.max(18, Math.round(W / 45))}px sans-serif`;
    ctx.lineWidth = 5;
    ctx.strokeStyle = "#ffffff";
    ctx.strokeText(label, first.x + 4, first.y - 6);
    ctx.fillStyle = DARK;
    ctx.fillText(label, first.x + 4, first.y - 6);
  };
  let drawn = 0;
  for (const n of questions) {
    const { question, answer } = boxesFor(layout, n);
    if (question) {
      draw(question, `Q${n}`, true);
      drawn++;
    }
    if (answer) {
      draw(answer, `A${n}`, false);
      drawn++;
    }
  }
  return done(drawn > 0);
}
