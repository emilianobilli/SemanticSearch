# Semantic Search API

A powerful semantic search engine built with FastAPI and VictorDB, featuring multilingual support and vector-based document retrieval.

## Overview

This semantic search system allows you to:
- **Ingest documents** with metadata and automatically chunk them for optimal retrieval
- **Perform semantic searches** using natural language queries across multiple languages
- **Retrieve similar documents** based on meaning rather than just keyword matching
- **Manage documents** with full CRUD operations via REST API

The system uses state-of-the-art sentence transformers for embedding generation and VictorDB for efficient vector storage and retrieval.

## Features

- 🔍 **Semantic Search**: Advanced similarity search using sentence transformers
- 🌍 **Multilingual Support**: Built-in support for multiple languages
- 📄 **Document Management**: Full CRUD operations for documents
- 🚀 **High Performance**: Optimized chunking and vector indexing
- 🔧 **RESTful API**: Complete FastAPI-based REST interface
- ⚙️ **Configurable**: Environment-based configuration system
- 🐳 **Production Ready**: Built for scalability and reliability

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │ Sentence         │    │   VictorDB      │
│   REST API      │───▶│ Transformers     │───▶│   Vector Store  │
│                 │    │ (Embeddings)     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Document      │    │   Text           │    │   Vector        │
│   Storage       │    │   Chunking       │    │   Indexing      │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Requirements

- **Python**: 3.9+
- **VictorDB**: Running instance with table and index services
- **System Memory**: Minimum 2GB RAM (4GB+ recommended)
- **Storage**: Depends on document volume

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/emilianobilli/SemanticSearch
cd SemanticSearch
```

### 2. Create Virtual Environment

```bash
python3 -m venv env
source env/bin/activate  # On macOS/Linux
# or
env\Scripts\activate     # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements-api.txt
```

### 4. Set Up VictorDB

You need to have VictorDB running with both table and index services. Please refer to the [VictorDB documentation](https://github.com/victor-base/victordb) for installation and setup instructions.

Typical VictorDB setup:
```bash
# Start table service
victord table --socket /var/lib/victord/semantic_table/socket.unix

# Start index service  
victord index --socket /var/lib/victord/semantic_index/socket.unix
```

### 5. Configure Environment

Copy the example environment file and adjust the settings:

```bash
cp .env.example .env  # If you have an example file
# or create .env manually
```

Edit `.env` with your configuration:

```bash
# VictorDB Configuration
SEMANTIC_VICTOR_TABLE_SOCKET=/var/lib/victord/semantic_table/socket.unix
SEMANTIC_VICTOR_INDEX_SOCKET=/var/lib/victord/semantic_index/socket.unix

# API Configuration
SEMANTIC_API_HOST=0.0.0.0
SEMANTIC_API_PORT=8000
SEMANTIC_API_RELOAD=true
SEMANTIC_API_LOG_LEVEL=info

# CORS Configuration
SEMANTIC_CORS_ORIGINS=*

# Search Configuration
SEMANTIC_MAX_SEARCH_RESULTS=50
SEMANTIC_DEFAULT_SEARCH_RESULTS=10
```

## Usage

### Starting the API Server

```bash
python api.py
```

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

### API Endpoints

#### Health Check
```bash
GET /health
```

#### Ingest Single Document
```bash
POST /document
Content-Type: application/json

{
  "title": "Document Title",
  "author": "Author Name",
  "source": "https://example.com/article",
  "published_at": "2024-01-01",
  "raw_text": "Document content here...",
  "metadata": ["tag1", "tag2"]
}
```

#### Ingest Multiple Documents
```bash
POST /documents
Content-Type: application/json

[
  {
    "title": "Document 1",
    "raw_text": "Content 1...",
    ...
  },
  {
    "title": "Document 2", 
    "raw_text": "Content 2...",
    ...
  }
]
```

#### Search Documents
```bash
GET /search?q=your search query&top=10
```

#### Get Specific Document
```bash
GET /documents/{document_id}
```

#### Delete Document
```bash
DELETE /documents/{document_id}
```

### Python SDK Usage

```python
from search import SemanticSearch
from model import Document
from victordb import VictorTableClient, VictorIndexClient, VictorSession

# Initialize connections
table = VictorTableClient()
table.connect(unix_path="/path/to/table/socket.unix")

index = VictorIndexClient()
index.connect(unix_path="/path/to/index/socket.unix")

session = VictorSession(table)
semantic_search = SemanticSearch(session, index)

# Create and ingest a document
document = Document(
    title="My Document",
    author="Author Name", 
    raw_text="Document content here...",
    metadata=["tag1", "tag2"]
)

success = semantic_search.ingest(document=document)

# Search for documents
results = semantic_search.search(query="search query", top=10)

# Get specific document
doc = semantic_search.retrieve(document_id=1)

# Delete document
success = semantic_search.delete(document_id=1)
```

### Interactive Search (CLI)

For testing and exploration, you can use the interactive search script:

```bash
python feed.py
```

This will start an interactive session where you can type queries and see results immediately.

## Configuration

All configuration is handled through environment variables. Key settings include:

| Variable | Default | Description |
|----------|---------|-------------|
| `SEMANTIC_VICTOR_TABLE_SOCKET` | `/tmp/victor_default_table.sock` | VictorDB table service socket |
| `SEMANTIC_VICTOR_INDEX_SOCKET` | `/tmp/victor_default_index.sock` | VictorDB index service socket |
| `SEMANTIC_API_HOST` | `0.0.0.0` | API server host |
| `SEMANTIC_API_PORT` | `8000` | API server port |
| `SEMANTIC_MAX_SEARCH_RESULTS` | `50` | Maximum search results |
| `SEMANTIC_DEFAULT_SEARCH_RESULTS` | `10` | Default search results |

## Text Processing

### Chunking Strategy

The system uses intelligent text chunking optimized for semantic search:

- **Target Length**: ~256 tokens per chunk
- **Overlap**: 40 tokens between chunks
- **Model**: Designed for `paraphrase-multilingual-MiniLM-L12-v2`
- **Title Prepending**: Automatically prepends document title to chunks for better context

### Embedding Model

- **Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Dimensions**: 384
- **Languages**: Supports 50+ languages
- **Normalization**: L2 normalized embeddings for consistent similarity scoring

## Production Deployment

### Docker Deployment (Recommended)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements-api.txt .
RUN pip install -r requirements-api.txt

COPY . .
EXPOSE 8000

CMD ["python", "api.py"]
```

### Environment Variables for Production

```bash
SEMANTIC_API_RELOAD=false
SEMANTIC_API_LOG_LEVEL=warning
SEMANTIC_CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Scaling Considerations

- **VictorDB**: Can be scaled horizontally across multiple nodes
- **API**: Stateless design allows for easy horizontal scaling
- **Memory**: Embedding model requires ~1GB RAM per instance
- **Storage**: Vector index size depends on document volume

## Development

### Project Structure

```
SemanticSearch/
├── api.py              # FastAPI application and endpoints
├── search.py           # Core semantic search logic
├── model.py            # Data models (Document, DocumentChunk)
├── embed.py            # Text embedding and chunking
├── settings.py         # Configuration management
├── feed.py             # Interactive CLI and utilities
├── requirements-api.txt # Python dependencies
├── .env                # Environment configuration
└── README.md           # This file
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Code Style

```bash
# Install development dependencies
pip install black isort flake8

# Format code
black .
isort .

# Check style
flake8 .
```

## Troubleshooting

### Common Issues

1. **VictorDB Connection Failed**
   - Ensure VictorDB services are running
   - Check socket paths in configuration
   - Verify file permissions

2. **Out of Memory**
   - Reduce chunk size or batch size
   - Consider using a smaller embedding model
   - Monitor memory usage during ingestion

3. **Slow Search Performance**
   - Check VictorDB index configuration
   - Consider reducing search result limits
   - Monitor vector index size

4. **Import Errors**
   - Ensure all dependencies are installed
   - Check Python version compatibility
   - Verify virtual environment activation

### Logs

The application logs important events. To see detailed logs:

```bash
SEMANTIC_API_LOG_LEVEL=debug python api.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review VictorDB documentation for database-related issues

---

Built with ❤️ using FastAPI, VictorDB, and Sentence Transformers.
