# Personal Knowledge OS - 7-Day Overhaul Plan

## Executive Summary
Transform the PKOS from a polished prototype into a fully functional, production-ready Personal Knowledge Operating System with cinematic visuals, complete audio feedback, and a working FastAPI backend that powers real AI capabilities.

---

## Day 1-2: Visual & Sensory Polish

### Day 1 Morning: Background Enhancement
- [ ] **Digital Void Background Overhaul**
  - Add depth layers: distant starfield (large), mid-ground stars (medium), foreground particles (small)
  - Implement procedural nebula with color gradients (deep purple, crimson, teal)
  - Add a distant grid plane with perspective fade
  - Add subtle animated particles/streaks for cinematic feel
  - Ensure proper performance with instancing

### Day 1 Afternoon: Sound System
- [ ] **Create useSound hook** (`/frontend/src/hooks/useSound.ts`)
  - Button click sound (mechanical/tactile)
  - Window open sound (digital hum/woosh)
  - Window close sound (reverse woosh)
  - FaceID scan sounds (scanning pulse, verification chime)
  - File upload complete sound
  - Error/alert sounds

- [ ] **Create sound files** (Web Audio API synthesized)
  - No external files needed - synthesize all sounds
  - Low-latency audio generation

### Day 1 Evening: Animation Polish
- [ ] **Fix Anti-Gravity Window System**
  - Verify smooth sway animation (gentle 2-5px drift, 6-10s period)
  - Ensure drag behavior is smooth with no jitter/snap
  - Add rotation tilt during drag (subtle 1-3 degrees)
  - Add spring-back animation on drop

---

## Day 3-4: FastAPI Backend Architecture

### Day 3 Morning: Core Backend Setup
- [ ] **Verify/Setup FastAPI main.py**
  - Add CORS for frontend
  - Add authentication middleware
  - Setup static file serving if needed

- [ ] **Create API Endpoints:**
  - `POST /knowledge/upload` - File upload with processing
  - `GET /knowledge/sources` - List uploaded documents
  - `GET /knowledge/graph` - Get knowledge graph data

### Day 3 Afternoon: AURA Chat Backend
- [ ] **Create AURA service endpoints:**
  - `POST /aura/query` - Process chat messages with RAG
  - `GET /aura/history` - Get conversation history
  - `GET /aura/state` - Get AURA system state

- [ ] **LLM Integration:**
  - Use OpenAI API or local model
  - Implement RAG (Retrieval Augmented Generation)
  - Create context window from uploaded documents

### Day 4 Morning: Knowledge Graph Backend
- [ ] **Graph Service:**
  - Create nodes from uploaded documents
  - Extract entities and relationships
  - Store in backend database
  - Provide graph data for frontend visualization

---

## Day 5-7: Full Integration & Testing

### Day 5: Component Integration
- [ ] **FileUploader → Backend:**
  - Connect to real upload endpoint
  - Show actual processing status
  - Handle errors gracefully

- [ ] **AuraChat → Backend:**
  - Connect to real AURA endpoint
  - Handle streaming responses
  - Display sources and citations

- [ ] **Knowledge Visualizer → Backend:**
  - Connect to graph endpoint
  - Render real nodes and edges
  - Handle empty states

### Day 6: Aura Bridge Implementation
- [ ] **Cross-component Communication:**
  - File upload → AURA acknowledgment
  - AURA → Knowledge Graph new nodes
  - Real-time updates across all components

### Day 7: Final Polish & Deployment
- [ ] **Testing & Bug Fixes:**
  - Test all features end-to-end
  - Fix any UI/UX issues
  - Ensure mobile responsiveness

- [ ] **Build & Deploy:**
  - Build frontend for production
  - Deploy to accessible URL
  - Verify everything works

---

## Technical Architecture

### Frontend Structure
```
/src
  /components
    /auth          - AuthBackground (cinematic background)
    /desktop       - Window, WindowManager (anti-gravity system)
    /dashboard     - Dashboard (main OS interface)
    /aura          - AuraChat (AI chat interface)
    /ingestion     - FileUploader (file processing)
    /knowledge     - KnowledgeVisualizer (3D graph)
    /ui            - Toast, CommandPalette, Badge
  /context
    AuthContext    - Authentication state
    AuraContext    - AI chat state
    KnowledgeContext - Knowledge graph state
  /hooks
    useSound.ts    - Audio feedback system
    useApiToasts.ts - API toast notifications
  /services
    api.ts         - Backend API integration
  /store
    useDesktopStore.ts - Window management, file bridge
```

### Backend Structure
```
/backend/app
  /routes
    auth.py        - Authentication endpoints
    aura.py        - AURA chat endpoints
    knowledge.py   - Knowledge management
    health.py      - Health checks
  /services
    aura_service.py - AI processing logic
    knowledge_service.py - Document processing
    graph_service.py - Knowledge graph management
  main.py          - FastAPI application
```

---

## Success Criteria
1. ✅ Login with FaceID animation works with sound effects
2. ✅ Desktop background is cinematic (stars, nebulae, grid)
3. ✅ All windows have smooth anti-gravity animation
4. ✅ UI sounds play for all interactions
5. ✅ File uploads go to backend and are processed
6. ✅ AURA Chat connects to backend and provides real responses
7. ✅ Knowledge Graph shows real data from backend
8. ✅ File upload triggers updates in AURA and Knowledge Graph
9. ✅ No black screens or broken features
10. ✅ Professional, polished appearance

---

## Notes
- Use Web Audio API for synthesized sounds (no external files)
- Use Framer Motion for all animations
- All backend endpoints return proper JSON responses
- Handle offline/fallback mode for demo purposes