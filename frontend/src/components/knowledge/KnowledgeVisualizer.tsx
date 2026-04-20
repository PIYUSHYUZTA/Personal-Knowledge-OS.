import React from 'react'
import { useKnowledge } from '@/context/KnowledgeContext'
import Graph3D from './Graph3D'
import Skeleton from '@/components/ui/Skeleton'

export default function KnowledgeVisualizer() {
  const { getGraph, isLoading } = useKnowledge()

  React.useEffect(() => {
    getGraph()
  }, [])

  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 gap-4">
        <div className="w-full max-w-md space-y-4">
          <Skeleton variant="text" lines={1} width="60%" height="20px" />
          <Skeleton variant="text" lines={2} />
          <div className="grid grid-cols-3 gap-3 mt-6">
            <Skeleton variant="stat-card" className="h-24" />
            <Skeleton variant="stat-card" className="h-24" />
            <Skeleton variant="stat-card" className="h-24" />
          </div>
        </div>
        <p className="text-xs font-medium text-text-muted mt-4 uppercase tracking-wider">
          Loading knowledge graph...
        </p>
      </div>
    )
  }

  return (
    <div className="w-full h-full bg-background/50 rounded-xl overflow-hidden">
      <Graph3D />
    </div>
  )
}
