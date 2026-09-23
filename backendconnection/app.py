"""Start in lesson 4. Replace display_rows with your own database query in lesson 5."""
import os
from flask import Flask, render_template
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('PROJECT_SECRET_KEY', 'local-practice-only')

@app.get('/')
def home():
    # A temporary mock dataset: this is not a database connection.
    display_rows = [{'title': 'Your first project record', 'category': 'Planning'}]
    return render_template('index.html', rows=display_rows)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)  # Local development only.
