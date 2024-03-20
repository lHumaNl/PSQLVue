from flask import Flask, request, render_template


app = Flask(__name__)


@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')


@app.route('/execute', methods=['POST'])
def execute():
    query = request.form['query']
    result = app.config['psql_connection'].execute_query(query)
    return "<pre>" + result + "</pre>"
