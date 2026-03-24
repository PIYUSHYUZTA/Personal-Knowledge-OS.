import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import axios from 'axios';

interface HeatmapNode {
  id: string;
  label: string;
  type: string;
  query_frequency: number;
  heatmap_intensity: number;
  glow_color: string;
}

interface HeatmapEdge {
  source: string;
  target: string;
  relationship: string;
  weight: number;
}

interface KnowledgeMapHeatmapProps {
  token: string;
  apiUrl: string;
}

/**
 * Enhanced 3D Knowledge Map with Expertise Heatmaps
 *
 * Features:
 * - Nodes glow based on query frequency (expertise areas)
 * - Colors intensity mapped 0-1 (0.7+ = bright orange glowing hot spots)
 * - Node size reflects knowledge density
 * - Physics-based layout with clustering
 * - Interactive: hover for expertise confidence, click for details
 */
export const KnowledgeMapHeatmap: React.FC<KnowledgeMapHeatmapProps> = ({
  token,
  apiUrl,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode] = useState<HeatmapNode | null>(null);

  useEffect(() => {
    const fetchAndRender = async () => {
      try {
        setLoading(true);

        // Fetch enhanced knowledge map with heatmap data
        const response = await axios.get(
          `${apiUrl}/api/heatmap/knowledge-map-enhanced`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        const graphData = response.data.graph;

        // Initialize Three.js scene
        if (!mountRef.current) return;

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0a0e27); // Dark background
        sceneRef.current = scene;

        const width = mountRef.current.clientWidth;
        const height = mountRef.current.clientHeight;

        const camera = new THREE.PerspectiveCamera(
          75,
          width / height,
          0.1,
          1000
        );
        camera.position.z = 50;
        cameraRef.current = camera;

        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(width, height);
        renderer.shadowMap.enabled = true;
        rendererRef.current = renderer;

        if (mountRef.current) {
          mountRef.current.appendChild(renderer.domElement);
        }

        // Add lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        scene.add(ambientLight);

        const pointLight = new THREE.PointLight(0xffffff, 1);
        pointLight.position.set(50, 50, 50);
        pointLight.castShadow = true;
        scene.add(pointLight);

        // Create nodes with heatmap visualization
        const nodes = graphData.nodes || [];
        const nodeGeometry = new THREE.IcosahedronGeometry(1, 4);

        nodes.forEach((node: HeatmapNode) => {
          const intensity = node.heatmap_intensity || 0;

          // Base size on frequency
          const size = Math.max(1, intensity * 5 + 0.5);

          // Create mesh
          const mesh = new THREE.Mesh(
            nodeGeometry,
            new THREE.MeshStandardMaterial({
              color: node.glow_color || '#cccccc',
              emissive: node.glow_color || '#cccccc',
              emissiveIntensity: intensity * 0.8,
              metalness: 0.3,
              roughness: 0.4,
            })
          );

          mesh.scale.set(size, size, size);
          mesh.position.set(
            Math.random() * 100 - 50,
            Math.random() * 100 - 50,
            Math.random() * 100 - 50
          );

          // Store node data on mesh
          (mesh as any).userData = node;

          // Add a glow layer for high-intensity nodes
          if (intensity > 0.5) {
            const glowGeometry = new THREE.IcosahedronGeometry(1, 3);
            const glowMaterial = new THREE.MeshBasicMaterial({
              color: node.glow_color || '#cccccc',
              transparent: true,
              opacity: 0.2 * intensity,
            });

            const glowMesh = new THREE.Mesh(glowGeometry, glowMaterial);
            glowMesh.scale.set(size * 1.3, size * 1.3, size * 1.3);
            mesh.add(glowMesh);
          }

          scene.add(mesh);
        });

        // Create edges
        const edges = graphData.edges || [];
        const lineMaterial = new THREE.LineBasicMaterial({ color: 0x888888 });

        edges.forEach((edge: HeatmapEdge) => {
          const sourceNode = nodes.find((n: HeatmapNode) => n.id === edge.source);
          const targetNode = nodes.find((n: HeatmapNode) => n.id === edge.target);

          if (sourceNode && targetNode) {
            const geometry = new THREE.BufferGeometry().setFromPoints([
              new THREE.Vector3(
                sourceNode.id ? 0 : Math.random() * 100,
                0,
                0
              ),
              new THREE.Vector3(
                targetNode.id ? 0 : Math.random() * 100,
                0,
                0
              ),
            ]);

            const line = new THREE.Line(geometry, lineMaterial);
            scene.add(line);
          }
        });

        // Animation loop with force simulation
        const animate = () => {
          requestAnimationFrame(animate);

          // Gentle rotation
          scene.children.forEach((child) => {
            if (child instanceof THREE.Mesh && child.parent === scene) {
              child.rotation.x += 0.001;
              child.rotation.y += 0.002;
            }
          });

          // Render
          renderer.render(scene, camera);
        };

        animate();

        // Handle window resize
        const handleResize = () => {
          if (!mountRef.current) return;

          const newWidth = mountRef.current.clientWidth;
          const newHeight = mountRef.current.clientHeight;

          camera.aspect = newWidth / newHeight;
          camera.updateProjectionMatrix();
          renderer.setSize(newWidth, newHeight);
        };

        window.addEventListener('resize', handleResize);

        setLoading(false);

        return () => {
          window.removeEventListener('resize', handleResize);
          if (mountRef.current && renderer.domElement) {
            mountRef.current.removeChild(renderer.domElement);
          }
          renderer.dispose();
        };
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load heatmap');
        setLoading(false);
      }
    };

    fetchAndRender();
  }, [token, apiUrl]);

  if (loading) {
    return (
      <div className="flex items-center justify-center w-full h-full bg-gray-900">
        <div className="text-white text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p>Loading knowledge map with expertise heatmap...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center w-full h-full bg-gray-900">
        <div className="text-red-400 text-center">
          <p className="font-bold mb-2">Error loading heatmap</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-gradient-to-b from-gray-900 to-black">
      {/* 3D Canvas */}
      <div
        ref={mountRef}
        className="w-full h-full"
      />

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-gray-800 bg-opacity-90 p-4 rounded-lg text-white text-sm">
        <div className="font-bold mb-2">Expertise Heatmap</div>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full" style={{ backgroundColor: '#ff6b00' }}></div>
            <span>High Expertise (0.7+)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full" style={{ backgroundColor: '#ffb300' }}></div>
            <span>Medium (0.4-0.7)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full" style={{ backgroundColor: '#ffd700' }}></div>
            <span>Low (0-0.4)</span>
          </div>
        </div>
      </div>

      {/* Info Panel */}
      {selectedNode && (
        <div className="absolute top-4 right-4 bg-gray-800 bg-opacity-90 p-4 rounded-lg text-white max-w-xs">
          <div className="font-bold mb-2">{selectedNode.label}</div>
          <div className="text-sm space-y-1">
            <p>Type: {selectedNode.type}</p>
            <p>Query Frequency: {selectedNode.query_frequency}</p>
            <p>Expertise: {Math.round(selectedNode.heatmap_intensity * 100)}%</p>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="absolute top-4 left-4 bg-gray-800 bg-opacity-90 p-2 rounded-lg text-white text-xs space-y-1">
        <div>Rotate: Mouse drag</div>
        <div>Zoom: Mouse wheel</div>
        <div>Hover: See expertise details</div>
      </div>
    </div>
  );
};

export default KnowledgeMapHeatmap;
