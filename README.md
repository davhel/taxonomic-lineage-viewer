# Taxonomic Lineage Viewer

A Flask web application for exploring and comparing taxonomic lineages using the complete NCBI taxonomy database (2.7M species) in Neo4j graph database.

## Features

- 🌳 **Complete NCBI Taxonomy**: Browse all 2.7 million species relationships
- 🔍 **Fast Species Search**: Find species by scientific or common name
- ⚖️ **Lineage Comparison**: Compare evolutionary paths between any two species
- 🌐 **Interactive Web Interface**: Clean, responsive D3.js visualizations

---

## 🚂 Railway Deployment (Recommended)

### Railway Setup

1. **Fork this repository** to your GitHub account
2. **Create Railway project**: Connect your GitHub repo to Railway
3. **Railway auto-detects Docker Compose**: Both Flask app and Neo4j services will be created automatically
4. **Set environment variables**: Railway will prompt for `NEO4J_PASSWORD` - set your secure password
5. **Deploy**: Railway deploys both services from your docker-compose.yml
6. **Load data**: Once deployed, use the app service terminal to run `python setup.py`

**That's it!** Your docker-compose.yml handles everything - Railway creates both the Flask app and Neo4j database services automatically.

---

## 💻 Local Development

### Quick Start

```bash
git clone https://github.com/your-username/tol-d3.git
cd tol-d3
cp .env.example .env

# Start services
docker compose up -d

# Load taxonomy data (first time only, 20-30 minutes)
docker compose run --rm ingest

# Access app
open http://localhost:5001
```

### Requirements
- Docker and Docker Compose
- 8GB+ RAM (for data loading)

---

## 🔧 API Reference

- `GET /api/search?q=homo` - Search species
- `GET /api/lineage/9606` - Get human lineage  
- `GET /api/compare/9606/9544` - Compare human vs monkey
- `GET /api/sample` - Get sample species

---

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Flask App     │────│   Neo4j DB      │
│   (Python)      │    │   (2.7M nodes)  │
│   Port 5001     │    │   Port 7687     │
└─────────────────┘    └─────────────────┘
```

## 📁 Project Structure

```
├── app.py              # Flask web app
├── models.py           # Neo4j database interface
├── setup.py           # NCBI taxonomy importer
├── docker-compose.yml  # Local development
├── Dockerfile         # App container
├── templates/         # Web interface
└── static/           # Assets (D3.js)
```

---

## 🛠️ Troubleshooting

**"Database not available"**: Services starting up, wait 2-3 minutes

**Data loading fails**: Ensure 8GB+ RAM, stable internet connection

**Railway deployment issues**: Check both services are "Active", verify environment variables match

---

## 📊 Data Source

This project uses the complete [NCBI Taxonomy Database](https://www.ncbi.nlm.nih.gov/taxonomy), which includes:
- **2.7 million taxonomic nodes**
- **Complete hierarchical relationships** from species to root
- **Scientific and common names**
- **Updated regularly** from NCBI FTP

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Test locally with `docker compose up`
4. Submit a pull request

## 📄 License

MIT License - Free to use and modify
