/**
 * Core TypeScript interfaces for PKOS Frontend
 */

export type UUID = string

export interface User {
  id: UUID
  email: string
  username: string
  full_name?: string
  profile_picture?: string
  is_active: boolean
  created_at: string
}

export interface AuthTokens {
  access_token: string
  refresh_token?: string
  token_type: string
  expires_in: number
}

export interface SearchResult {
  chunk_id: UUID
  source_id: UUID
  file_name: string
  chunk_text: string
  similarity_score: number
  metadata?: Record<string, any>
}

export interface KnowledgeSource {
  id: UUID
  file_name: string
  source_type: 'pdf' | 'text' | 'markdown' | 'document' | 'web' | 'code'
  file_size?: number
  chunks_count: number
  metadata?: Record<string, any>
  created_at: string
}

export interface AuraMessage {
  id: UUID
  user_message: string
  aura_response: string
  persona_used: 'advisor' | 'friend'
  retrieved_knowledge: SearchResult[]
  confidence_score: number
  created_at: string
}

export interface AuraState {
  id: UUID
  current_persona: 'advisor' | 'friend'
  context_window: number
  latest_message?: AuraMessage
}

export interface GraphEntity {
  id: UUID
  entity_name: string
  entity_type: string
  weight?: number          // Cumulative interaction-hit score (Phase 3.5 heatmap)
  last_accessed_at?: string
  metadata?: Record<string, any>
}

export interface GraphRelationship {
  id: UUID
  source_entity: GraphEntity
  target_entity: GraphEntity
  relationship_type: string
  weight: number
}

export interface GraphData {
  entities: GraphEntity[]
  relationships: GraphRelationship[]
}

export interface APIError {
  error: string
  error_code: string
  details?: Record<string, any>
  timestamp: string
}
