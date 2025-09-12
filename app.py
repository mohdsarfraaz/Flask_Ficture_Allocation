
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os
from werkzeug.utils import secure_filename
from ficture_processing import ficture_allocation

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Load data
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)

            columns = df.columns.tolist()
            return render_template('index.html', columns=columns, preview=df.head().to_html(classes='table table-bordered'), filename=filename)

    return render_template('index.html', columns=None)

@app.route('/process', methods=['POST'])
def process():
    filename = request.form['filename']
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if filename.endswith('.csv'):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    # Column mapping
    col_map = {
        'store': request.form['store_col'],
        'department': request.form['department_col'],
        'udf': request.form['udf_col'],
        'mc_fic': request.form['mc_fic_col'],
        'cont_per': request.form['cont_per_col'],
        'art': request.form['art_col']
    }

    # Process data
    processed_df = ficture_allocation(df, col_map)

    # Save result to CSV (for download)
    result_path = os.path.join(app.config['UPLOAD_FOLDER'], f"processed_{filename}")
    processed_df.to_csv(result_path, index=False)

    # Convert to HTML table for preview
    table_html = processed_df.head(100).to_html(classes='table table-striped', index=False)

    return render_template('result.html', table=table_html, filename=filename)

if __name__ == '__main__':
    app.run(debug=True)
