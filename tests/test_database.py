#!/usr/bin/env python3
"""
Test to identify the NCBI taxonomy database problem with node 9526 (Catarrhini)
having multiple or incorrect parent relationships.
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from neo4j import GraphDatabase
from models import SimpleLineageViewer

class TestNCBIDatabaseIntegrity:
    """Test cases to identify database integrity issues in NCBI taxonomy"""
    
    def setup_method(self):
        """Setup test environment"""
        self.viewer = SimpleLineageViewer()
        self.driver = self.viewer.driver
    
    def test_node_9526_single_parent(self):
        """Test that node 9526 (Catarrhini) has exactly one parent relationship"""
        with self.driver.session() as session:
            # Check how many parent relationships node 9526 has
            result = session.run("""
                MATCH (catarrhini:Taxon {taxid: 9526})
                MATCH (parent)-[:PARENT_OF]->(catarrhini)
                RETURN parent.taxid as parent_taxid, parent.scientific_name as parent_name,
                       parent.rank as parent_rank
            """).data()
            
            print(f"\nNode 9526 (Catarrhini) has {len(result)} parent(s):")
            for parent in result:
                print(f"  Parent: {parent['parent_taxid']} - {parent['parent_name']} ({parent['parent_rank']})")
            
            # A node should have exactly one parent (except root)
            assert len(result) == 1, f"Node 9526 should have exactly 1 parent, but has {len(result)}"
    
    def test_node_9526_expected_parent(self):
        """Test that node 9526 has the expected parent according to NCBI data"""
        with self.driver.session() as session:
            # According to your grep, 9526 should have parent 314293
            result = session.run("""
                MATCH (catarrhini:Taxon {taxid: 9526})
                MATCH (expected_parent:Taxon {taxid: 314293})
                MATCH (parent)-[:PARENT_OF]->(catarrhini)
                RETURN parent.taxid = 314293 as has_expected_parent,
                       parent.taxid as actual_parent_taxid,
                       parent.scientific_name as actual_parent_name
            """).single()
            
            if result:
                print(f"\nNode 9526 actual parent: {result['actual_parent_taxid']} - {result['actual_parent_name']}")
                print(f"Has expected parent (314293): {result['has_expected_parent']}")
                
                assert result['has_expected_parent'], f"Node 9526 should have parent 314293, but has {result['actual_parent_taxid']}"
            else:
                pytest.fail("Could not find node 9526 or it has no parent")
    
    def test_nodes_314145_and_314293_exist(self):
        """Test that the problematic nodes 314145 and 314293 exist in the database"""
        with self.driver.session() as session:
            # Check if both nodes exist
            result = session.run("""
                MATCH (n1:Taxon {taxid: 314145})
                MATCH (n2:Taxon {taxid: 314293})
                RETURN n1.scientific_name as name_314145, n1.rank as rank_314145,
                       n2.scientific_name as name_314293, n2.rank as rank_314293
            """).single()
            
            if result:
                print(f"\nNode 314145: {result['name_314145']} ({result['rank_314145']})")
                print(f"Node 314293: {result['name_314293']} ({result['rank_314293']})")
            else:
                pytest.fail("One or both of nodes 314145, 314293 do not exist in the database")
    
    def test_no_duplicate_parent_relationships(self):
        """Test that no node has duplicate parent relationships"""
        with self.driver.session() as session:
            # Find any nodes with multiple parents
            result = session.run("""
                MATCH (child:Taxon)
                MATCH (parent)-[:PARENT_OF]->(child)
                WITH child, count(parent) as parent_count
                WHERE parent_count > 1
                RETURN child.taxid as child_taxid, child.scientific_name as child_name,
                       parent_count
                ORDER BY parent_count DESC
                LIMIT 10
            """).data()
            
            print(f"\nNodes with multiple parents ({len(result)} found):")
            for node in result:
                print(f"  {node['child_taxid']} - {node['child_name']}: {node['parent_count']} parents")
            
            # No node should have multiple parents in a proper taxonomy
            assert len(result) == 0, f"Found {len(result)} nodes with multiple parents"
    
    def test_no_circular_relationships(self):
        """Test that there are no circular parent-child relationships"""
        with self.driver.session() as session:
            # Check for any node that is both parent and child of another node
            result = session.run("""
                MATCH (a:Taxon)-[:PARENT_OF]->(b:Taxon)-[:PARENT_OF]->(a)
                RETURN a.taxid as node_a, a.scientific_name as name_a,
                       b.taxid as node_b, b.scientific_name as name_b
                LIMIT 10
            """).data()
            
            print(f"\nCircular relationships found: {len(result)}")
            for rel in result:
                print(f"  {rel['node_a']} ({rel['name_a']}) <-> {rel['node_b']} ({rel['name_b']})")
            
            assert len(result) == 0, f"Found {len(result)} circular relationships"
    
    def test_relationship_direction_consistency(self):
        """Test that all relationships point in the correct direction (parent -> child)"""
        with self.driver.session() as session:
            # Check the relationship direction for node 9526
            result = session.run("""
                MATCH path = (root)-[:PARENT_OF*]->(catarrhini:Taxon {taxid: 9526})
                WHERE NOT (()-[:PARENT_OF]->(root))
                WITH path, root
                RETURN root.taxid as root_taxid, root.scientific_name as root_name,
                       length(path) as path_length
                ORDER BY path_length DESC
                LIMIT 1
            """).single()
            
            if result:
                print(f"\nPath to root from 9526: length = {result['path_length']}")
                print(f"Root node: {result['root_taxid']} - {result['root_name']}")
                
                # Should be able to trace back to root
                assert result['path_length'] > 0, "Should be able to trace path to root"
            else:
                pytest.fail("Cannot trace path from node 9526 to root")
    
    def test_specific_lineage_integrity(self):
        """Test the specific lineage path for node 9526 to identify the problem"""
        with self.driver.session() as session:
            # Get the complete lineage for node 9526
            result = session.run("""
                MATCH path = (ancestor)-[:PARENT_OF*0..]->(catarrhini:Taxon {taxid: 9526})
                WITH ancestor, length(path) as depth
                ORDER BY depth DESC
                RETURN ancestor.taxid as taxid, 
                       ancestor.scientific_name as name,
                       ancestor.rank as rank,
                       depth
            """).data()
            
            print(f"\nComplete lineage for node 9526 ({len(result)} levels):")
            for i, level in enumerate(result):
                print(f"  {i}: {level['taxid']} - {level['name']} ({level['rank']}) [depth: {level['depth']}]")
            
            # Check for any anomalies in the lineage
            taxids_in_lineage = [level['taxid'] for level in result]
            
            # Should contain the expected nodes based on NCBI data
            assert 314293 in taxids_in_lineage, "Node 314293 should be in the lineage of 9526"
            
    def test_compare_database_with_ncbi_structure(self):
        """Compare database structure with expected NCBI structure"""
        with self.driver.session() as session:
            # Check what the database thinks are the children of 314293
            children_314293 = session.run("""
                MATCH (parent:Taxon {taxid: 314293})-[:PARENT_OF]->(child)
                RETURN child.taxid as child_taxid, child.scientific_name as child_name
                ORDER BY child.taxid
            """).data()
            
            print(f"\nChildren of 314293 in database ({len(children_314293)}):")
            for child in children_314293:
                print(f"  {child['child_taxid']} - {child['child_name']}")
            
            # Based on your grep, should include 9479 and 9526
            child_taxids = [child['child_taxid'] for child in children_314293]
            assert 9526 in child_taxids, "Node 9526 should be a child of 314293"
            assert 9479 in child_taxids, "Node 9479 should be a child of 314293"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
