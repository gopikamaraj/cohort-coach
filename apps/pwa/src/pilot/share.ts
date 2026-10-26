// Sharing the audio on WhatsApp from the coordinator's own phone. The WhatsApp Business API is not
// set up, so this is manual: the browser's share sheet with the file attached where the phone
// allows it (navigator.share with files), and Download, Copy link and Open WhatsApp where it does not.
import { getAudioBlob, type AudioDeps } from "./audioCache";
import type { Card, Session } from "./api";

export type ShareOutcome = "shared" | "cancelled" | "unsupported" | "failed";

interface ShareNav {
  canShare?: (data: ShareData) => boolean;
  share?: (data: ShareData) => Promise<void>;
}

/** Browsers differ on the audio type they allow in a share; try the likely ones. */
export function candidateTypes(mime: string): string[] {
  return mime === "audio/mpeg" ? ["audio/mpeg", "audio/mp3"] : ["audio/mp4", "audio/x-m4a", "audio/m4a"];
}

/** A File for the share sheet, typed with the first audio type this phone will accept. */
export function makeShareFile(blob: Blob, name: string, mime: string, nav: ShareNav = navigator): File {
  const types = candidateTypes(mime);
  for (const type of types) {
    const file = new File([blob], name, { type });
    if (nav.canShare?.({ files: [file] })) return file;
  }
  return new File([blob], name, { type: types[0] });
}

export function canShareFiles(files: File[], nav: ShareNav = navigator): boolean {
  return typeof nav.canShare === "function" && typeof nav.share === "function" && nav.canShare({ files });
}

export function whatsappUrl(text: string): string {
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

/** The text that goes with a link: the short message, then the link on its own line. */
export function messageWithLink(message: string, link: string): string {
  return `${message}\n${link}`;
}

export async function shareFiles(files: File[], text: string, nav: ShareNav = navigator): Promise<ShareOutcome> {
  if (!canShareFiles(files, nav)) return "unsupported";
  try {
    await nav.share!({ files, text });
    return "shared";
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") return "cancelled"; // she closed the sheet
    return "failed";
  }
}

/** The phone's share sheet with a link and a short message (no file): WhatsApp is one of its targets. */
export async function shareLink(text: string, url?: string, nav: ShareNav = navigator): Promise<ShareOutcome> {
  if (typeof nav.share !== "function") return "unsupported";
  try {
    await nav.share(url ? { text, url } : { text });
    return "shared";
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") return "cancelled";
    return "failed";
  }
}

/** Fetch (or take from the phone's saved copy) every card's file and make them ready to share. */
export async function filesFor(
  cards: Card[],
  session: Session,
  deps: AudioDeps,
  nav: ShareNav = navigator,
): Promise<File[]> {
  const files: File[] = [];
  for (const c of cards) {
    const { blob } = await getAudioBlob(c.id, session, deps);
    files.push(makeShareFile(blob, c.file_name, c.mime, nav));
  }
  return files;
}

/** Saves a blob to the phone through a temporary link. */
export function saveToPhone(blob: Blob, name: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}
