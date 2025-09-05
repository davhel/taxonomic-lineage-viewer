"""
Simple Neo4j-based taxonomic lineage viewer
Focus: Just view the lineage of a species by taxID
"""

import os
from neo4j import GraphDatabase
from typing import List, Dict, Optional

class SimpleLineageViewer:
    def __init__(self, uri=None, user=None, password=None):
        """Initialize connection to Neo4j database"""
        # Use environment variables with fallback to defaults
        uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = user or os.getenv("NEO4J_USERNAME", "neo4j")
        password = password or os.getenv("NEO4J_PASSWORD", "neotaxonomy")
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print(f"✅ Connected to Neo4j at {uri}")
        except Exception as e:
            print(f"❌ Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close the database connection"""
        self.driver.close()
    
    def is_database_empty(self) -> bool:
        """Check if the database has any taxonomy data"""
        try:
            with self.driver.session() as session:
                result = session.run("MATCH (n:Taxon) RETURN count(n) as count LIMIT 1")
                count = result.single()['count']
                return count == 0
        except Exception:
            return True  # Assume empty if we can't check
    
    def get_species_lineage(self, taxid: int) -> List[Dict]:
        """Get the complete lineage of a species from itself up to root"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (species:Taxon {taxid: $taxid})
                MATCH path = (species)<-[:PARENT_OF*]-(ancestor)
                WITH nodes(path) as lineage_nodes
                UNWIND lineage_nodes as node
                RETURN DISTINCT 
                    node.taxid as taxid,
                    node.scientific_name as scientific_name,
                    node.common_name as common_name,
                    node.rank as rank
                """
            , taxid=taxid)
            
            lineage = []
            for record in result:
                lineage.append({
                    'taxid': record['taxid'],
                    'scientific_name': record['scientific_name'],
                    'common_name': record['common_name'],
                    'rank': record['rank'],
                    'display_name': record['common_name'] or record['scientific_name']
                })
            
            return lineage
    
    def search_species_by_name(self, search_query: str, limit: int = 10) -> List[Dict]:
        """Search for species by name"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (t:Taxon)
                WHERE (toLower(t.scientific_name) CONTAINS toLower($search_query) 
                    OR toLower(t.common_name) CONTAINS toLower($search_query))
                AND t.rank = 'species'
                RETURN t.taxid as taxid,
                       t.scientific_name as scientific_name,
                       t.common_name as common_name,
                       t.rank as rank
                ORDER BY 
                    CASE 
                        WHEN toLower(t.common_name) STARTS WITH toLower($search_query) THEN 1
                        WHEN toLower(t.scientific_name) STARTS WITH toLower($search_query) THEN 2
                        ELSE 3
                    END,
                    t.scientific_name
                LIMIT $limit
            """, search_query=search_query, limit=limit)
            
            species = []
            for record in result:
                species.append({
                    'taxid': record['taxid'],
                    'scientific_name': record['scientific_name'],
                    'common_name': record['common_name'],
                    'rank': record['rank'],
                    'display_name': record['common_name'] or record['scientific_name']
                })
            
            return species
    
    def get_sample_species(self, limit: int = 20) -> List[Dict]:
        """Get a sample of interesting species for initial display"""
        # Some well-known taxids for common species
        sample_taxids = [
            9606,   # Human
            9615,   # Dog  
            9685,   # Cat
            9796,   # Horse
            9913,   # Cow
            9031,   # Chicken
            8030,   # Salmon
            7227,   # Fruit fly
            4932,   # Yeast
            562     # E. coli
        ]
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (t:Taxon)
                WHERE t.taxid IN $taxids AND t.rank = 'species'
                RETURN t.taxid as taxid,
                       t.scientific_name as scientific_name,
                       t.common_name as common_name,
                       t.rank as rank
                ORDER BY t.scientific_name
            """, taxids=sample_taxids)
            
            species = []
            for record in result:
                species.append({
                    'taxid': record['taxid'],
                    'scientific_name': record['scientific_name'],
                    'common_name': record['common_name'],
                    'rank': record['rank'],
                    'display_name': record['common_name'] or record['scientific_name']
                })
            
            return species
    
    def get_comparative_lineage(self, taxid1: int, taxid2: int) -> Dict:
        """Get comparative lineage between two species, showing shared and unique ancestors"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s1:Taxon {taxid: $taxid1})
                MATCH (s1)<-[:PARENT_OF*0..]-(l1)
                WITH s1, collect(DISTINCT l1) as lineage1
                MATCH (s2:Taxon {taxid: $taxid2})
                MATCH (s2)<-[:PARENT_OF*0..]-(l2)
                WITH s1, lineage1, s2, collect(DISTINCT l2) as lineage2
                RETURN s1, s2, lineage1, lineage2,
                       [x IN lineage1 WHERE x IN lineage2] as common_data
            """, taxid1=taxid1, taxid2=taxid2)
            
            record = result.single()
            if not record:
                return {"error": "Species not found"}
            
            # Single mapping function - convert Node to our final format
            def to_lineage_item(node, common_taxids):
                return {
                    'taxid': node['taxid'],
                    'scientific_name': node['scientific_name'],
                    'common_name': node['common_name'],
                    'rank': node['rank'],
                    'shared': node['taxid'] in common_taxids,
                    'display_name': node['common_name'] or node['scientific_name']
                }
            
            # Extract data once
            s1, s2 = record['s1'], record['s2']
            common_taxids = {node['taxid'] for node in record['common_data']}
            
            # Rank order for sorting
            rank_order = {
                'species': 1, 'genus': 2, 'subfamily': 3, 'family': 4, 'suborder': 5,
                'order': 6, 'superorder': 7, 'class': 8, 'phylum': 9, 'kingdom': 10,
                'superkingdom': 11, 'domain': 12, 'cellular root': 13, 'no rank': 14
            }
            
            # Single transformation: Node -> final format, sorted
            lineage1 = [to_lineage_item(node, common_taxids) for node in record['lineage1']]
            lineage2 = [to_lineage_item(node, common_taxids) for node in record['lineage2']]

            # Most recent common ancestor
            if record['common_data']:
                mrca = min(record['common_data'], key=lambda x: rank_order.get(x['rank'], 15))
                common_ancestor = {
                    'taxid': mrca['taxid'],
                    'rank': mrca['rank'], 
                    'name': mrca['common_name'] or mrca['scientific_name']
                }
            else:
                common_ancestor = None
            
            return {
                'species1': {
                    'taxid': s1['taxid'],
                    'scientific_name': s1['scientific_name'],
                    'common_name': s1['common_name'],
                    'display_name': s1['common_name'] or s1['scientific_name'],
                    'lineage': lineage1
                },
                'species2': {
                    'taxid': s2['taxid'],
                    'scientific_name': s2['scientific_name'], 
                    'common_name': s2['common_name'],
                    'display_name': s2['common_name'] or s2['scientific_name'],
                    'lineage': lineage2
                },
                'comparison': {
                    'common_ancestor': common_ancestor,
                    'total_common_ancestors': len(record['common_data'])
                }
            }
