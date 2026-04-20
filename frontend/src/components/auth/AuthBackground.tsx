import React, { useRef, useMemo, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

// ═══════════════════════════════════════════════════════════════
// STARFIELD — 900 procedural stars with color variation,
// cinematic rotation crawl, and mouse-reactive parallax.
// ═══════════════════════════════════════════════════════════════
function Starfield({ count = 900 }) {
  const pointsRef = useRef<THREE.Points>(null)

  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)

    for (let i = 0; i < count; i++) {
      // Distribute in a spherical shell (12–50 unit radius)
      const radius = 12 + Math.random() * 38
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)

      positions[i * 3]     = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = radius * Math.cos(phi)

      // Color variation: cool white, pale blue, warm amber
      const roll = Math.random()
      if (roll < 0.55) {
        // Cool white
        colors[i * 3]     = 0.85 + Math.random() * 0.15
        colors[i * 3 + 1] = 0.88 + Math.random() * 0.12
        colors[i * 3 + 2] = 0.92 + Math.random() * 0.08
      } else if (roll < 0.8) {
        // Pale blue
        colors[i * 3]     = 0.6 + Math.random() * 0.15
        colors[i * 3 + 1] = 0.7 + Math.random() * 0.15
        colors[i * 3 + 2] = 0.95 + Math.random() * 0.05
      } else {
        // Warm amber/orange
        colors[i * 3]     = 0.95 + Math.random() * 0.05
        colors[i * 3 + 1] = 0.5 + Math.random() * 0.25
        colors[i * 3 + 2] = 0.2 + Math.random() * 0.15
      }
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
    return geo
  }, [count])

  // Slow cinematic rotation + mouse parallax
  useFrame((state) => {
    if (!pointsRef.current) return
    const t = state.clock.elapsedTime

    // Base cinematic crawl
    pointsRef.current.rotation.y = t * 0.008
    pointsRef.current.rotation.x = t * 0.003

    // Lazy mouse parallax (very low lerp for deep-space inertia)
    const px = state.pointer.x * 0.06
    const py = state.pointer.y * 0.04
    pointsRef.current.rotation.y += (px - pointsRef.current.rotation.y * 0.01) * 0.008
    pointsRef.current.rotation.x += (py - pointsRef.current.rotation.x * 0.01) * 0.008
  })

  return (
    <points ref={pointsRef} geometry={geometry}>
      <pointsMaterial
        size={0.15}
        vertexColors
        transparent
        opacity={0.9}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  )
}

// ═══════════════════════════════════════════════════════════════
// NEBULA CLOUD — Large translucent sphere with additive blending.
// Multiple instances at different depths create volumetric feel.
// Each slowly rotates and "breathes" via subtle scale oscillation.
// ═══════════════════════════════════════════════════════════════
function NebulaCloud({
  position,
  color,
  scale,
  speed,
  opacity = 0.05
}: {
  position: [number, number, number]
  color: string
  scale: number
  speed: number
  opacity?: number
}) {
  const meshRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (!meshRef.current) return
    const t = state.clock.elapsedTime
    meshRef.current.rotation.z = t * speed
    meshRef.current.rotation.y = t * speed * 0.6
    // Gentle breathing
    const breath = 1 + Math.sin(t * 0.35 + position[0]) * 0.04
    meshRef.current.scale.setScalar(scale * breath)
  })

  return (
    <mesh ref={meshRef} position={position}>
      <sphereGeometry args={[1, 32, 32]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        side={THREE.BackSide}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </mesh>
  )
}

// ═══════════════════════════════════════════════════════════════
// VOID GRID — Subtle perspective grid on the ground plane.
// Fades into distance via fog. Gives depth + command-center feel.
// ═══════════════════════════════════════════════════════════════
function VoidGrid() {
  const gridRef = useRef<THREE.GridHelper>(null)

  useEffect(() => {
    if (!gridRef.current) return
    // Make grid lines transparent
    const mat = gridRef.current.material
    if (Array.isArray(mat)) {
      mat.forEach(m => {
        m.transparent = true
        m.opacity = 0.045
        m.depthWrite = false
      })
    } else {
      (mat as THREE.Material).transparent = true;
      (mat as THREE.Material).opacity = 0.045;
      (mat as THREE.Material).depthWrite = false
    }
  }, [])

  return (
    <gridHelper
      ref={gridRef}
      args={[100, 50, '#FF5722', '#1a1a3e']}
      position={[0, -7, 0]}
    />
  )
}

// ═══════════════════════════════════════════════════════════════
// SCENE COMPOSITION — All elements assembled with 3-point lighting.
// ═══════════════════════════════════════════════════════════════
function DigitalVoidScene() {
  return (
    <>
      {/* Ambient fill — cool-toned for deep space */}
      <ambientLight intensity={0.12} color="#6677aa" />

      {/* Key light — warm accent (upper-right) */}
      <directionalLight position={[6, 4, 5]} intensity={0.2} color="#FF5722" />

      {/* Fill light — cool blue (lower-left, softer) */}
      <directionalLight position={[-5, -3, 4]} intensity={0.1} color="#3355aa" />

      {/* Stars */}
      <Starfield count={900} />

      {/* Nebula clouds — layered for depth */}
      <NebulaCloud position={[5, -2, -22]}   color="#FF5722" scale={8}  speed={0.015}  opacity={0.04} />
      <NebulaCloud position={[-7, 3, -28]}   color="#3344aa" scale={10} speed={-0.01}  opacity={0.035} />
      <NebulaCloud position={[1, -1, -18]}   color="#6633aa" scale={7}  speed={0.012}  opacity={0.03} />
      <NebulaCloud position={[-3, -5, -35]}  color="#FF8a50" scale={13} speed={-0.008} opacity={0.025} />

      {/* Ground grid */}
      <VoidGrid />
    </>
  )
}

// ═══════════════════════════════════════════════════════════════
// EXPORT — Canvas wrapper with camera, fog, and performance tuning.
// ═══════════════════════════════════════════════════════════════
export default function AuthBackground() {
  return (
    <div className="absolute inset-0 pointer-events-auto z-0" style={{ backgroundColor: '#0B0F19' }}>
      <Canvas
        camera={{ position: [0, 0, 12], fov: 60 }}
        gl={{ antialias: true, alpha: false }}
        dpr={[1, 1.5]}
      >
        <fog attach="fog" args={['#0B0F19', 10, 55]} />
        <DigitalVoidScene />
      </Canvas>
    </div>
  )
}
