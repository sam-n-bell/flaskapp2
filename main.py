import config
import auth
import datetime

from flask import current_app, Flask, redirect, url_for, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_cors import CORS


app = Flask(__name__)
CORS(app)
app.config.from_object(config)
db = SQLAlchemy(app)


@app.route("/", methods=['GET'])
def index():
    return jsonify({"Events Platform v1": "APAD Project - Sasha Opela & Sam Bell"})


def email_pass_validation(email, password):
    email = email.lower()
    query = db.session.execute("SELECT * FROM users WHERE lower(email) = :email", {'email': email})
    user = dict(query.fetchone())
    if user['password'] == password and user['email'] == email:
        return user
    else:
        raise Exception('Invalid login')


def store_token(user, token):
    expires = datetime.date.today() + datetime.timedelta(days=1)
    db.session.execute(
        "INSERT INTO user_tokens (user_id, token, expires) VALUES (:user_id, :token, :expires);",
        {'user_id': user['user_id'], 'token': token, 'expires': expires})
    db.session.commit()


def validate_token(header):
    query = db.session.execute("SELECT ut.* FROM user_tokens ut WHERE ut.token = :token ORDER BY ut.date_created DESC LIMIT 1", {'token': header.split(' ')[1]})
    token_dict = dict(query.fetchone())
    if token_dict['expires'] < datetime.date.today():
        raise Exception('Expired token')
    decoded = auth.decode_token(header)
    return decoded  # user dict


@app.route("/<venueId>/availability", methods=['POST'])
def get_venue_availability(venueId):
    try:
        #  venueId is from the URL
        user = validate_token(request.headers.get('Authorization'))

        query = db.session.execute("", {'event_id': eventId})
        event = dict(query.fetchone())
        return jsonify({'eventid': "blank"})
    except Exception as e:
        return jsonify({'message': "An error occured joining event"}), 500

@app.route("/login", methods=['POST'])
def create_token():
    try:
        content = request.json
        user = email_pass_validation(content['email'], content['password'])
        token = auth.create_token(user)
        store_token(user, token)
        return token, 200
    except Exception as e:
        return jsonify({"message": "Error logging in"}), 500


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
            query = db.session.execute("INSERT INTO users (name, email, password, administrator) VALUES (:name, :email, :password, :administrator);",
                               {'name': content['name'], 'email': content['email'], 'password': content['password'], 'administrator': content['administrator']})
            # print(query.lastrowid) # returns last id
            db.session.commit()
            return jsonify({"message": "User Added"}), 201  # returns a 201 status code with a message
    except Exception as e:
        return jsonify({"message": "Error Adding New User"}), 500  # returns a 500 status code with a message


@app.route("/venues", methods=['GET'])
def get_venues():
    query = db.session.execute('SELECT * FROM venues')
    results = query.fetchall()  # returns a list
    results_dicts = []
    for r in results:
        results_dicts.append(dict(r))
    return jsonify(results_dicts)


@app.route("/venues", methods=['POST'])
def create_venue():
    try:
        content = request.json
        db.session.execute("INSERT INTO venues (name, address, activities) VALUES (:name, :address, :activities",
                          {'name': content['name'], 'address': content['address'], 'activities': content['activities']})
        db.session.commit()
        return jsonify({"message": "Venue Added"}), 201  # returns a 201 status code with a message
    except Exception as e:
        return jsonify({"message": "Error adding venue"}), 500


@app.route("/events", methods=['GET'])
def get_events():
    venue_id = request.args.get('venueId')
    mine = request.args.get('mine')
    time = request.args.get('time')

    query = db.session.execute('SELECT * FROM events')
    results = query.fetchall()  # returns a list
    results_dicts = []
    for r in results:
        results_dicts.append(dict(r))
    return jsonify(results_dicts)


@app.route("/events", methods=['POST'])
def create_event():
    try:
        pass
    except Exception as e:
        return jsonify({"message": "Error adding venue"}), 500

@app.route("/<eventId>/join", methods=['POST'])
def join_event(eventId):
    try:
        # eventId is from the URL
        #
        user = validate_token(request.headers.get('Authorization'))

        query = db.session.execute("SELECT e.*, (COUNT(distinct p.user_id) + SUM(p.num_guests)) AS num_players FROM events e LEFT JOIN participants p on p.event_id = e.event_id WHERE e.event_id = :event_id", {'event_id': eventId})
        event = dict(query.fetchone())
        return jsonify({'eventid': eventId})
    except Exception as e:
        return jsonify({'message': "An error occured joining event"}), 500



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
