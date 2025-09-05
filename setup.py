#!/usr/bin/env python3
"""
Complete NCBI Taxonomy to Neo4j Migration
Downloads the full NCBI taxonomy dump and loads it directly into Neo4j graph database
This ensures we have complete taxonomic relationships without missing links.
"""
import os
import sys
import tarfile
import requests
import tempfile
import shutil
from typing import Dict, List, Optional
from neo4j import GraphDatabase

class NCBIToNeo4jMigrator:
    def __init__(self):
        self.ncbi_ftp_url = "https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz"
        self.temp_dir = tempfile.mkdtemp()
        
        # Railway Neo4j connection handling
        neo4j_uri = None
        if os.getenv("RAILWAY_PRIVATE_DOMAIN"):
            # Use private domain for internal communication
            neo4j_uri = f"bolt://{os.getenv('RAILWAY_PRIVATE_DOMAIN')}:7687"
        elif os.getenv("RAILWAY_TCP_PROXY_DOMAIN") and os.getenv("RAILWAY_TCP_PROXY_PORT"):
            # Use TCP proxy for external access
            neo4j_uri = f"bolt://{os.getenv('RAILWAY_TCP_PROXY_DOMAIN')}:{os.getenv('RAILWAY_TCP_PROXY_PORT')}"
        else:
            # Standard environment variables or local fallback
            neo4j_uri = os.getenv('NEO4J_URI') or os.getenv('NEO4J_URL') or 'bolt://localhost:7687'
        
        neo4j_user = os.getenv('NEO4J_USERNAME') or os.getenv('NEO4J_USER') or 'neo4j'
        neo4j_password = os.getenv('NEO4J_PASSWORD') or 'neotaxonomy'
        
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        print(f"Connected to Neo4j at {neo4j_uri}")
        
    def download_ncbi_taxonomy(self) -> str:
        """Download NCBI taxonomy dump files"""
        print("Downloading NCBI taxonomy database...")
        print("This may take a few minutes (file is ~50MB)")
        
        response = requests.get(self.ncbi_ftp_url, stream=True)
        response.raise_for_status()
        
        tar_path = os.path.join(self.temp_dir, "taxdump.tar.gz")
        
        # Download with progress indication
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(tar_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\rProgress: {percent:.1f}%", end="", flush=True)
        
        print("\nDownload complete. Extracting...")
        
        # Extract the tar file
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(self.temp_dir)
        
        return self.temp_dir
    
    def parse_nodes_file(self, nodes_path: str) -> Dict[int, Dict]:
        """Parse the nodes.dmp file to get taxonomy hierarchy"""
        print("Parsing taxonomy nodes...")
        
        nodes = {}
        with open(nodes_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                if line_num % 100000 == 0:
                    print(f"\rProcessed {line_num:,} nodes", end="", flush=True)
                
                # NCBI format: taxid | parent_taxid | rank | ... (separated by \t|\t)
                line = line.strip()
                if line.endswith('\t|'):
                    line = line[:-2]  # Remove trailing \t|
                
                parts = line.split('\t|\t')
                if len(parts) >= 3:
                    try:
                        taxid = int(parts[0].strip())
                        parent_taxid = int(parts[1].strip())
                        rank = parts[2].strip()
                        
                        nodes[taxid] = {
                            'parent_taxid': parent_taxid if parent_taxid != taxid else None,
                            'rank': rank
                        }
                    except ValueError:
                        continue  # Skip malformed lines
        
        print(f"\nParsed {len(nodes):,} taxonomy nodes")
        return nodes
    
    def parse_names_file(self, names_path: str) -> Dict[int, Dict]:
        """Parse the names.dmp file to get scientific and common names"""
        print("Parsing taxonomy names...")
        
        names = {}
        with open(names_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                if line_num % 100000 == 0:
                    print(f"\rProcessed {line_num:,} names", end="", flush=True)
                
                # NCBI format: taxid | name | unique_name | name_class | (separated by \t|\t)
                line = line.strip()
                if line.endswith('\t|'):
                    line = line[:-2]  # Remove trailing \t|
                
                parts = line.split('\t|\t')
                if len(parts) >= 4:
                    try:
                        taxid = int(parts[0].strip())
                        name = parts[1].strip()
                        name_class = parts[3].strip()
                        
                        if taxid not in names:
                            names[taxid] = {}
                        
                        if name_class == "scientific name":
                            names[taxid]['scientific_name'] = name
                        elif name_class == "common name":
                            # Only store the first common name we encounter
                            if 'common_name' not in names[taxid]:
                                names[taxid]['common_name'] = name
                    except ValueError:
                        continue  # Skip malformed lines
        
        print(f"\nParsed names for {len(names):,} taxa")
        return names
    
    def clear_existing_data(self):
        """Clear existing data from Neo4j database"""
        print("Clearing existing Neo4j data...")
        
        with self.driver.session() as session:
            # Delete all relationships first
            session.run("MATCH ()-[r:PARENT_OF]->() DELETE r")
            
            # Delete all nodes
            session.run("MATCH (n:Taxon) DELETE n")
            
            # Drop any indexes (if they exist)
            try:
                session.run("DROP INDEX taxon_taxid_index IF EXISTS")
            except:
                pass
                
        print("Existing data cleared.")
    
    def create_indexes(self):
        """Create indexes for better performance"""
        print("Creating database indexes...")
        
        with self.driver.session() as session:
            # Create index on taxid for fast lookups
            session.run("CREATE INDEX taxon_taxid_index IF NOT EXISTS FOR (t:Taxon) ON (t.taxid)")
            
            # Create index on scientific_name for searches
            session.run("CREATE INDEX taxon_name_index IF NOT EXISTS FOR (t:Taxon) ON (t.scientific_name)")
            
        print("Indexes created.")
    
    def load_taxonomy_into_neo4j(self, extract_dir: str):
        """Load the complete NCBI taxonomy into Neo4j"""
        nodes_path = os.path.join(extract_dir, "nodes.dmp")
        names_path = os.path.join(extract_dir, "names.dmp")
        
        if not os.path.exists(nodes_path) or not os.path.exists(names_path):
            raise FileNotFoundError("Required NCBI files not found in extracted archive")
        
        # Parse the files
        nodes = self.parse_nodes_file(nodes_path)
        names = self.parse_names_file(names_path)
        
        # Clear existing data and create indexes
        self.clear_existing_data()
        self.create_indexes()
        
        # Prepare bulk insert data for nodes
        print("Loading taxonomy nodes into Neo4j...")
        
        total_nodes = len(nodes)
        chunk_size = 10000
        
        with self.driver.session() as session:
            # Create all nodes first (without relationships)
            node_data = []
            for i, (taxid, node_info) in enumerate(nodes.items()):
                if i % chunk_size == 0 and i > 0:
                    # Insert this chunk
                    progress = (i / total_nodes) * 100
                    print(f"\rCreating nodes: {progress:.1f}% ({i:,}/{total_nodes:,})", end="", flush=True)
                    
                    session.run("""
                        UNWIND $nodes as node
                        CREATE (:Taxon {
                            taxid: node.taxid,
                            scientific_name: node.scientific_name,
                            common_name: node.common_name,
                            rank: node.rank
                        })
                    """, nodes=node_data)
                    
                    node_data = []
                
                scientific_name = names.get(taxid, {}).get('scientific_name', f'Unknown_{taxid}')
                common_name = names.get(taxid, {}).get('common_name')
                
                node_data.append({
                    'taxid': taxid,
                    'scientific_name': scientific_name,
                    'common_name': common_name,
                    'rank': node_info['rank']
                })
            
            # Insert remaining nodes
            if node_data:
                session.run("""
                    UNWIND $nodes as node
                    CREATE (:Taxon {
                        taxid: node.taxid,
                        scientific_name: node.scientific_name,
                        common_name: node.common_name,
                        rank: node.rank
                    })
                """, nodes=node_data)
        
        print(f"\nCreated {total_nodes:,} taxonomy nodes")
        
        # Create relationships
        print("Creating parent-child relationships...")
        
        with self.driver.session() as session:
            relationship_data = []
            processed = 0
            
            for taxid, node_info in nodes.items():
                parent_taxid = node_info['parent_taxid']
                
                # Skip root node (parent_taxid is None or same as taxid)
                if parent_taxid and parent_taxid != taxid:
                    relationship_data.append({
                        'parent_taxid': parent_taxid,
                        'child_taxid': taxid
                    })
                
                processed += 1
                
                if len(relationship_data) >= chunk_size:
                    # Insert this chunk of relationships
                    progress = (processed / total_nodes) * 100
                    print(f"\rCreating relationships: {progress:.1f}% ({processed:,}/{total_nodes:,})", end="", flush=True)
                    
                    session.run("""
                        UNWIND $relationships as rel
                        MATCH (parent:Taxon {taxid: rel.parent_taxid})
                        MATCH (child:Taxon {taxid: rel.child_taxid})
                        CREATE (parent)-[:PARENT_OF]->(child)
                    """, relationships=relationship_data)
                    
                    relationship_data = []
            
            # Insert remaining relationships
            if relationship_data:
                session.run("""
                    UNWIND $relationships as rel
                    MATCH (parent:Taxon {taxid: rel.parent_taxid})
                    MATCH (child:Taxon {taxid: rel.child_taxid})
                    CREATE (parent)-[:PARENT_OF]->(child)
                """, relationships=relationship_data)
        
        print(f"\nCreated parent-child relationships")
        print(f"Successfully loaded {total_nodes:,} taxonomy entries into Neo4j")
    
    def verify_migration(self):
        """Verify the migration was successful"""
        print("\n=== Verifying Migration ===")
        
        with self.driver.session() as session:
            # Count total nodes
            node_count = session.run("MATCH (n:Taxon) RETURN count(n) as count").single()['count']
            print(f"Total nodes: {node_count:,}")
            
            # Count relationships
            rel_count = session.run("MATCH ()-[r:PARENT_OF]->() RETURN count(r) as count").single()['count']
            print(f"Total relationships: {rel_count:,}")
            
            # Test specific species
            test_species = [
                (9606, "Homo sapiens"),
                (9544, "Macaca mulatta"),
                (9685, "Felis catus"),
                (9526, "Catarrhini")
            ]
            
            print("\nTesting specific species:")
            for taxid, expected_name in test_species:
                result = session.run("""
                    MATCH (t:Taxon {taxid: $taxid})
                    RETURN t.scientific_name as name, t.rank as rank
                """, taxid=taxid).single()
                
                if result:
                    print(f"✓ {expected_name} (taxid: {taxid}) - {result['name']} ({result['rank']})")
                else:
                    print(f"✗ {expected_name} (taxid: {taxid}) - NOT FOUND")
            
            # Test human-monkey ancestry
            print("\nTesting human-monkey common ancestry:")
            lca_result = session.run("""
                // Get ancestors of human (9606)
                MATCH (s1:Taxon {taxid: 9606})
                MATCH (s1)<-[:PARENT_OF*0..20]-(a1:Taxon)
                WITH collect(a1.taxid) as ancestors1
                
                // Get ancestors of monkey (9544)  
                MATCH (s2:Taxon {taxid: 9544})
                MATCH (s2)<-[:PARENT_OF*0..20]-(a2:Taxon)
                WITH ancestors1, collect(a2.taxid) as ancestors2
                
                RETURN size(ancestors1) as human_ancestor_count,
                       size(ancestors2) as monkey_ancestor_count,
                       size([x IN ancestors1 WHERE x IN ancestors2]) as common_count
            """).single()
            
            print(f"Human ancestors: {lca_result['human_ancestor_count']}")
            print(f"Monkey ancestors: {lca_result['monkey_ancestor_count']}")
            print(f"Common ancestors: {lca_result['common_count']}")
            
            if lca_result['common_count'] > 0:
                print("✓ Human-monkey ancestry test PASSED")
            else:
                print("✗ Human-monkey ancestry test FAILED")
    
    def run_migration(self):
        """Run the complete migration process"""
        try:
            print("=== NCBI to Neo4j Migration ===")
            print("This will download and process the complete NCBI taxonomy database.")
            print("The process may take 15-30 minutes depending on your internet connection.\n")
            
            # Download and extract NCBI data
            extract_dir = self.download_ncbi_taxonomy()
            
            # Load into Neo4j
            self.load_taxonomy_into_neo4j(extract_dir)
            
            # Verify migration
            self.verify_migration()
            
            print("\n=== Migration Complete! ===")
            print("The complete NCBI taxonomy is now loaded in Neo4j.")
            
            # Cleanup
            shutil.rmtree(self.temp_dir)
            
        except Exception as e:
            print(f"\nError during migration: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            if hasattr(self, 'driver'):
                self.driver.close()

class SimpleAutoInitializer:
    """Simple auto-initialization for database setup"""
    
    def __init__(self):
        self.is_running = False
        self.is_complete = False
        self.error = None
        
    def start_import(self):
        """Start database import in background"""
        if self.is_running:
            return False
            
        self.is_running = True
        self.is_complete = False
        self.error = None
        
        # Start import in background thread
        import threading
        thread = threading.Thread(target=self._run_import, daemon=True)
        thread.start()
        return True
    
    def _run_import(self):
        """Run the import process"""
        try:
            print("🔄 Starting NCBI taxonomy download and import...")
            migrator = NCBIToNeo4jMigrator()
            migrator.run_migration()
            
            self.is_complete = True
            self.is_running = False
            print("✅ Database import completed successfully!")
            
        except Exception as e:
            self.error = str(e)
            self.is_running = False
            print(f"❌ Database import failed: {e}")

# Global instance for app to use
auto_initializer = SimpleAutoInitializer()

def main():
    """Main entry point for NCBI to Neo4j migration"""
    migrator = NCBIToNeo4jMigrator()
    migrator.run_migration()

if __name__ == "__main__":
    main()
