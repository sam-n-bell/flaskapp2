import config

from flask import current_app, Flask, redirect, url_for, jsonify, request
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config.from_object(config)
db = SQLAlchemy(app)


@app.route("/", methods=['GET'])
def index():
    return jsonify({"Events Platform v1": "APAD Project - Sasha Opela & Sam Bell"})


@app.route("/users", methods=['GET', 'POST'])
def get_users():
    if request.method == 'GET':
        query = db.session.execute('SELECT * FROM users')
        results = query.fetchall()  # returns a list
        results_dicts = []
        for r in results:
            results_dicts.append(dict(r))
        return jsonify(results_dicts)
    else:
        return jsonify({"message": "post"})


@app.route("/venues", methods=['GET', 'POST'])
def get_venues():
    if request.method == 'GET':
        query = db.session.execute('SELECT * FROM venues')
        results = query.fetchall()  # returns a list
        results_dicts = []
        for r in results:
            results_dicts.append(dict(r))
        return jsonify(results_dicts)
    else:
        return jsonify({"message": "post"})



# Add an error handler. This is useful for debugging the live application,
# however, you should disable the output of the exception for production
# applications.

# @app.errorhandler(500)
# def server_error(e):
#     return """
#     An internal error occurred: <pre>{}</pre>
#     See logs for full stacktrace.
#     """.format(e), 500


# This is only used when running locally. When running live, gunicorn runs
# the application.


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
