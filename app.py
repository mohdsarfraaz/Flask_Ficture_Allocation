
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os
from werkzeug.utils import secure_filename
from ficture_processing import ficture_allocation

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'static/results'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

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

    col_map = {
        'store': request.form['store_col'],
        'department': request.form['department_col'],
        'udf': request.form['udf_col'],
        'mc_fic': request.form['mc_fic_col'],
        'cont_per': request.form['cont_per_col'],
        'art': request.form['art_col']
    }

    processed_df = ficture_allocation(df, col_map)

    # Order columns so the original data remains at the front of the table.
    original_cols = [c for c in df.columns if c in processed_df.columns]
    allocation_order = [
        'FIC_REQ_0', 'Allocate_0', 'MC_BAl_0',
        'FIC_REQ_1', 'Allocate_1', 'MC_BAl_1',
        'FIC_REQ_2', 'Allocate_2', 'MC_BAl_2',
        'rest_per', 'Final_Allocation'
    ]
    allocation_cols = [col for col in allocation_order if col in processed_df.columns]
    processed_df = processed_df[original_cols + allocation_cols]

    # Save result to static folder
    result_filename = f"processed_{filename.replace(' ', '_')}"
    result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
    processed_df.to_csv(result_path, index=False)

    table_html = processed_df.to_html(
        classes='table table-bordered table-striped align-middle',
        index=False,
        table_id='resultTable'
    )

    plot_series = processed_df.groupby(col_map['store'])['Final_Allocation'].sum().reset_index()
    plot_data = {
        'store': plot_series[col_map['store']].tolist(),
        'allocation': plot_series['Final_Allocation'].tolist()
    }

    return render_template(
        'result.html',
        table=table_html,
        filename=filename,
        result_filename=result_filename,
        column_map=col_map,
        plot_data=plot_data
    )

if __name__ == '__main__':
    app.run(debug=True)
