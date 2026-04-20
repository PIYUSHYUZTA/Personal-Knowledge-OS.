import React, { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { knowledgeAPI } from '@/services/api'
import { GraphEntity, GraphRelationship } from '@/types'
import { Info, Maximize2, X } from 'lucide-react'

// ---------------------------------------------------------------------------
// Heatmap helpers
// ---------------------------------------------------------------------------

function normaliseWeight(rawWeight: number): number {
  return Math.min(1.0, Math.log1p(rawWeight) / Math.log1p(50))
}

function glowConfig(intensity: number, isDark: boolean): { color: number; emissiveIntensity: number } {
  const baseColor = isDark ? 0x818cf8 : 0x6366f1; // Indigo colors
  const hotColor = isDark ? 0xffffff : 0x111111;
  const coldColor = isDark ? 0x4f46e5 : 0xa5b4fc;

  if (intensity > 0.7) {
    return { color: hotColor, emissiveIntensity: intensity }
  } else if (intensity > 0.4) {
    return { color: baseColor, emissiveIntensity: intensity * 0.85 }
  } else {
    return { color: coldColor, emissiveIntensity: Math.max(0.05, intensity * 0.6) }
  }
}

interface Node {
  id: string
  name: string
  type: string
  weight: number
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
  const [nodesCount, setNodesCount] = useState(0)
  const [edgesCount, setEdgesCount] = useState(0)

  useEffect(() => {
    if (!containerRef.current) return

    const isDark = document.documentElement.classList.contains('dark');
    const bgColor = isDark ? 0x0A0A0A : 0xFAFAFA;
    const edgeColor = isDark ? 0x262626 : 0xE5E5E5;

    // === THREE.js Setup ===
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(bgColor)
    scene.fog = new THREE.FogExp2(bgColor, 0.005)
    sceneRef.current = scene

    const camera = new THREE.PerspectiveCamera(
      60,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      10000
    )
    camera.position.z = 80
    cameraRef.current = camera

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    containerRef.current.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4)
    scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.6)
    directionalLight.position.set(50, 50, 50)
    scene.add(directionalLight)

    // === Load Graph Data ===
    const loadGraphData = async () => {
      try {
        const graphData = await knowledgeAPI.getGraph()

        if (!graphData.entities || graphData.entities.length === 0) {
          createSampleGraph(scene, isDark, edgeColor)
          return
        }

        graphData.entities.forEach((entity: GraphEntity, index: number) => {
          const angle = (index / graphData.entities.length) * Math.PI * 2
          const radius = Math.random() * 40

          const node = createNode(
            entity.id,
            entity.entity_name,
            entity.entity_type,
            normaliseWeight(entity.weight ?? 0),
            new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, (Math.random() - 0.5) * 20),
            scene,
            isDark
          )

          nodesRef.current.set(entity.id, node)
        })

        graphData.relationships?.forEach((rel: GraphRelationship) => {
          const sourceNode = nodesRef.current.get(rel.source_entity.id)
          const targetNode = nodesRef.current.get(rel.target_entity.id)

          if (sourceNode && targetNode) {
            const edge = createEdge(sourceNode, targetNode, scene, edgeColor)
            edgesRef.current.push(edge)
          }
        })
        
        setNodesCount(nodesRef.current.size)
        setEdgesCount(edgesRef.current.length)
      } catch (error) {
        console.error('Failed to load graph data:', error)
        createSampleGraph(scene, isDark, edgeColor)
      }
    }

    const createSampleGraph = (scene: THREE.Scene, isDark: boolean, edgeColor: number) => {
      const sampleNodes = [
        { id: '1', name: 'Knowledge Graph', type: 'CORE' },
        { id: '2', name: 'Semantic Search', type: 'CONCEPT' },
        { id: '3', name: 'Embeddings', type: 'CONCEPT' },
        { id: '4', name: 'LLM Integration', type: 'TOOL' },
        { id: '5', name: 'Vector Database', type: 'TOOL' },
        { id: '6', name: 'RAG Architecture', type: 'PATTERN' },
      ]

      sampleNodes.forEach((data, index) => {
        const angle = (index / sampleNodes.length) * Math.PI * 2
        const radius = 25
        const demoWeight = normaliseWeight(index * 10 + 5)

        const node = createNode(
          data.id,
          data.name,
          data.type,
          demoWeight,
          new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, (Math.random() - 0.5) * 10),
          scene,
          isDark
        )

        nodesRef.current.set(data.id, node)
      })

      ;[
        ['1', '2'], ['2', '3'], ['1', '3'], ['1', '4'], ['4', '5'], ['1', '6'], ['6', '4']
      ].forEach(([src, tgt]) => {
        const sourceNode = nodesRef.current.get(src)
        const targetNode = nodesRef.current.get(tgt)

        if (sourceNode && targetNode) {
          const edge = createEdge(sourceNode, targetNode, scene, edgeColor)
          edgesRef.current.push(edge)
        }
      })
      setNodesCount(nodesRef.current.size)
      setEdgesCount(edgesRef.current.length)
    }

    loadGraphData()

    // === Force-Directed Physics ===
    const physicsStep = () => {
      const nodes = Array.from(nodesRef.current.values())
      const friction = 0.95
      const attraction = 0.02
      const repulsion = 150

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const nodeA = nodes[i]
          const nodeB = nodes[j]

          const dx = nodeB.position.x - nodeA.position.x
          const dy = nodeB.position.y - nodeA.position.y
          const dz = nodeB.position.z - nodeA.position.z
          const distance = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.1

          const force = repulsion / (distance * distance)

          nodeA.velocity.x -= (force * dx) / distance
          nodeA.velocity.y -= (force * dy) / distance
          nodeA.velocity.z -= (force * dz) / distance

          nodeB.velocity.x += (force * dx) / distance
          nodeB.velocity.y += (force * dy) / distance
          nodeB.velocity.z += (force * dz) / distance
        }
      }

      edgesRef.current.forEach((edge) => {
        const dx = edge.target.position.x - edge.source.position.x
        const dy = edge.target.position.y - edge.source.position.y
        const dz = edge.target.position.z - edge.source.position.z
        const distance = Math.sqrt(dx * dx + dy * dy + dz * dz)

        const force = attraction * (distance - 20) // target distance

        edge.source.velocity.x += (force * dx) / distance
        edge.source.velocity.y += (force * dy) / distance
        edge.source.velocity.z += (force * dz) / distance

        edge.target.velocity.x -= (force * dx) / distance
        edge.target.velocity.y -= (force * dy) / distance
        edge.target.velocity.z -= (force * dz) / distance
      })

      // Central gravity
      nodes.forEach((node) => {
         node.velocity.x += -node.position.x * 0.005
         node.velocity.y += -node.position.y * 0.005
         node.velocity.z += -node.position.z * 0.005

         node.position.add(node.velocity)
         node.velocity.multiplyScalar(friction)
         node.mesh.position.copy(node.position)
      })

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
      })
    }

    // === Interaction ===
    const raycaster = new THREE.Raycaster()
    const mouse = new THREE.Vector2()

    const onMouseMove = (event: MouseEvent) => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

        if (controlsRef.current.isDragging) {
          const deltaX = event.clientX - controlsRef.current.previousMousePosition.x
          const deltaY = event.clientY - controlsRef.current.previousMousePosition.y

          scene.rotation.y += deltaX * 0.005
          scene.rotation.x += deltaY * 0.005
        }

        controlsRef.current.previousMousePosition = { x: event.clientX, y: event.clientY }
      }
    }

    const onMouseDown = () => {
      controlsRef.current.isDragging = true
      if (containerRef.current) containerRef.current.style.cursor = 'grabbing'
    }

    const onMouseUp = () => {
      controlsRef.current.isDragging = false
      if (containerRef.current) containerRef.current.style.cursor = 'grab'
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
          // Handle halo clicks as well
          const clickedNode = Array.from(nodesRef.current.values()).find(
            (n) => n.mesh === clickedMesh || n.mesh.children.includes(clickedMesh as any)
          )

          if (clickedNode) {
            setSelectedNode(clickedNode)

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
              ).catch(() => { /* fire-and-forget */ })
            }
          }
        }
      }
    }

    const onWheel = (event: WheelEvent) => {
      event.preventDefault()
      if (cameraRef.current) {
        cameraRef.current.position.z += event.deltaY * 0.05
        cameraRef.current.position.z = Math.max(20, Math.min(200, cameraRef.current.position.z))
      }
    }

    if (containerRef.current) {
      containerRef.current.style.cursor = 'grab'
      containerRef.current.addEventListener('mousemove', onMouseMove)
      containerRef.current.addEventListener('mousedown', onMouseDown)
      containerRef.current.addEventListener('mouseup', onMouseUp)
      containerRef.current.addEventListener('mouseleave', onMouseUp)
      containerRef.current.addEventListener('click', onClick)
      containerRef.current.addEventListener('wheel', onWheel, { passive: false })
      
      const resizeObserver = new ResizeObserver(() => {
        if (!containerRef.current || !rendererRef.current || !cameraRef.current) return
        const width = containerRef.current.clientWidth
        const height = containerRef.current.clientHeight
        rendererRef.current.setSize(width, height)
        cameraRef.current.aspect = width / height
        cameraRef.current.updateProjectionMatrix()
      })
      resizeObserver.observe(containerRef.current)
    }

    // === Animation Loop ===
    let animationFrameId: number
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate)
      physicsStep()
      
      // Auto-rotation slightly
      if (!controlsRef.current.isDragging && sceneRef.current) {
         sceneRef.current.rotation.y += 0.001
      }

      if (sceneRef.current && rendererRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current)
      }
    }

    animate()

    // Cleanup
    const currentContainer = containerRef.current
    return () => {
      cancelAnimationFrame(animationFrameId)
      if (currentContainer) {
        currentContainer.removeEventListener('mousemove', onMouseMove)
        currentContainer.removeEventListener('mousedown', onMouseDown)
        currentContainer.removeEventListener('mouseup', onMouseUp)
        currentContainer.removeEventListener('mouseleave', onMouseUp)
        currentContainer.removeEventListener('click', onClick)
        currentContainer.removeEventListener('wheel', onWheel)
      }
      renderer.dispose()
    }
  }, [])

  const createNode = (
    id: string,
    name: string,
    type: string,
    weight: number,
    position: THREE.Vector3,
    scene: THREE.Scene,
    isDark: boolean
  ): Node => {
    const baseRadius = 1.5
    const radius = baseRadius + weight * 2
    const geometry = new THREE.IcosahedronGeometry(radius, 2)

    const { color: glowColor, emissiveIntensity } = glowConfig(weight, isDark)

    const material = new THREE.MeshPhysicalMaterial({
      color: glowColor,
      emissive: new THREE.Color(glowColor),
      emissiveIntensity: emissiveIntensity * 0.5,
      metalness: 0.1,
      roughness: 0.2,
      transmission: 0.5,
      thickness: 1.0,
      clearcoat: 1.0,
    })
    
    const mesh = new THREE.Mesh(geometry, material)
    mesh.position.copy(position)
    scene.add(mesh)

    // Optional glow halo
    if (weight > 0.3) {
      const haloGeom = new THREE.IcosahedronGeometry(radius * 1.5, 1)
      const haloMat = new THREE.MeshBasicMaterial({
        color: glowColor,
        transparent: true,
        opacity: 0.1 + weight * 0.1,
        wireframe: true,
      })
      const halo = new THREE.Mesh(haloGeom, haloMat)
      mesh.add(halo)
      
      // Rotate halo slowly
      halo.userData = { isHalo: true }
    }

    return { id, name, type, weight, position, mesh, velocity: new THREE.Vector3(0, 0, 0) }
  }

  const createEdge = (source: Node, target: Node, scene: THREE.Scene, edgeColor: number): Edge => {
    const geometry = new THREE.BufferGeometry()
    const positions = new Float32Array(6)
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    const material = new THREE.LineBasicMaterial({ 
      color: edgeColor, 
      linewidth: 1,
      transparent: true,
      opacity: 0.3
    })
    const line = new THREE.Line(geometry, material)

    scene.add(line)

    return { source, target, line }
  }

  return (
    <div className="w-full h-full relative group">
      <div ref={containerRef} className="w-full h-full absolute inset-0 outline-none" tabIndex={0} />

      {/* Floating UI Elements */}
      <div className="absolute top-4 left-4 flex gap-2">
        <div className="glass px-3 py-1.5 rounded-md flex items-center gap-2 text-xs font-medium text-text-muted shadow-sm">
           <Info size={14} />
           Interactive Knowledge Space
        </div>
      </div>

      <div className="absolute bottom-4 left-4 glass px-4 py-2.5 rounded-md shadow-sm font-mono text-[10px] text-text-muted uppercase tracking-wider flex items-center gap-4">
        <span>Nodes: <span className="text-secondary font-bold">{nodesCount}</span></span>
        <span>Edges: <span className="text-secondary font-bold">{edgesCount}</span></span>
        <span className="opacity-50 ml-2 hidden sm:inline">Left Click + Drag: Rotate • Scroll: Zoom</span>
      </div>

      <button className="absolute bottom-4 right-4 p-2.5 glass rounded-md text-text-muted hover:text-primary transition-colors focus-ring hidden md:block">
        <Maximize2 size={16} />
      </button>

      {/* Node Context Menu */}
      {selectedNode && (
        <div className="absolute top-4 right-4 glass p-5 rounded-xl shadow-lg w-72 animate-in slide-in-from-right-4 fade-in duration-200">
          <div className="flex justify-between items-start mb-4">
             <div>
                <h3 className="font-semibold text-primary leading-tight text-base">{selectedNode.name}</h3>
                <p className="text-[11px] uppercase tracking-wider text-text-muted font-medium mt-1">Type: {selectedNode.type}</p>
             </div>
             <button 
               onClick={() => setSelectedNode(null)}
               className="p-1 rounded bg-black/5 dark:bg-white/5 text-text-muted hover:text-primary transition-colors"
             >
                <X size={14} />
             </button>
          </div>

          <div className="space-y-3 pt-3 border-t border-border/50">
             <div className="flex justify-between text-xs">
                <span className="text-text-muted">Entity Score</span>
                <span className="font-mono text-secondary">{(selectedNode.weight * 100).toFixed(0)}</span>
             </div>
             <div className="flex justify-between text-xs">
                <span className="text-text-muted">Graph UID</span>
                <span className="font-mono text-text-muted opacity-50 truncate max-w-[120px]" title={selectedNode.id}>{selectedNode.id}</span>
             </div>
          </div>
          
          <button className="w-full mt-5 py-2 rounded-md bg-secondary text-surface text-xs font-semibold hover:bg-secondary/90 transition-colors shadow-sm">
             Explore Connections
          </button>
        </div>
      )}
    </div>
  )
}

export default KnowledgeGraphVisualiser
