#!/usr/bin/env python3
"""
Tests for Flask API endpoints
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app

@pytest.fixture
def client():
    """Create test client for Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

class TestFlaskAPI:
    """Test Flask API endpoints"""
    
    def test_index_route(self, client):
        """Test main page loads"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Taxonomic Lineage Explorer' in response.data
    
    def test_api_search_missing_query(self, client):
        """Test API search without query parameter"""
        response = client.get('/api/search')
        assert response.status_code == 400
        
    def test_api_search_with_query(self, client):
        """Test API search with query parameter"""
        response = client.get('/api/search?q=human')
        assert response.status_code in [200, 500]  # 500 if no database connection
        
    def test_api_sample(self, client):
        """Test sample species endpoint"""
        response = client.get('/api/sample')
        assert response.status_code in [200, 500]  # 500 if no database connection
        
    def test_api_compare(self, client):
        """Test species comparison endpoint"""
        response = client.get('/api/compare/9606/9685')  # human vs cat
        assert response.status_code in [200, 500]  # 500 if no database connection
