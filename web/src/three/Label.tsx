import { useEffect, useMemo } from "react";
import * as THREE from "three";

// Canvas-texture text sprite — ports the design's mkLabel() helper.
export function Label({
  text,
  hex,
  position,
  scale = [3.0, 0.75, 1],
  fontPx = 30,
}: {
  text: string;
  hex: number;
  position: [number, number, number];
  scale?: [number, number, number];
  fontPx?: number;
}) {
  const texture = useMemo(() => {
    const c = document.createElement("canvas");
    c.width = 256;
    c.height = 64;
    const x = c.getContext("2d")!;
    x.font = `600 ${fontPx}px -apple-system, Helvetica, Arial, sans-serif`;
    x.fillStyle = "#" + hex.toString(16).padStart(6, "0");
    x.textAlign = "center";
    x.textBaseline = "middle";
    x.fillText(text, 128, 36);
    const tex = new THREE.CanvasTexture(c);
    tex.needsUpdate = true;
    return tex;
  }, [text, hex, fontPx]);

  useEffect(() => () => texture.dispose(), [texture]);

  return (
    <sprite position={position} scale={scale}>
      <spriteMaterial map={texture} transparent depthTest={false} />
    </sprite>
  );
}
