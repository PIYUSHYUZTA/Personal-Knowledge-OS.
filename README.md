# Personal Knowledge OS (PKOS) + Project AURA

A unified, high-performance Personal Knowledge Operating System with semantic search, dual-persona AI, and 3D knowledge visualization.

## 🌟 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 20+ (for local development)
- PostgreSQL 16 (with pgvector extension)

### Running with Docker Compose

```bash
# Clone and navigate
cd "e:/Personal Knowledge Os"

# Create environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Start all services
docker-compose up -d

# Services will be available at:
# - Backend API: http://localhost:8000
# - Frontend: http://localhost:5173
# - PostgreSQL: localhost:5432
# - API Docs: http://localhost:8000/api/docs
```

### Local Development Setup

#### Backend
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env from example
cp .env.example .env

# Run database migrations (if using Alembic)
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Create .env from example
cp .env.example .env

# Start development server
npm run dev
```

## 📁 Project Structure

```
PKOS/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── main.py            # FastAPI entry point
│   │   ├── config.py          # Configuration management
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   ├── schemas.py         # Pydantic validation schemas
│   │   ├── core/              # Security, JWT, MPC
│   │   ├── routes/            # API endpoints
│   │   ├── services/          # Business logic
│   │   ├── database/          # Database setup
│   │   └── utils/             # Utilities
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example           # Environment template
│   └── Dockerfile             # Container build
│
├── frontend/                   # React/TypeScript frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/            # Page components
│   │   ├── context/          # React contexts
│   │   ├── services/         # API clients
│   │   ├── types/            # TypeScript types
│   │   ├── App.tsx           # Root component
│   │   └── main.tsx          # Entry point
│   ├── package.json          # NPM dependencies
│   ├── vite.config.ts        # Vite configuration
│   ├── tsconfig.json         # TypeScript config
│   ├── .env.example          # Environment template
│   └── Dockerfile            # Container build
│
├── docker-compose.yml         # Orchestration
├── .gitignore                # Git ignore patterns
└── README.md                 # This file
```

## 🏗️ Architecture

### Backend Stack
- **Framework**: FastAPI (async, high-performance)
- **Database**: PostgreSQL with pgvector
- **ORM**: SQLAlchemy
- **Search**: Semantic embeddings (sentence-transformers)
- **Authentication**: JWT + optional MPC
- **API**: RESTful with WebSocket support

### Frontend Stack
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: React Context + Zustand
- **Visualization**: Three.js (3D knowledge map)
- **HTTP Client**: Axios

### Database Schema
- **Users**: Authentication and profiles
- **Sessions**: User sessions with MPC handshakes
- **Knowledge Sources**: PDF, Text, Markdown files
- **Knowledge Chunks**: Semantic chunks with metadata
- **Knowledge Embeddings**: Vector embeddings (pgvector)
- **AURA State**: Persona and conversation state
- **Conversation History**: Chat history
- **Graph Entities/Relationships**: Knowledge graph (Neo4j optional)

## 🤖 Project AURA Features

### Dual-Persona Logic
1. **Advisor Mode**: Technical, precise, efficient responses
2. **Friend Mode**: Empathetic, conversational, supportive

Persona switches based on query intent/keywords automatically.

### RAG Pipeline
- Semantic chunking of ingested documents
- Vector embeddings with sentence-transformers
- Similarity-based retrieval
- Context-aware response generation

### 🧠 Autonomous Agentic Reasoning (Phase 6)
- **Multi-Step Reasoning**: 5-step pipeline (Analyze → Search → Verify → Synthesize → Finalize)
- **Hybrid Inference**: Intelligent routing between local models (Ollama/Mistral) and cloud providers (Claude/GPT-4o)
- **Skill Gap Mapper**: Real-time expertise tracking across 12 BCA domains with personalized study roadmaps
- **Federated P2P Sync**: Secure, cloudless synchronization between home server and mobile devices via encrypted tunnels

## 🔒 Security

- **JWT Authentication**: Token-based auth with refresh tokens
- **Password Hashing**: bcrypt with passlib
- **MPC Handshake**: Optional multi-party computation security
- **Federated Privacy**: Local-first data architecture ensures sensitive information never leaves your hardware

- **CORS Protection**: Configurable origins
- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy

## 📊 API Endpoints

### Authentication
- `POST /auth/register` - Create account
- `POST /auth/login` - Login
- `POST /auth/logout` - Logout
- `GET /auth/verify` - Verify token
- `POST /auth/refresh` - Refresh token

### Knowledge Management
- `POST /ingestion/upload` - Upload files
- `POST /knowledge/search` - Semantic search
- `GET /knowledge/sources` - List sources
- `GET /knowledge/graph` - Get knowledge graph

### AURA Chat
- `POST /aura/query` - Send query
- `GET /aura/history` - Get conversation history
- `GET /aura/state` - Get AURA state

### System
- `GET /health` - Health check
- `GET /status` - System status
- `GET /version` - API version

## 🚀 Deployment

### Production with Docker

```bash
# Build images
docker-compose build

# Run containers
docker-compose up -d

# View logs
docker-compose logs -f backend frontend

# Stop services
docker-compose down
```

### Environment Configuration

Edit `.env` files to configure:
- Database credentials
- Secret keys
- API URLs
- Feature flags
- Model parameters

## 📝 Development

### Code Quality
- Type hints (mypy)
- Linting (flake8, eslint)
- Formatting (black, prettier)
- Testing (pytest, jest)

Run checks:
```bash
# Backend
black backend/
flake8 backend/
mypy backend/
pytest backend/

# Frontend
npm run lint
npm run type-check
npm run build
```

## 🔄 CI/CD

GitHub Actions pipelines:
- `.github/workflows/ci-backend.yml` - Backend tests & build
- `.github/workflows/ci-frontend.yml` - Frontend tests & build
- `.github/workflows/security-scan.yml` - Security analysis

## 📚 Documentation

- **ARCHITECTURE.md** - System design details
- **API_CONTRACT.md** - API specifications
- **DATABASE_SCHEMA.md** - Database design
- **AURA_PERSONA_LOGIC.md** - AI persona implementation
- **DEPLOYMENT.md** - Production setup guide

## 🆘 Troubleshooting

### Database Connection Error
```bash
# Check PostgreSQL is running
docker-compose ps

# Verify DATABASE_URL in .env
cat backend/.env | grep DATABASE_URL
```

### Port Already in Use
```bash
# Change ports in docker-compose.yml or .env
BACKEND_PORT=8001
FRONTEND_PORT=5174
```

### Build Failures
```bash
# Clear containers and rebuild
docker-compose down -v
docker-compose build --no-cache
```

## 📄 License

MIT License - See LICENSE file for details

## 👥 Authors

- Piyush Nawani - Lead Architect

## 🔗 Links

- API Documentation: [Swagger UI](http://localhost:8000/api/docs)
- ReDoc: [ReDoc](http://localhost:8000/api/redoc)
- Frontend: [http://localhost:5173](http://localhost:5173)

---

**Status**: Beta (v1.6.0-sovereign)
**Last Updated**: 2026-04-24
# Personal-Knowledge-OS.
