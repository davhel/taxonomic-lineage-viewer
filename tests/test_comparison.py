"""
Pytest tests for the comparative lineage functionality
"""

import pytest
import requests
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import SimpleLineageViewer


class TestComparativeLineage:
    """Test class for comparative lineage functionality"""
    
    @pytest.fixture(scope="class")
    def viewer(self):
        """Create a SimpleLineageViewer instance for testing"""
        viewer = SimpleLineageViewer()
        yield viewer
        viewer.close()
    
    def test_connection(self, viewer):
        """Test that we can connect to Neo4j"""
        # Connection is tested in the fixture creation
        assert viewer.driver is not None
    
    def test_cat_human_comparison(self, viewer):
        """Test comparing cat with human"""
        cat_taxid = 9685  # Cat
        human_taxid = 9606  # Human
        
        comparison = viewer.get_comparative_lineage(cat_taxid, human_taxid)
        
        # Check no error
        assert 'error' not in comparison
        
        # Check structure
        assert 'species1' in comparison
        assert 'species2' in comparison
        assert 'comparison' in comparison
        
        # Check species data
        assert comparison['species1']['taxid'] == cat_taxid
        assert comparison['species2']['taxid'] == human_taxid
        assert comparison['species1']['display_name'] == 'cat'
        assert comparison['species2']['display_name'] == 'human'
        
        # Check lineage data
        assert len(comparison['species1']['lineage']) > 0
        assert len(comparison['species2']['lineage']) > 0
        
        # Check that each lineage item has required fields
        for item in comparison['species1']['lineage']:
            assert 'taxid' in item
            assert 'rank' in item
            assert 'display_name' in item
            assert 'shared' in item
            assert isinstance(item['shared'], bool)
        
        for item in comparison['species2']['lineage']:
            assert 'taxid' in item
            assert 'rank' in item
            assert 'display_name' in item
            assert 'shared' in item
            assert isinstance(item['shared'], bool)
        
        # Check common ancestor
        assert comparison['comparison']['common_ancestor'] is not None
        assert comparison['comparison']['common_ancestor']['name'] == 'Laurasiatheria'
        assert comparison['comparison']['common_ancestor']['rank'] == 'superorder'
        assert comparison['comparison']['total_common_ancestors'] > 0
        
        # Check that some ancestors are shared
        shared_count_species1 = sum(1 for item in comparison['species1']['lineage'] if item['shared'])
        shared_count_species2 = sum(1 for item in comparison['species2']['lineage'] if item['shared'])
        assert shared_count_species1 > 0
        assert shared_count_species2 > 0
    
    def test_cow_human_comparison(self, viewer):
        """Test comparing cow with human"""
        cow_taxid = 9913  # Cow
        human_taxid = 9606  # Human
        
        comparison = viewer.get_comparative_lineage(cow_taxid, human_taxid)
        
        # Check no error
        assert 'error' not in comparison
        
        # Check species data
        assert comparison['species1']['taxid'] == cow_taxid
        assert comparison['species2']['taxid'] == human_taxid
        assert comparison['species1']['display_name'] == 'bovine'
        assert comparison['species2']['display_name'] == 'human'
        
        # Check common ancestor
        assert comparison['comparison']['common_ancestor'] is not None
        assert comparison['comparison']['common_ancestor']['name'] == 'Laurasiatheria'
        assert comparison['comparison']['total_common_ancestors'] > 0
    
    def test_human_human_comparison(self, viewer):
        """Test comparing human with human (edge case)"""
        human_taxid = 9606  # Human
        
        comparison = viewer.get_comparative_lineage(human_taxid, human_taxid)
        
        # Check no error
        assert 'error' not in comparison
        
        # Should be identical
        assert comparison['species1']['taxid'] == human_taxid
        assert comparison['species2']['taxid'] == human_taxid
        
        # All ancestors should be shared
        for item in comparison['species1']['lineage']:
            assert item['shared'] is True
        
        for item in comparison['species2']['lineage']:
            assert item['shared'] is True
        
        # Most recent common ancestor should be human itself
        assert comparison['comparison']['common_ancestor']['taxid'] == human_taxid
    
    def test_invalid_taxid(self, viewer):
        """Test with invalid taxid"""
        invalid_taxid = 999999999
        human_taxid = 9606
        
        comparison = viewer.get_comparative_lineage(invalid_taxid, human_taxid)
        
        # Should return an error
        assert 'error' in comparison
    
    def test_lineage_sorting(self, viewer):
        """Test that lineages are properly sorted by taxonomic rank"""
        cat_taxid = 9685
        human_taxid = 9606
        
        comparison = viewer.get_comparative_lineage(cat_taxid, human_taxid)
        
        # Check that species comes first, then genus, etc.
        cat_lineage = comparison['species1']['lineage']
        human_lineage = comparison['species2']['lineage']
        
        # First item should be species
        assert cat_lineage[0]['rank'] == 'species'
        assert human_lineage[0]['rank'] == 'species'
        
        # Check that ranks are in taxonomic order (species -> genus -> family -> etc.)
        rank_hierarchy = ['species', 'genus', 'subfamily', 'family', 'suborder', 'order', 'superorder', 'class']
        
        for lineage in [cat_lineage, human_lineage]:
            previous_rank_index = -1
            for item in lineage:
                if item['rank'] in rank_hierarchy:
                    current_rank_index = rank_hierarchy.index(item['rank'])
                    assert current_rank_index >= previous_rank_index, f"Ranks not in order: {item['rank']} should come after previous rank"
                    previous_rank_index = current_rank_index


class TestAPIEndpoints:
    """Test class for API endpoints"""
    
    BASE_URL = "http://localhost:5001"
    
    @pytest.fixture(scope="class", autouse=True)
    def check_server(self):
        """Check if the server is running before running API tests"""
        try:
            response = requests.get(f"{self.BASE_URL}/api/sample", timeout=5)
            if response.status_code != 200:
                pytest.skip("Server not responding correctly")
        except requests.exceptions.ConnectionError:
            pytest.skip("Server not running on port 5001")
    
    def test_compare_cat_endpoint(self):
        """Test /api/compare/9685 endpoint (cat vs human)"""
        response = requests.get(f"{self.BASE_URL}/api/compare/9685")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['species1']['display_name'] == 'cat'
        assert data['species2']['display_name'] == 'human'
        assert data['comparison']['common_ancestor']['name'] == 'Laurasiatheria'
    
    def test_compare_cow_endpoint(self):
        """Test /api/compare/9913 endpoint (cow vs human)"""
        response = requests.get(f"{self.BASE_URL}/api/compare/9913")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['species1']['display_name'] == 'bovine'
        assert data['species2']['display_name'] == 'human'
        assert data['comparison']['common_ancestor']['name'] == 'Laurasiatheria'
    
    def test_compare_human_endpoint(self):
        """Test /api/compare/9606 endpoint (human vs human)"""
        response = requests.get(f"{self.BASE_URL}/api/compare/9606")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['species1']['display_name'] == 'human'
        assert data['species2']['display_name'] == 'human'
        assert data['comparison']['common_ancestor']['taxid'] == 9606
    
    def test_compare_invalid_taxid_endpoint(self):
        """Test /api/compare endpoint with invalid taxid"""
        response = requests.get(f"{self.BASE_URL}/api/compare/999999999")
        
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data
    
    def test_existing_endpoints_still_work(self):
        """Test that existing endpoints still function"""
        # Test sample endpoint
        response = requests.get(f"{self.BASE_URL}/api/sample")
        assert response.status_code == 200
        data = response.json()
        assert 'species' in data
        assert len(data['species']) > 0
        
        # Test search endpoint
        response = requests.get(f"{self.BASE_URL}/api/search?q=human")
        assert response.status_code == 200
        data = response.json()
        assert 'species' in data
        assert len(data['species']) > 0
        
        # Test lineage endpoint
        response = requests.get(f"{self.BASE_URL}/api/lineage/9606")
        assert response.status_code == 200
        data = response.json()
        assert 'lineage' in data
        assert len(data['lineage']) > 0


class TestDataQuality:
    """Test class for data quality checks"""
    
    @pytest.fixture(scope="class")
    def viewer(self):
        """Create a SimpleLineageViewer instance for testing"""
        viewer = SimpleLineageViewer()
        yield viewer
        viewer.close()
    
    def test_shared_ancestors_consistency(self, viewer):
        """Test that shared ancestors are consistent between species"""
        cat_taxid = 9685
        human_taxid = 9606
        
        comparison = viewer.get_comparative_lineage(cat_taxid, human_taxid)
        
        # Get shared taxids from both lineages
        cat_shared_taxids = {item['taxid'] for item in comparison['species1']['lineage'] if item['shared']}
        human_shared_taxids = {item['taxid'] for item in comparison['species2']['lineage'] if item['shared']}
        
        # Should be identical sets
        assert cat_shared_taxids == human_shared_taxids, "Shared ancestors should be identical between species"
        
        # Should match the total count
        expected_count = comparison['comparison']['total_common_ancestors']
        assert len(cat_shared_taxids) == expected_count
    
    def test_most_recent_common_ancestor_is_shared(self, viewer):
        """Test that the most recent common ancestor appears as shared in both lineages"""
        cat_taxid = 9685
        human_taxid = 9606
        
        comparison = viewer.get_comparative_lineage(cat_taxid, human_taxid)
        
        mrca_taxid = comparison['comparison']['common_ancestor']['taxid']
        
        # Find this taxid in both lineages
        cat_mrca_items = [item for item in comparison['species1']['lineage'] if item['taxid'] == mrca_taxid]
        human_mrca_items = [item for item in comparison['species2']['lineage'] if item['taxid'] == mrca_taxid]
        
        assert len(cat_mrca_items) == 1, "MRCA should appear exactly once in cat lineage"
        assert len(human_mrca_items) == 1, "MRCA should appear exactly once in human lineage"
        
        assert cat_mrca_items[0]['shared'] is True, "MRCA should be marked as shared in cat lineage"
        assert human_mrca_items[0]['shared'] is True, "MRCA should be marked as shared in human lineage"


if __name__ == '__main__':
    # Run pytest with verbose output
    pytest.main([__file__, "-v"])
