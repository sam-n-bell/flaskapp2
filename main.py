import config

from flask import current_app, Flask, redirect, url_for, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text


app = Flask(__name__)
app.config.from_object(config)
db = SQLAlchemy(app)


@app.route("/", methods=['GET'])
def index():
    return jsonify({"Events Platform v1": "APAD Project - Sasha Opela & Sam Bell"})


@app.route("/users", methods=['GET'])
def get_users():
    if request.method == 'GET':
        query = db.session.execute('SELECT * FROM users')
        results = query.fetchall()  # returns a list
        results_dicts = []
        for r in results:
            results_dicts.append(dict(r))
        return jsonify(results_dicts)
    else:
        return jsonify('')


@app.route("/users", methods=['POST'])
def add_user():
    try:
            content = request.json # turns the json request body into a dict :D
            name = content['name']
            email = content['email']
            password = content['password']
            administrator = content['administrator']
            query = db.session.execute("INSERT INTO users (name, email, password, administrator) VALUES (:name, :email, :password, :administrator);",
                               {'name': name, 'email': email, 'password': password, 'administrator': administrator})
            # print(query.lastrowid) # returns last id
            db.session.commit()
            return jsonify({"message": "User Added"}), 201  # returns a 201 status code with a message
    except Exception as e:
        return jsonify({"message": "Error Adding New User"}), 500  # returns a 500 status code with a message


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


@app.route("/events", methods=['GET', 'POST'])
def get_events():
    if request.method == 'GET':
        venue_id = request.args.get('venueId')
        mine = request.args.get('mine')
        time = request.args.get('time')

        query = db.session.execute('SELECT * FROM events')
        results = query.fetchall()  # returns a list
        results_dicts = []
        for r in results:
            results_dicts.append(dict(r))
        return jsonify(results_dicts)
    else:
        return jsonify({"message": "post"})


# same of how to do insert with parameters
# db.my_session.execute(
#     "UPDATE client SET musicVol = :mv, messageVol = :ml",
#     {'mv': music_volume, 'ml': message_volume}
# )

# get query params
# user = request.args.get('user')



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
