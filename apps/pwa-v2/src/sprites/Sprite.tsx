// Draws one sprite scene as inline SVG. The SVG is built by our own renderer from approved data and
// passes the guard first; this component only places it and names it for screen readers.
import { t } from "../i18n";
import type { Key, Lang } from "../i18n";
import { validateSvg } from "./grammar";

interface Props {
  svg: string;
  lang: Lang;
  /** What the picture shows in words, from the layout's own report (counts come from code). */
  count?: number;
  className?: string;
}

export function Sprite({ svg, lang, count, className = "sprite" }: Props) {
  if (validateSvg(svg).length) return null;
  const key = /data-alt="([a-z0-9_.]+)"/.exec(svg)?.[1] as Key | undefined;
  const base = key ? t(lang, key) : "";
  const label = count === undefined ? base : `${base}: ${count}`;
  return <div className={className} role="img" aria-label={label} dangerouslySetInnerHTML={{ __html: svg }} />;
}
