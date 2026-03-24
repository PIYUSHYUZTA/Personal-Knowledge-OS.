import React, { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { knowledgeAPI } from '@/services/api'
import { GraphEntity, GraphRelationship } from '@/types'

// ---------------------------------------------------------------------------
// Heatmap helpers (Phase 3.5)
// ---------------------------------------------------------------------------

/** Normalise a raw hit-count weight to [0, 1] using log-scaling (same curve as backend). */
function normaliseWeight(rawWeight: number): number {
  return Math.min(1.0, Math.log1p(rawWeight) / Math.log1p(50))
}

/** Return emissive hex colour and intensity based on normalised intensity (0-1). */
function glowConfig(intensity: number): { color: number; emissiveIntensity: number } {
  if (intensity > 0.7) {
    // Hot – bright white / neon (core expertise)
    return { color: 0xffffff, emissiveIntensity: intensity }
  } else if (intensity > 0.4) {
    // Warm – cyan (moderately integrated concepts)
    return { color: 0x00e5ff, emissiveIntensity: intensity * 0.85 }
  } else {
    // Cold – blue (new / rarely accessed knowledge)
    return { color: 0x2979ff, emissiveIntensity: Math.max(0.05, intensity * 0.6) }
  }
}

interface Node {
  id: string
  name: string
  type: string
  weight: number           // normalised [0, 1]
  position: THREE.Vector3
  mesh: THREE.Mesh
  velocity: THREE.Vector3
}

interface Edge {
  source: Node
  target: Node
  line: THREE.Line
}

interface KnowledgeGraphVisualiserProps {
  token?: string
}

/**
 * Three.js 3D Knowledge Graph Visualiser
 *
 * Renders knowledge base as interactive 3D graph where:
 * - Nodes represent knowledge chunks/entities
 * - Edges represent relationships
 * - Physics simulation provides force-directed layout
 * - Click nodes to view metadata
 * - Drag to rotate, scroll to zoom
 */
const KnowledgeGraphVisualiser: React.FC<KnowledgeGraphVisualiserProps> = ({ token }) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const nodesRef = useRef<Map<string, Node>>(new Map())
  const edgesRef = useRef<Edge[]>([])
  const controlsRef = useRef<{
    isDragging: boolean
    previousMousePosition: { x: number; y: number }
  }>({
    isDragging: false,
    previousMousePosition: { x: 0, y: 0 },
  })

  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  const tokenRef = useRef<string | undefined>(token)

  useEffect(() => {
    if (!containerRef.current) return

    // === THREE.js Setup ===
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0f172a)
    sceneRef.current = scene

    const camera = new THREE.PerspectiveCamera(
      75,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      10000
    )
    camera.position.z = 50
    cameraRef.current = camera

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    containerRef.current.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
    scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
    directionalLight.position.set(50, 50, 50)
    scene.add(directionalLight)

    // === Load Graph Data ===
    const loadGraphData = async () => {
      try {
        const graphData = await knowledgeAPI.getGraph()

        if (!graphData.entities || graphData.entities.length === 0) {
          // Create sample nodes for demo
          createSampleGraph(scene)
          return
        }

        // Create nodes from entities
        graphData.entities.forEach((entity: GraphEntity, index: number) => {
          const angle = (index / graphData.entities.length) * Math.PI * 2
          const radius = 20

          const node = createNode(
            entity.id,
            entity.entity_name,
            entity.entity_type,
            normaliseWeight(entity.weight ?? 0),
            new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0),
            scene
          )

          nodesRef.current.set(entity.id, node)
        })

        // Create edges from relationships
        graphData.relationships?.forEach((rel: GraphRelationship) => {
          const sourceNode = nodesRef.current.get(rel.source_entity.id)
          const targetNode = nodesRef.current.get(rel.target_entity.id)

          if (sourceNode && targetNode) {
            const edge = createEdge(sourceNode, targetNode, scene)
            edgesRef.current.push(edge)
          }
        })
      } catch (error) {
        console.error('Failed to load graph data:', error)
        createSampleGraph(scene)
      }
    }

    const createSampleGraph = (scene: THREE.Scene) => {
      // Create sample nodes for demo
      const sampleNodes = [
        { id: '1', name: 'Machine Learning', type: 'CONCEPT' },
        { id: '2', name: 'Neural Networks', type: 'CONCEPT' },
        { id: '3', name: 'Deep Learning', type: 'CONCEPT' },
        { id: '4', name: 'Python', type: 'TOOL' },
        { id: '5', name: 'PyTorch', type: 'TOOL' },
      ]

      sampleNodes.forEach((data, index) => {
        const angle = (index / sampleNodes.length) * Math.PI * 2
        const radius = 20
        // Stagger sample weights so all three glow tiers are visible in demo mode
        const demoWeight = normaliseWeight(index * 10)

        const node = createNode(
          data.id,
          data.name,
          data.type,
          demoWeight,
          new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0),
          scene
        )

        nodesRef.current.set(data.id, node)
      })

      // Create sample edges
      ;[
        ['1', '2'],
        ['2', '3'],
        ['1', '3'],
        ['4', '5'],
      ].forEach(([src, tgt]) => {
        const sourceNode = nodesRef.current.get(src)
        const targetNode = nodesRef.current.get(tgt)

        if (sourceNode && targetNode) {
          const edge = createEdge(sourceNode, targetNode, scene)
          edgesRef.current.push(edge)
        }
      })
    }

    loadGraphData()

    // === Force-Directed Physics ===
    const physicsStep = () => {
      const nodes = Array.from(nodesRef.current.values())
      const friction = 0.99
      const attraction = 0.01
      const repulsion = 100

      // Repulsion between nodes
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const nodeA = nodes[i]
          const nodeB = nodes[j]

          const dx = nodeB.position.x - nodeA.position.x
          const dy = nodeB.position.y - nodeA.position.y
          const distance = Math.sqrt(dx * dx + dy * dy) + 0.01

          const force = repulsion / (distance * distance)

          nodeA.velocity.x -= (force * dx) / distance
          nodeA.velocity.y -= (force * dy) / distance

          nodeB.velocity.x += (force * dx) / distance
          nodeB.velocity.y += (force * dy) / distance
        }
      }

      // Attraction along edges
      edgesRef.current.forEach((edge) => {
        const dx = edge.target.position.x - edge.source.position.x
        const dy = edge.target.position.y - edge.source.position.y
        const distance = Math.sqrt(dx * dx + dy * dy)

        const force = attraction * distance

        edge.source.velocity.x += (force * dx) / distance
        edge.source.velocity.y += (force * dy) / distance

        edge.target.velocity.x -= (force * dx) / distance
        edge.target.velocity.y -= (force * dy) / distance
      })

      // Apply velocity and friction
      nodes.forEach((node) => {
        node.position.add(node.velocity)
        node.velocity.multiplyScalar(friction)
        node.mesh.position.copy(node.position)
      })

      // Update edges
      edgesRef.current.forEach((edge) => {
        const geometry = edge.line.geometry as THREE.BufferGeometry
        const positions = new Float32Array([
          edge.source.position.x,
          edge.source.position.y,
          edge.source.position.z,
          edge.target.position.x,
          edge.target.position.y,
          edge.target.position.z,
        ])

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
        geometry.attributes.position.needsUpdate = true
      })
    }

    // === Interaction ===
    const raycaster = new THREE.Raycaster()
    const mouse = new THREE.Vector2()

    const onMouseMove = (event: MouseEvent) => {
      if (containerRef.current) {
        mouse.x = (event.clientX / containerRef.current.clientWidth) * 2 - 1
        mouse.y = -(event.clientY / containerRef.current.clientHeight) * 2 + 1

        if (controlsRef.current.isDragging) {
          const deltaX = event.clientX - controlsRef.current.previousMousePosition.x
          const deltaY = event.clientY - controlsRef.current.previousMousePosition.y

          if (cameraRef.current) {
            cameraRef.current.position.x -= (deltaX * 0.01 * cameraRef.current.position.z) / 10
            cameraRef.current.position.y += (deltaY * 0.01 * cameraRef.current.position.z) / 10
          }
        }

        controlsRef.current.previousMousePosition = { x: event.clientX, y: event.clientY }
      }
    }

    const onMouseDown = () => {
      controlsRef.current.isDragging = true
    }

    const onMouseUp = () => {
      controlsRef.current.isDragging = false
    }

    const onClick = (event: MouseEvent) => {
      if (containerRef.current && cameraRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

        raycaster.setFromCamera(mouse, cameraRef.current)

        const objects = Array.from(nodesRef.current.values()).map((n) => n.mesh)
        const intersects = raycaster.intersectObjects(objects)

        if (intersects.length > 0) {
          const clickedMesh = intersects[0].object
          const clickedNode = Array.from(nodesRef.current.values()).find(
            (n) => n.mesh === clickedMesh
          )

          if (clickedNode) {
            setSelectedNode(clickedNode)

            // Phase 3.5: record interaction hit so the backend heatmap stays live
            if (tokenRef.current) {
              fetch(
                `/api/heatmap/record-interaction`,
                {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${tokenRef.current}`,
                  },
                  body: JSON.stringify({
                    entity_name: clickedNode.name,
                    hit_weight: 0.5,
                  }),
                }
              ).catch(() => { /* fire-and-forget – don't break the 3D view */ })
            }
          }
        }
      }
    }

    const onWheel = (event: WheelEvent) => {
      event.preventDefault()

      if (cameraRef.current) {
        cameraRef.current.position.z += event.deltaY * 0.05

        cameraRef.current.position.z = Math.max(10, Math.min(500, cameraRef.current.position.z))
      }
    }

    renderer.domElement.addEventListener('mousemove', onMouseMove)
    renderer.domElement.addEventListener('mousedown', onMouseDown)
    renderer.domElement.addEventListener('mouseup', onMouseUp)
    renderer.domElement.addEventListener('click', onClick)
    renderer.domElement.addEventListener('wheel', onWheel, { passive: false })

    // === Animation Loop ===
    const animate = () => {
      requestAnimationFrame(animate)

      physicsStep()

      if (sceneRef.current && rendererRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current)
      }
    }

    animate()

    // Cleanup
    return () => {
      renderer.domElement.removeEventListener('mousemove', onMouseMove)
      renderer.domElement.removeEventListener('mousedown', onMouseDown)
      renderer.domElement.removeEventListener('mouseup', onMouseUp)
      renderer.domElement.removeEventListener('click', onClick)
      renderer.domElement.removeEventListener('wheel', onWheel)

      renderer.dispose()
      containerRef.current?.removeChild(renderer.domElement)
    }
  }, [])

  const createNode = (
    id: string,
    name: string,
    type: string,
    weight: number,          // normalised [0, 1]
    position: THREE.Vector3,
    scene: THREE.Scene
  ): Node => {
    // Node size grows slightly with expertise
    const baseRadius = 2
    const radius = baseRadius + weight * 1.5
    const geometry = new THREE.SphereGeometry(radius, 32, 32)

    // Phase 3.5: weight overrides the flat type-colour with a glow gradient
    const { color: glowColor, emissiveIntensity } = glowConfig(weight)

    const material = new THREE.MeshStandardMaterial({
      color: glowColor,
      emissive: new THREE.Color(glowColor),
      emissiveIntensity,
      metalness: 0.2,
      roughness: 0.4,
    })
    const mesh = new THREE.Mesh(geometry, material)
    mesh.position.copy(position)
    scene.add(mesh)

    // Glow halo: semi-transparent shell for high-weight nodes
    if (weight > 0.4) {
      const haloGeom = new THREE.SphereGeometry(radius * 1.45, 16, 16)
      const haloMat = new THREE.MeshBasicMaterial({
        color: glowColor,
        transparent: true,
        opacity: 0.12 + weight * 0.18,
        side: THREE.BackSide,
      })
      const halo = new THREE.Mesh(haloGeom, haloMat)
      mesh.add(halo)
    }

    return { id, name, type, weight, position, mesh, velocity: new THREE.Vector3(0, 0, 0) }
  }

  const createEdge = (source: Node, target: Node, scene: THREE.Scene): Edge => {
    const geometry = new THREE.BufferGeometry()
    const positions = new Float32Array([
      source.position.x,
      source.position.y,
      source.position.z,
      target.position.x,
      target.position.y,
      target.position.z,
    ])

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    const material = new THREE.LineBasicMaterial({ color: 0x94a3b8, linewidth: 1 })
    const line = new THREE.Line(geometry, material)

    scene.add(line)

    return { source, target, line }
  }

  return (
    <div className="w-full h-full relative">
      <div ref={containerRef} className="w-full h-full" />

      {selectedNode && (
        <div className="absolute top-4 right-4 bg-slate-800 text-white p-4 rounded-lg shadow-lg max-w-xs">
          <h3 className="font-bold text-lg mb-2">{selectedNode.name}</h3>
          <p className="text-sm text-slate-300">Type: {selectedNode.type}</p>
          <p className="text-xs text-slate-400 mt-2">ID: {selectedNode.id}</p>

          <button
            onClick={() => setSelectedNode(null)}
            className="mt-4 px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
          >
            Close
          </button>
        </div>
      )}

      <div className="absolute bottom-4 left-4 text-slate-400 text-xs bg-slate-900 bg-opacity-75 p-3 rounded">
        <p>🖱️ Drag to rotate | 🔍 Scroll to zoom | 🖱️ Click nodes for details</p>
        <p className="mt-1">Nodes: {nodesRef.current.size} | Edges: {edgesRef.current.length}</p>
      </div>
    </div>
  )
}

export default KnowledgeGraphVisualiser
