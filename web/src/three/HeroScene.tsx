import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

const QPU = new THREE.Vector3(-1.7, -3.4, 0);
const BRAIN = new THREE.Vector3(1.7, -3.35, 0);
const ARC = 1.6;

// One additive particle stream travelling from -> to along an arc.
function useStream(from: THREE.Vector3, to: THREE.Vector3, n: number) {
  return useMemo(() => {
    const pos = new Float32Array(n * 3);
    const prog = new Float32Array(n);
    // deterministic spread so SSR/strict-mode double-mount looks stable
    for (let i = 0; i < n; i++) prog[i] = (Math.sin(i * 7.13) * 0.5 + 0.5) % 1;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    return { geo, pos, prog, from: from.clone(), to: to.clone(), n };
  }, [from, to, n]);
}

function Streams() {
  const syn = useStream(QPU, BRAIN, 90);
  const corr = useStream(BRAIN, QPU, 70);

  const advance = (
    s: { pos: Float32Array; prog: Float32Array; from: THREE.Vector3; to: THREE.Vector3; n: number; geo: THREE.BufferGeometry },
    speed: number,
    dt: number,
  ) => {
    for (let i = 0; i < s.n; i++) {
      s.prog[i] += speed * dt + 0.0005;
      if (s.prog[i] > 1) s.prog[i] -= 1;
      const t = s.prog[i];
      const jx = (Math.sin(i * 12.9 + t * 30) - 0.5) * 0.05;
      const jz = (Math.sin(i * 7.7 + t * 24) - 0.5) * 0.05;
      s.pos[i * 3] = s.from.x + (s.to.x - s.from.x) * t + jx;
      s.pos[i * 3 + 1] = s.from.y + (s.to.y - s.from.y) * t + Math.sin(t * Math.PI) * ARC;
      s.pos[i * 3 + 2] = s.from.z + (s.to.z - s.from.z) * t + jz;
    }
    s.geo.attributes.position.needsUpdate = true;
  };

  useFrame((_, delta) => {
    const dt = Math.min(delta, 0.05);
    advance(syn, 0.35, dt);
    advance(corr, 0.28, dt);
  });

  return (
    <>
      <points geometry={syn.geo}>
        <pointsMaterial
          color={0x64d2ff}
          size={0.12}
          transparent
          opacity={0.95}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
      <points geometry={corr.geo}>
        <pointsMaterial
          color={0xffb340}
          size={0.12}
          transparent
          opacity={0.95}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
    </>
  );
}

function CryostatRings() {
  const rings = [0, 1, 2, 3, 4, 5];
  const rods = [0, 1, 2, 3, 4, 5];
  return (
    <>
      {rings.map((i) => (
        <mesh key={`r${i}`} rotation={[Math.PI / 2, 0, 0]} position={[0, 5.2 - i * 1.5, 0]}>
          <torusGeometry args={[4.4 - i * 0.55, 0.05, 10, 96]} />
          <meshStandardMaterial color={0xc89b4a} metalness={0.95} roughness={0.32} emissive={0x140d03} />
        </mesh>
      ))}
      {rods.map((a) => {
        const ang = (a / 6) * Math.PI * 2;
        return (
          <mesh key={`rod${a}`} position={[Math.cos(ang) * 2.6, 0.6, Math.sin(ang) * 2.6]}>
            <cylinderGeometry args={[0.03, 0.03, 9, 8]} />
            <meshStandardMaterial color={0x8a6a2e} metalness={0.9} roughness={0.4} />
          </mesh>
        );
      })}
    </>
  );
}

function Qpu() {
  const cells: [number, number, number][] = [];
  for (let x = -1; x <= 1; x++) for (let z = -1; z <= 1; z++) cells.push([QPU.x + x * 0.5, QPU.y, QPU.z + z * 0.5]);
  return (
    <>
      {cells.map((p, i) => (
        <mesh key={i} position={p}>
          <boxGeometry args={[0.34, 0.34, 0.34]} />
          <meshStandardMaterial color={0x0e1116} metalness={0.5} roughness={0.5} emissive={0x0a3a55} emissiveIntensity={0.7} />
        </mesh>
      ))}
      <mesh position={[QPU.x, QPU.y - 0.25, QPU.z]}>
        <boxGeometry args={[2.0, 0.08, 2.0]} />
        <meshStandardMaterial color={0x14181e} metalness={0.7} roughness={0.4} />
      </mesh>
    </>
  );
}

function Brain() {
  const core = useRef<THREE.Mesh>(null);
  const boxGeo = useMemo(() => new THREE.BoxGeometry(1.7, 0.9, 1.7), []);
  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (core.current) {
      core.current.rotation.y += 0.01;
      core.current.rotation.x += 0.006;
      core.current.scale.setScalar(1 + Math.sin(t * 2.2) * 0.12);
    }
  });
  return (
    <group position={[BRAIN.x, BRAIN.y, BRAIN.z]}>
      <mesh geometry={boxGeo}>
        <meshStandardMaterial color={0x080a0e} metalness={0.85} roughness={0.22} emissive={0x0a84ff} emissiveIntensity={0.32} />
      </mesh>
      <lineSegments>
        <edgesGeometry args={[boxGeo]} />
        <lineBasicMaterial color={0x64d2ff} />
      </lineSegments>
      <mesh ref={core}>
        <icosahedronGeometry args={[0.34, 1]} />
        <meshBasicMaterial color={0x9be4ff} transparent opacity={0.9} />
      </mesh>
    </group>
  );
}

function HeroWorld() {
  const group = useRef<THREE.Group>(null);
  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (group.current) group.current.rotation.y = Math.sin(t * 0.12) * 0.5 + 0.3;
    state.camera.position.y = 1.5 + Math.sin(t * 0.35) * 0.5;
    state.camera.lookAt(0, -1.2, 0);
  });
  return (
    <group ref={group}>
      <CryostatRings />
      <Qpu />
      <Brain />
      <Streams />
    </group>
  );
}

export function HeroScene() {
  return (
    <Canvas
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
      camera={{ fov: 44, position: [0, 1.5, 14], near: 0.1, far: 100 }}
      onCreated={({ scene }) => {
        scene.fog = new THREE.FogExp2(0x060608, 0.034);
      }}
    >
      <ambientLight color={0x3a4250} intensity={1.3} />
      <pointLight color={0x7fd6ff} intensity={70} distance={50} position={[4, 3, 7]} />
      <pointLight color={0xffaa44} intensity={30} distance={36} position={[-6, -2, -4]} />
      <directionalLight color={0xffffff} intensity={0.4} position={[0, 8, 2]} />
      <HeroWorld />
    </Canvas>
  );
}
