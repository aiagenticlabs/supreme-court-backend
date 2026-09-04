from flask import Flask, request, jsonify
from flask_cors import CORS
import duckdb
import time

app = Flask(__name__)
# Allow your HTML frontend to access this API
CORS(app) 

# Base URL for the AWS bucket
S3_BASE_URL = 'https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com'

@app.route('/api/index', methods=['GET'])
def search_judgments():
    year = request.args.get('year')
    query = request.args.get('query', '')
    petitioner = request.args.get('petitioner', '')
    respondent = request.args.get('respondent', '')
    
    if not year:
        return jsonify({'error': 'Year is required'}), 400

    try:
        start_time = time.time()
        
        # Connect to an in-memory DuckDB instance
        con = duckdb.connect()

        con.execute("SET home_directory='/tmp';")
        con.execute("SET extension_directory='/tmp';")
        
        # Define the Parquet file URL on AWS
        parquet_url = f"{S3_BASE_URL}/metadata/parquet/year={year}/metadata.parquet"
        
        # Build the SQL query securely using parameters
        sql = f"SELECT * FROM read_parquet('{parquet_url}') WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (LOWER(petitioner) LIKE ? OR LOWER(respondent) LIKE ? OR LOWER(description) LIKE ?)"
            like_query = f"%{query.lower()}%"
            params.extend([like_query, like_query, like_query])
            
        if petitioner:
            sql += " AND LOWER(petitioner) LIKE ?"
            params.append(f"%{petitioner.lower()}%")
            
        if respondent:
            sql += " AND LOWER(respondent) LIKE ?"
            params.append(f"%{respondent.lower()}%")
            
        sql += " ORDER BY decision_date DESC LIMIT 100"
        
        # Execute query and convert to list of dictionaries
        results = con.execute(sql, params).fetchdf().fillna('').to_dict(orient='records')
        
        elapsed_time = round((time.time() - start_time) * 1000)
        
        return jsonify({
            'results': results,
            'stats': {'count': len(results), 'timeMs': elapsed_time}
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        con.close()

# Note: In Vercel, we DO NOT use app.run() at the bottom. 
# Vercel's serverless environment handles the execution automatically.
