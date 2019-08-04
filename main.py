import config

from flask import current_app, Flask, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

import socket

# app = bookshelf.create_app(config)

app = Flask(__name__)
app.config.from_object(config)
print(app)
db = SQLAlchemy(app)


@app.route("/")
def index():
    # results = db.session.execute('SELECT * FROM users')
    # print(results)
    # host_name = socket.gethostname()
    # host_ip = socket.gethostbyname(host_name)
    # print("Hostname :  ", host_name)
    # print("IP : ", host_ip)
    return jsonify({"name": "sam"})

    # return redirect(url_for('crud.list'))

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
