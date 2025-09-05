# Taxonomic Lineage Viewer

A Flask web application for exploring and comparing taxonomic lineages using the complete NCBI taxonomy database (2.7M species) in Neo4j graph database.

## Features

- 🌳 **Complete NCBI Taxonomy**: Browse all 2.7 million species relationships
- 🔍 **Fast Species Search**: Find species by scientific or common name
- ⚖️ **Lineage Comparison**: Compare evolutionary paths between any two species
- 🚀 **Auto-Setup**: Automatically downloads and imports NCBI data when database is empty
- 📊 **Import Status Tracking**: Real-time progress monitoring for data import
- 🔗 **API Endpoints**: RESTful API for programmatic access
- 📖 **Wikipedia Integration**: Click any taxonomic name to open its Wikipedia page

---

## 🚂 Railway Deployment

Visit the live application: [Taxonomic Lineage Viewer](https://taxonomic-lineage-viewer-production.up.railway.app/)

### Deploy your own

1. **Fork this repository** to your GitHub account
2. **Create Railway project**: Connect your GitHub repo to Railway
3. **Add Neo4j service**: In Railway dashboard, add a [Neo4j template service](https://railway.com/deploy/ZVljtU)
4. **Deploy your app from Github**: Railway auto-detects the Dockerfile and deploys your Flask app
5. **Environment variables**: Set the variables as described below
6. **Auto-import**: The app automatically detects empty database and starts NCBI data import

**That's it!** The app will automatically download and import the complete NCBI taxonomy database on first launch.

#### Railway Environment Variables
in neo4j
- `NEO4J_AUTH` - Credentials in format `neo4j/{YOUR_PASSWORD}`
in app
- `NEO4J_URI` - Internal Neo4j connection, must be set to `bolt://${{neo4j.RAILWAY_PRIVATE_DOMAIN}}:7687
- `NEO4J_PASSWORD` - Password as set in neo4j in format `{YOUR_PASSWORD}`

---

## 💻 Local Development

### Homebrew (macOS/Linux)

```bash
# Install Neo4j
brew install neo4j

# Start Neo4j
brew services start neo4j

# Wait for Neo4j to start (about 30 seconds)
# Set initial password at http://localhost:7474 to neotaxonomy (or your-password)

# Clone and setup project
git clone https://github.com/davhel/taxonomic-lineage-viewer.git
cd taxonomic-lineage-viewer

# Install Python dependencies
uv sync

# Set environment variables (optional - uses defaults)
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"

# Run Flask app
uv run python app.py

# Access app (auto-import will start on first launch)
open http://localhost:5001
```

**Requirements:**
- Python 3.11+
- [Homebrew](https://brew.sh/)
- [uv](https://astral.sh/docs/uv)
- 8GB+ RAM (for data loading)
- Stable internet connection (50MB NCBI download)

### Docker

```bash
git clone https://github.com/davhel/taxonomic-lineage-viewer.git
cd taxonomic-lineage-viewer
cp .env.example .env

# Start services
docker compose up -d

# The app will automatically detect empty database and start import
# Or manually trigger import:
# docker compose run --rm ingest

# Access app
open http://localhost:5001
```

### Requirements
- Docker and Docker Compose
- 8GB+ RAM (for data loading)
- Stable internet connection (50MB NCBI download)

---

## 🔧 API Reference

### Main Endpoints
- `GET /api/search?q=homo` - Search species by name
- `GET /api/lineage/9606` - Get complete lineage for species (human)
- `GET /api/compare/9606/9544` - Compare two species (human vs monkey)
- `GET /api/compare/9606` - Compare species with human (default)
- `GET /api/sample` - Get sample species for exploration

### Status & Info Endpoints
- `GET /api/import/status` - Check import progress and database status
- `POST /api/import/start` - Manually trigger database import
- `GET /api/database/info` - Get database statistics

### Response Format
```json
{
  "species": [
    {
      "taxid": 9606,
      "scientific_name": "Homo sapiens",
      "common_name": "human",
      "display_name": "human"
    }
  ]
}
```

---

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Flask App     │────│   Neo4j DB      │
│   (Python)      │    │   (2.7M nodes)  │
│   Port 5001     │    │   Port 7687     │
└─────────────────┘    └─────────────────┘
```

### Key Components
- **Flask Web App**: Serves API and web interface
- **Neo4j Database**: Graph database storing taxonomic relationships
- **Auto-Setup System**: Automatically imports NCBI data when database is empty
- **Wikipedia Integration**: Click any taxonomic name in lineages to view Wikipedia pages
  - Special case: Root node (taxid 1) links to [LUCA](https://en.wikipedia.org/wiki/Last_universal_common_ancestor)

## 📁 Project Structure

```
├── app.py              # Flask web app with auto-setup integration
├── models.py           # Neo4j database interface
├── setup.py           # NCBI taxonomy importer with status tracking
├── docker-compose.yml  # Local development services
├── Dockerfile         # App container for Railway deployment
├── railway.toml       # Railway deployment configuration
├── LICENSE            # MIT license
├── templates/         # Web interface with GitHub integration
│   └── index.html     # Main UI with credit attribution
└── static/           # Assets (D3.js visualizations)
```

---

## 🚀 Auto-Setup Features

The application includes an intelligent auto-setup system:

- **Database Detection**: Automatically checks if Neo4j database is empty on startup
- **Background Import**: Downloads and imports NCBI taxonomy data in background thread
- **Progress Tracking**: Real-time status updates via `/api/import/status` endpoint
- **Error Handling**: Graceful error recovery and status reporting
- **Service Coordination**: Handles connection retries and service dependencies

### Import Process
1. **Download**: Fetches latest NCBI taxonomy dump (~50MB)
2. **Parse**: Processes nodes.dmp and names.dmp files
3. **Import**: Bulk loads 2.7M nodes and relationships into Neo4j
4. **Verify**: Validates data integrity and sample queries
5. **Ready**: Application becomes fully functional

---

## 🛠️ Troubleshooting

**"Database not available"**: 
- Services starting up, wait 2-3 minutes
- Check `docker compose logs` for details

**"Database import in progress"**: 
- Auto-import is running, check `/api/import/status`
- Import takes 15-30 minutes depending on connection

**Railway deployment issues**: 
- Verify Neo4j service is active in Railway dashboard
- Check environment variables are properly set
- Monitor app logs for connection details

**Local development issues**:
- Ensure Docker has sufficient memory (8GB+ recommended)
- Check firewall settings for Neo4j ports
- Verify `.env` file configuration

**Homebrew setup issues**:
- **Neo4j won't start**: Try `brew services restart neo4j` or check logs with `brew services list`
- **Password issues**: Reset Neo4j password at http://localhost:7474 (default: neo4j/neo4j)

---

## 📊 Data Source

This project uses the complete [NCBI Taxonomy Database](https://www.ncbi.nlm.nih.gov/taxonomy), which includes:
- **2.7 million taxonomic nodes**
- **Complete hierarchical relationships** from species to root
- **Scientific and common names**
- **Updated regularly** from NCBI FTP
- **Automatic import** on first application launch

The data is automatically downloaded from NCBI's FTP server and imported into Neo4j on first run, ensuring you always have the latest taxonomy data.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Test locally with `docker compose up`
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📄 License

MIT License - Free to use and modify. See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **NCBI Taxonomy Database** - Primary data source
- **Neo4j** - Graph database platform
- **D3.js** - Data visualization library
- **GitHub Copilot & Claude Sonnet 4** - AI development assistance

---

Built with ❤️ by [Davide Heller](https://github.com/davhel)
