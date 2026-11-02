// A scene a flow step refers to, drawn here from the same data the bot turns into a PNG.
import { renderLayout } from "../sprites";
import type { SceneRef } from "../lib/flow";

interface Props {
  scene: SceneRef;
  /** The server's words for what the picture shows, in her language. */
  label: string;
}

export function SceneView({ scene, label }: Props) {
  let svg: string;
  try {
    svg = renderLayout(scene.layout, scene.item, scene.args, scene.palette, scene.seed).svg;
  } catch {
    return null; // the words still show; a picture that cannot be drawn is left out
  }
  return <div className="sprite" role="img" aria-label={label} dangerouslySetInnerHTML={{ __html: svg }} />;
}
