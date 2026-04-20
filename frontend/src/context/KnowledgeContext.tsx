import React, { createContext, useContext, useState, ReactNode } from 'react'
import { KnowledgeSource, SearchResult, GraphData } from '@/types'
import { knowledgeAPI } from '@/services/api'

interface KnowledgeContextType {
  sources: KnowledgeSource[]
  searchResults: SearchResult[]
  graphData: GraphData | null
  isSearching: boolean
  isLoading: boolean
  error: string | null
  search: (query: string, top_k?: number) => Promise<void>
  uploadFile: (file: File, sourceType?: string) => Promise<void>
  getSources: () => Promise<void>
  getGraph: () => Promise<void>
  clearResults: () => void
  clearError: () => void
}

const KnowledgeContext = createContext<KnowledgeContextType | undefined>(undefined)

export const KnowledgeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [sources, setSources] = useState<KnowledgeSource[]>([])
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const search = async (query: string, top_k: number = 5) => {
    setIsSearching(true)
    setError(null)
    try {
      const response = await knowledgeAPI.search(query, top_k)
      setSearchResults(response.results || [])
    } catch (err: any) {
      setError('Search failed')
      console.error('Search error:', err)
    } finally {
      setIsSearching(false)
    }
  }

  const uploadFile = async (file: File, sourceType: string = 'pdf') => {
    setIsLoading(true)
    setError(null)
    try {
      await knowledgeAPI.upload(file, sourceType)
      // Refresh sources after upload
      await getSources()
    } catch (err: any) {
      setError('Upload failed')
      console.error('Upload error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getSources = async () => {
    setIsLoading(true)
    try {
      const response = await knowledgeAPI.getSources()
      setSources(Array.isArray(response) ? response : response.sources || [])
    } catch (err: any) {
      setError('Failed to fetch sources')
      console.error('Get sources error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getGraph = async () => {
    setIsLoading(true)
    try {
      const response = await knowledgeAPI.getGraph()
      setGraphData(response)
    } catch (err: any) {
      setError('Failed to fetch graph')
      console.error('Get graph error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const clearResults = () => setSearchResults([])
  const clearError = () => setError(null)

  return (
    <KnowledgeContext.Provider
      value={{
        sources,
        searchResults,
        graphData,
        isSearching,
        isLoading,
        error,
        search,
        uploadFile,
        getSources,
        getGraph,
        clearResults,
        clearError,
      }}
    >
      {children}
    </KnowledgeContext.Provider>
  )
}

export const useKnowledge = () => {
  const context = useContext(KnowledgeContext)
  if (!context) {
    throw new Error('useKnowledge must be used within KnowledgeProvider')
  }
  return context
}
