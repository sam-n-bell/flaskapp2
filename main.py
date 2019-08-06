import config
import auth
import datetime
import utilities

from flask import current_app, Flask, redirect, url_for, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_cors import CORS


app = Flask(__name__)
CORS(app)  # asking to get data back
app.config.from_object(config)  # tells flask the project ID and cloud SQL details
db = SQLAlchemy(app)  # allows us to use SQL queries


@app.route("/", methods=['GET'])  # Home Page for Flask App
def index():
    return jsonify({"Events Platform v1": "APAD Project - Sasha Opela & Sam Bell"})


def email_pass_validation(email, password):  # Making sure when someone logs in the password and email matches on file
    email = email.lower()
    query = db.session.execute("SELECT * FROM users WHERE lower(email) = :email", {'email': email})
    user = dict(query.fetchone())
    if user['password'] == password and user['email'] == email:
        return user
    else:
        raise Exception('Invalid login')

# Takes in a user dictionary and a token string
def store_token(user, token): 
    expires = datetime.date.today() + datetime.timedelta(days=1)
    db.session.execute(
        "INSERT INTO user_tokens (user_id, token, expires) VALUES (:user_id, :token, :expires);",
        {'user_id': user['user_id'], 'token': token, 'expires': expires})
    db.session.commit()

#Checking that the token is not expired
def validate_token(header):
#  split where there is a space in the String - returns a list,( index 0 is Bearer),only return index 1 the token
    query = db.session.execute("SELECT ut.* FROM user_tokens ut WHERE ut.token = :token ORDER BY ut.date_created DESC LIMIT 1", {'token': header.split(' ')[1]})
    token_dict = dict(query.fetchone())
    if token_dict['expires'] < datetime.date.today():
        raise Exception('Expired token')
    decoded = auth.decode_token(header)
    return decoded  # user dict


@app.route("/<venueId>/availability", methods=['GET'])
def get_venue_availability(venueId):
    try:
        # venueId is from the URL
        # when a query param is missing, it's None
        # when a query param is just var=, it's an empty string
        user = validate_token(request.headers.get('Authorization'))
        day = request.args.get('day')
        print(day)
        #day is needed for query
        if day == '' or day == None:
            raise Exception('day needed')

        events_query = db.session.execute("SELECT e.* FROM events e WHERE e.event_day = :day and e.venue_id = :venue_id", {'day': day, 'venue_id': venueId})
        events = events_query.fetchall()

        venue_query = db.session.execute("SELECT v.* FROM venues v WHERE v.venue_id = :venueId", {'venueId': venueId})
        venue = dict(venue_query.fetchone())

        # strptime parses a string "time" to create a new datetime object
        opens = datetime.datetime.strptime(utilities.convert_timedelta_to_string(venue['open_time'], '%H:%M:%S'), '%H:%M:%S')
        closes = datetime.datetime.strptime(utilities.convert_timedelta_to_string(venue['close_time'], '%H:%M:%S'), '%H:%M:%S')
        datetime_difference = (closes - opens)
        hours_diff = datetime_difference.seconds // 3600
        slots = []

        # create time slots to be sent to UI
        for i in range(hours_diff):
            time_dict = {
                "value": opens.strftime('%H:%M:%S'),  # what can be sent to server side code
                "label": opens.strftime('%-I:%M %p'),  # what can be displayed in the UI
                "reserved": False
            }
            slot_begins = opens
            for e in events:
                event_begins = datetime.datetime.strptime(utilities.convert_timedelta_to_string(e['start_time'], '%H:%M:%S'), '%H:%M:%S')
                if (event_begins == slot_begins):
                    time_dict['reserved'] = True
                else:
                    pass
            slots.append(time_dict)
            opens += datetime.timedelta(hours=1)
        return jsonify(slots), 200
    except Exception as e:
        return jsonify({'message': "An error occurred getting time slots for venue"}), 500

#Vue will post data to this route 
@app.route("/login", methods=['POST'])
def create_token():
    try:
        content = request.json #makes dictionary out of json request
        user = email_pass_validation(content['email'], content['password']) #calling validation to make sure email and password will work
        token = auth.create_token(user) 
        store_token(user, token) 
        return token, 201
    except Exception as e:
        return jsonify({"message": "Error logging in"}), 500

#Returning a list of users from the database
@app.route("/users", methods=['GET'])
def get_users():
    try:
        query = db.session.execute('SELECT * FROM users')
        results = query.fetchall()  # returns a list
        results_dicts = []
        for r in results:
            results_dicts.append(dict(r))
        return jsonify(results_dicts)
    except Exception as e:
        return jsonify({"message": "Error getting users"}), 500

#Adding a user to the database
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


#Returning a list of all the venues
@app.route("/venues", methods=['GET'])
def get_venues():
    try:
        query = db.session.execute('SELECT * FROM venues')
        results = query.fetchall()  # returns a list
        results_dicts = []
        for r in results:
            venue_dict = dict(r)
            venue_dict['open_time'] = utilities.convert_timedelta_to_string(venue_dict['open_time'], '%H:%M:%S')
            venue_dict['close_time'] = utilities.convert_timedelta_to_string(venue_dict['close_time'], '%H:%M:%S')
            results_dicts.append(venue_dict)
        return jsonify(results_dicts), 200
    except Exception as e:
        return jsonify({"message": "Error getting list of venues "}), 500

#  Creating a venue
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

#
@app.route("/<venueId>/events", methods=['GET'])
def get_events(venueId):
    try:
        day = request.args.get('date')
        time = request.args.get('date')
        events = []
        events_dict=[]
        if time != None:
            query = db.session.execute("SELECT e.*, v.name as venue_name, count(distinct p.participant_id) +sum(p.num_guests) as total FROM events e LEFT JOIN venues v ON v.venue_id = e.venue_id LEFT JOIN participants p on p.event_id = e.event_id WHERE e.start_time :time AND e.event_day : day and e.venue_id : venueId",
            {'time': time, 'day': day, 'venueId': venueId})
            events = query.fetchall()
        else:
            query = db.session.execute("SELECT e.*, v.name as venue_name, count(distinct p.participant_id) +sum(p.num_guests) as total FROM events e LEFT JOIN venues v ON v.venue_id = e.venue_id LEFT JOIN participants p on p.event_id = e.event_id WHERE e.event_day : day and e.venue_id : venueId GROUP BY e.event_id",
            {'day': day, 'venueId': venueId})
            events = query.fetchall()

        if (len(events) > 0 and events[0]['event_id'] != None):
            events_dict = [{'event_id': e['event_id'],
                        'venue': e['venue_name'],
                        'starts': e['start_time'],
                        'name': e['name'],
                        'max_players': e['max_players'],
                        'total': e['total']}
                       for e in events]
        return jsonify(''), 200
    except Exception as e:
        return jsonify({"message:" "Error getting event"}), 500


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
