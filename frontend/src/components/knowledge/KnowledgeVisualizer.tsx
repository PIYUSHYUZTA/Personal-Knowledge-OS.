import React from 'react'
import { useKnowledge } from '@/context/KnowledgeContext'
import Graph3D from './Graph3D'

export default function KnowledgeVisualizer() {
  const { getGraph, isLoading } = useKnowledge()

  React.useEffect(() => {
    getGraph()
  }, [])

  if (isLoading) {
    return <div className="h-full flex items-center justify-center text-sm font-medium text-muted">Loading knowledge map...</div>
  }

  return (
    <div className="w-full h-full bg-slate-950/50 rounded-xl overflow-hidden backdrop-blur-3xl animate-in fade-in duration-500">
      <Graph3D />
    </div>
  )
}
