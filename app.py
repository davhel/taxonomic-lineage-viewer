"""
Flask app for taxonomic lineage viewing
Clean, minimal interface to view and compare taxonomic lineages
"""

from flask import Flask, render_template, jsonify, request
from models import SimpleLineageViewer
from setup import auto_initializer

app = Flask(__name__)

# Initialize the lineage viewer
try:
    lineage_viewer = SimpleLineageViewer()
    print("🚀 Connected to Neo4j database")
    
    # Check if database is empty and auto-start import if needed
    if lineage_viewer.is_database_empty():
        print("📦 Database is empty - starting automatic import...")
        if auto_initializer.start_import():
            print("🔄 Import started in background")
        else:
            print("❌ Failed to start import")
    else:
        print("✅ Database contains data - ready to serve")
        
except Exception as e:
    print(f"❌ Failed to initialize: {e}")
    lineage_viewer = None

@app.route('/')
def index():
    """Main page - comparative lineage viewer"""
    return render_template('index.html')

@app.route('/api/search')
def search_species():
    """Search for species by name"""
    if not lineage_viewer:
        return jsonify({'error': 'Database not available'}), 500
    
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'species': []})
    
    try:
        species = lineage_viewer.search_species_by_name(query, limit=10)
        return jsonify({'species': species})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lineage/<int:taxid>')
def get_lineage(taxid):
    """Get the lineage of a species"""
    if not lineage_viewer:
        return jsonify({'error': 'Database not available'}), 500
    
    try:
        lineage = lineage_viewer.get_species_lineage(taxid)
        if not lineage:
            return jsonify({'error': 'Species not found'}), 404
        
        return jsonify({'lineage': lineage})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sample')
def get_sample_species():
    """Get sample species for initial display"""
    if not lineage_viewer:
        return jsonify({'error': 'Database not available'}), 500
    
    try:
        species = lineage_viewer.get_sample_species()
        return jsonify({'species': species})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/compare/<int:taxid>')
def compare_with_human(taxid):
    """Compare a species lineage with human lineage"""
    if not lineage_viewer:
        return jsonify({'error': 'Database not available'}), 500
    
    try:
        # Always compare with human (taxid: 9606)
        comparison = lineage_viewer.get_comparative_lineage(taxid, 9606)
        if 'error' in comparison:
            return jsonify(comparison), 404
        
        return jsonify(comparison)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/compare/<int:taxid1>/<int:taxid2>')
def compare_two_species(taxid1, taxid2):
    """Compare lineages of two species"""
    if not lineage_viewer:
        return jsonify({'error': 'Database not available'}), 500
    
    try:
        comparison = lineage_viewer.get_comparative_lineage(taxid1, taxid2)
        if 'error' in comparison:
            return jsonify(comparison), 404
        
        return jsonify(comparison)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/import/status')
def import_status():
    """Get import status"""
    status = {
        'is_running': auto_initializer.is_running,
        'is_complete': auto_initializer.is_complete,
        'has_error': auto_initializer.error is not None,
        'error_message': auto_initializer.error
    }
    
    # Add database info if available
    if lineage_viewer and not auto_initializer.is_running:
        try:
            status['database_empty'] = lineage_viewer.is_database_empty()
        except:
            status['database_empty'] = True
    
    return jsonify(status)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
