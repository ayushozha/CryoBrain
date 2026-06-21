import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Label } from "./Label";

function ChipWorld() {
  const group = useRef<THREE.Group>(null);
  const npu = useRef<THREE.Mesh>(null);
  const npuCore = useRef<THREE.Mesh>(null);

  const subGeo = useMemo(() => new THREE.BoxGeometry(9, 0.35, 7), []);
  const npuGeo = useMemo(() => new THREE.BoxGeometry(2.2, 0.9, 2.4), []);

  const qpu: [number, number, number][] = [];
  for (let i = 0; i < 5; i++) for (let j = 0; j < 5; j++) qpu.push([-3.3 + i * 0.55, 0.18, -1.1 + j * 0.55]);

  // control lines QPU <-> NPU — built once (mesh + material, not just geometry)
  const lines = useMemo(() => {
    const out: THREE.Line[] = [];
    for (let j = 0; j < 5; j++) {
      const a = new THREE.Vector3(-1.1, 0.3, -1.1 + j * 0.55);
      const b = new THREE.Vector3(0.3, 0.4, -0.8 + j * 0.4);
      const g = new THREE.BufferGeometry().setFromPoints([a, b]);
      out.push(new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0x64d2ff, transparent: true, opacity: 0.5 })));
    }
    return out;
  }, []);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (group.current) group.current.rotation.y = -0.35 + Math.sin(t * 0.13) * 0.32;
    if (npuCore.current) {
      npuCore.current.rotation.y += 0.02;
      npuCore.current.scale.setScalar(1 + Math.sin(t * 2.4) * 0.15);
    }
    if (npu.current) (npu.current.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.5 + Math.sin(t * 1.6) * 0.12;
  });

  const frameMat = <meshStandardMaterial color={0x9a7b3a} metalness={0.9} roughness={0.3} />;

  return (
    <group ref={group} position={[4.2, -0.6, 0]} scale={0.6}>
      {/* substrate */}
      <mesh geometry={subGeo} position={[0, -0.2, 0]}>
        <meshStandardMaterial color={0x0c0f15} metalness={0.8} roughness={0.35} />
      </mesh>
      <lineSegments position={[0, -0.2, 0]}>
        <edgesGeometry args={[subGeo]} />
        <lineBasicMaterial color={0x1c2530} />
      </lineSegments>

      {/* package frame */}
      <mesh position={[0, 0, 3.5]}>
        <boxGeometry args={[9.4, 0.5, 0.25]} />
        {frameMat}
      </mesh>
      <mesh position={[0, 0, -3.5]}>
        <boxGeometry args={[9.4, 0.5, 0.25]} />
        {frameMat}
      </mesh>
      <mesh position={[4.7, 0, 0]}>
        <boxGeometry args={[0.25, 0.5, 7.2]} />
        {frameMat}
      </mesh>
      <mesh position={[-4.7, 0, 0]}>
        <boxGeometry args={[0.25, 0.5, 7.2]} />
        {frameMat}
      </mesh>

      {/* QPU array */}
      {qpu.map((p, i) => (
        <mesh key={i} position={p}>
          <boxGeometry args={[0.38, 0.3, 0.38]} />
          <meshStandardMaterial color={0x0a1a24} emissive={0x0a90c8} emissiveIntensity={0.7} metalness={0.5} roughness={0.4} />
        </mesh>
      ))}
      <Label text="QPU array" hex={0x64d2ff} position={[-2.5, 1.6, 0]} scale={[2.6, 0.65, 1]} fontPx={28} />

      {/* decoder NPU */}
      <mesh ref={npu} geometry={npuGeo} position={[1.4, 0.35, 0]}>
        <meshStandardMaterial color={0x081019} emissive={0x0a84ff} emissiveIntensity={0.5} metalness={0.85} roughness={0.2} />
      </mesh>
      <lineSegments position={[1.4, 0.35, 0]}>
        <edgesGeometry args={[npuGeo]} />
        <lineBasicMaterial color={0x64d2ff} />
      </lineSegments>
      <mesh ref={npuCore} position={[1.4, 0.95, 0]}>
        <icosahedronGeometry args={[0.3, 1]} />
        <meshBasicMaterial color={0x9be4ff} />
      </mesh>
      <Label text="CryoBrain NPU" hex={0x9be4ff} position={[1.4, 1.9, 0]} scale={[3.0, 0.75, 1]} fontPx={28} />

      {/* local memory */}
      <mesh position={[1.4, 0.15, 2.4]}>
        <boxGeometry args={[1.4, 0.5, 1.2]} />
        <meshStandardMaterial color={0x141820} emissive={0x1d6b35} emissiveIntensity={0.4} metalness={0.7} roughness={0.3} />
      </mesh>
      <Label text="memory" hex={0x30d158} position={[1.4, 0.95, 2.4]} scale={[1.8, 0.45, 1]} fontPx={28} />

      {/* classical interface */}
      <mesh position={[4.0, 0.1, 0]}>
        <boxGeometry args={[0.6, 0.4, 2.4]} />
        <meshStandardMaterial color={0x1a1410} emissive={0xc89b4a} emissiveIntensity={0.3} metalness={0.8} roughness={0.3} />
      </mesh>
      <Label text="classical I/O" hex={0xffb340} position={[4.0, 0.9, 0]} scale={[2.0, 0.5, 1]} fontPx={28} />

      {lines.map((line, i) => (
        <primitive key={i} object={line} />
      ))}
    </group>
  );
}

export function ChipScene() {
  return (
    <Canvas
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
      camera={{ fov: 40, position: [0.6, 9.8, 16.5], near: 0.1, far: 100 }}
      onCreated={({ scene, camera }) => {
        scene.fog = new THREE.FogExp2(0x060608, 0.03);
        camera.lookAt(4.0, -0.5, 0);
      }}
    >
      <ambientLight color={0x3a4250} intensity={1.3} />
      <pointLight color={0x7fd6ff} intensity={60} distance={50} position={[-2, 6, 6]} />
      <pointLight color={0xffffff} intensity={25} distance={40} position={[6, 4, -4]} />
      <ChipWorld />
    </Canvas>
  );
}
