import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { Label } from "./Label";
import type { CryoData, ReplayEvent } from "../data/types";

const AGENTS = ["Research", "Planner", "Architect", "RTL", "Measurement", "Verifier", "Scorer", "Memory"] as const;
const COL: Record<string, number> = {
  Research: 0x64d2ff,
  Planner: 0x64d2ff,
  Architect: 0x9be4ff,
  RTL: 0x0a84ff,
  Measurement: 0x0a84ff,
  Verifier: 0xffd60a,
  Scorer: 0x30d158,
  Memory: 0x30d158,
};
const R = 3.9;

interface NodeRec {
  mesh: THREE.Mesh;
  halo: THREE.Mesh;
  hex: number;
  pulse: number;
}
interface Packet {
  m: THREE.Mesh;
  from: THREE.Vector3;
  to: THREE.Vector3;
  t0: number;
  dur: number;
  onArrive?: () => void;
}

function position(i: number): THREE.Vector3 {
  const ang = (i / AGENTS.length) * Math.PI * 2 - Math.PI / 2;
  return new THREE.Vector3(Math.cos(ang) * R, Math.sin(ang) * R, 0);
}

function SwarmWorld({ data, onEvent, active }: { data: CryoData; onEvent: (e: ReplayEvent) => void; active: boolean }) {
  const group = useRef<THREE.Group>(null);
  const chip = useRef<THREE.Mesh>(null);
  const chipEdge = useRef<THREE.LineSegments>(null);
  const { scene } = useThree();

  const positions = useMemo(() => {
    const m: Record<string, THREE.Vector3> = {};
    AGENTS.forEach((n, i) => (m[n] = position(i)));
    return m;
  }, []);

  const nodes = useRef<Record<string, NodeRec>>({});
  const chipPulse = useRef(0);
  const packets = useRef<Packet[]>([]);
  const idx = useRef(0);
  const lastNode = useRef<string>("Memory");
  const activeRef = useRef(active);
  activeRef.current = active;

  const chipGeo = useMemo(() => new THREE.BoxGeometry(1.7, 1.7, 0.5), []);

  // pipeline ring edges — built once (recreating geometries per render leaks)
  const edges = useMemo(
    () =>
      AGENTS.map((name, i) => {
        const a = positions[name];
        const b = positions[AGENTS[(i + 1) % AGENTS.length]];
        const g = new THREE.BufferGeometry().setFromPoints([a, b]);
        return new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.1 }));
      }),
    [positions],
  );

  const spawnPacket = (from: THREE.Vector3, to: THREE.Vector3, hex: number, onArrive?: () => void) => {
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 12), new THREE.MeshBasicMaterial({ color: hex }));
    m.position.copy(from);
    group.current?.add(m);
    packets.current.push({ m, from: from.clone(), to: to.clone(), t0: performance.now(), dur: 620, onArrive });
  };

  // step the real replay on a fixed cadence (only while section is active)
  useEffect(() => {
    idx.current = 0;
    lastNode.current = "Memory";
    const step = () => {
      if (!activeRef.current) return;
      const ev = data.replay[idx.current % data.replay.length];
      idx.current += 1;
      const nd = nodes.current[ev.agent];
      if (nd) nd.pulse = 1;
      let hex = 0x64d2ff;
      if (ev.agent === "Verifier") hex = ev.gates === false ? 0xff453a : 0x30d158;
      else if (ev.agent === "Scorer") hex = ev.valid === false ? 0xff453a : 0x30d158;
      else if (ev.agent === "Measurement") hex = 0x0a84ff;
      else if (nd) hex = nd.hex;
      const fromP = positions[lastNode.current] || positions.Memory;
      const toP = positions[ev.agent] || positions.Research;
      spawnPacket(fromP, toP, hex);
      if (ev.agent === "RTL" || ev.agent === "Measurement") spawnPacket(toP, new THREE.Vector3(0, 0, 0), 0x0a84ff);
      if (ev.agent === "Memory" && ev.action === "record_variant")
        spawnPacket(toP, new THREE.Vector3(0, 0, 0.4), 0x30d158, () => {
          chipPulse.current = 1;
        });
      lastNode.current = ev.agent;
      onEvent(ev);
    };
    step();
    const timer = setInterval(step, 820);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (group.current) group.current.rotation.y = Math.sin(t * 0.18) * 0.28;
    if (chip.current) {
      chip.current.rotation.z = t * 0.25;
      (chip.current.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.4 + chipPulse.current * 0.8;
    }
    if (chipEdge.current) chipEdge.current.rotation.z = t * 0.25;
    chipPulse.current = Math.max(0, chipPulse.current - 0.012);

    Object.values(nodes.current).forEach((n) => {
      const s = 1 + n.pulse * 0.5;
      n.mesh.scale.setScalar(s);
      (n.mesh.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.45 + n.pulse * 0.9;
      n.halo.material && ((n.halo.material as THREE.MeshBasicMaterial).opacity = 0.25 + n.pulse * 0.6);
      n.halo.scale.setScalar(1 + n.pulse * 0.4);
      n.pulse = Math.max(0, n.pulse - 0.018);
    });

    const now = performance.now();
    for (let k = packets.current.length - 1; k >= 0; k--) {
      const p = packets.current[k];
      let u = (now - p.t0) / p.dur;
      if (u >= 1) {
        group.current?.remove(p.m);
        p.m.geometry.dispose();
        (p.m.material as THREE.Material).dispose();
        packets.current.splice(k, 1);
        p.onArrive?.();
        continue;
      }
      const e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
      p.m.position.lerpVectors(p.from, p.to, e);
      (p.m.material as THREE.MeshBasicMaterial).opacity = 1 - u * 0.3;
    }
    void scene;
  });

  return (
    <group ref={group} rotation={[0.28, 0, 0]} position={[2.7, 0.1, 0]}>
      {AGENTS.map((name) => {
        const p = positions[name];
        const hex = COL[name];
        return (
          <group key={name}>
            <mesh
              position={[p.x, p.y, p.z]}
              ref={(m) => {
                if (m) {
                  nodes.current[name] = nodes.current[name] || ({ hex, pulse: 0 } as NodeRec);
                  nodes.current[name].mesh = m;
                  nodes.current[name].hex = hex;
                }
              }}
            >
              <sphereGeometry args={[0.42, 24, 24]} />
              <meshStandardMaterial color={0x0a0c10} emissive={hex} emissiveIntensity={0.45} metalness={0.6} roughness={0.3} />
            </mesh>
            <mesh
              position={[p.x, p.y, p.z]}
              ref={(m) => {
                if (m) {
                  nodes.current[name] = nodes.current[name] || ({ hex, pulse: 0 } as NodeRec);
                  nodes.current[name].halo = m;
                }
              }}
            >
              <ringGeometry args={[0.55, 0.62, 32]} />
              <meshBasicMaterial color={hex} transparent opacity={0.35} side={THREE.DoubleSide} />
            </mesh>
            <Label text={name} hex={hex} position={[p.x, p.y + 0.95, p.z]} scale={[3.0, 0.75, 1]} />
          </group>
        );
      })}

      {/* pipeline ring edges */}
      {edges.map((line, i) => (
        <primitive key={`e${i}`} object={line} />
      ))}

      {/* central decoder chip */}
      <mesh ref={chip} geometry={chipGeo}>
        <meshStandardMaterial color={0x081019} emissive={0x0a84ff} emissiveIntensity={0.4} metalness={0.85} roughness={0.2} />
      </mesh>
      <lineSegments ref={chipEdge}>
        <edgesGeometry args={[chipGeo]} />
        <lineBasicMaterial color={0x64d2ff} />
      </lineSegments>
      <Label text="decoder core" hex={0x9be4ff} position={[0, -1.4, 0]} scale={[3.4, 0.8, 1]} />
    </group>
  );
}

export function SwarmScene({ data, onEvent, active }: { data: CryoData; onEvent: (e: ReplayEvent) => void; active: boolean }) {
  return (
    <Canvas
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
      camera={{ fov: 46, position: [0, 0.3, 21], near: 0.1, far: 100 }}
    >
      <ambientLight color={0x4a5260} intensity={1.4} />
      <pointLight color={0x7fd6ff} intensity={50} distance={60} position={[0, 4, 12]} />
      <pointLight color={0xffffff} intensity={20} distance={40} position={[-8, -6, 6]} />
      <SwarmWorld data={data} onEvent={onEvent} active={active} />
    </Canvas>
  );
}
