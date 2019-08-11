import config
import auth
import datetime
import utilities

from flask import current_app, Flask, redirect, url_for, jsonify, request, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_cors import CORS


app = Flask(__name__) #creating an instance of the Flask class and assigning it to the app variable
CORS(app)  # asking to get data back
app.config.from_object(config)  # tells flask the project ID and cloud SQL details
db = SQLAlchemy(app)  # allows us to use SQL queries


@app.route("/", methods=['GET'])
def index():
    """
    Index route, returns general information about the flask app
    :return:
    """
    return jsonify({"Events Platform v1": "APAD Project - Sasha Opela & Sam Bell"})


def email_pass_validation(email, password):
    """
    Makes sure email and password from user are correct
    :param email:
    :param password:
    :return: user dict
    """
    email = email.lower()
    #Select all from users when email entered matches email in table
    query = db.session.execute("SELECT * FROM users WHERE lower(email) = :email", {'email': email})
    user = query.fetchone() #fetching one user
    #if there is no such user, abort
    if user is None:
        abort(401, 'Incorrect login information')
        #else set user dict
    else:
        user = dict(user)
        #if user password and email matches what is in table return user
    if user['password'] == password and user['email'] == email:
        return user
        #else, abort
    else:
        abort(401, 'Incorrect login information')


def store_token(user, token):
    """
    Stores a new user token in the user token label
    :param user: dict of user from users table
    :param token: encoded token
    :return:
    """
    #when the token expires
    expires = datetime.date.today() + datetime.timedelta(days=1)
    #storing user id, token, expiration in user_tokens table
    db.session.execute(
        "INSERT INTO user_tokens (user_id, token, expires) VALUES (:user_id, :token, :expires);",
        {'user_id': user['user_id'], 'token': token, 'expires': expires})
    db.session.commit()


def validate_token(header):
    """
    validates that the token exists and isn't expired
    :param header:
    :return:
    """
#  split where there is a space in the String - returns a list,( index 0 is Bearer),only return index 1 the token
    query = db.session.execute("SELECT ut.* FROM user_tokens ut WHERE ut.token = :token ORDER BY ut.date_created DESC LIMIT 1", {'token': header.split(' ')[1]})
    token_dict = query.fetchone() #fetching one token
    #if there is no token, abort
    if token_dict is None:
        abort(401, 'Token Not Exist')
        #else set token dict
    else:
        token_dict = dict(token_dict)
        #if the token expiration date is less than today's date, it has expired, abort
    if token_dict['expires'] < datetime.date.today():
        raise Exception('Expired token')
    decoded = auth.decode_token(header)
    return decoded  # user dict

#If user is a admin, they have admin privileges
def is_admin(user):
    if user['administrator'] == 1:
        return True
    else:
        raise Exception('Not an admin')


@app.route("/<venueId>/availability", methods=['GET'])
def get_venue_availability(venueId):
    try:
        # venueId is from the URL
        # when a query param is missing, it's None
        # when a query param is just var=, it's an empty string
        validate_token(request.headers.get('Authorization'))
        day = request.args.get('day')

        #day is needed for query
        if day == '' or day is None:
            abort(400, 'day needed')
        #Select all from events where day and venue_id match
        events_query = db.session.execute("SELECT e.* FROM events e WHERE e.event_day = :day and e.venue_id = :venue_id", {'day': day, 'venue_id': venueId})
        events = events_query.fetchall() #fetch all events
        #Select all from venues where venue_id matches
        venue_query = db.session.execute("SELECT v.* FROM venues v WHERE v.venue_id = :venueId", {'venueId': venueId})
        venue = dict(venue_query.fetchone()) #fetch one venue

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
            slot_reserved = False

            for e in events:
                event_begins = datetime.datetime.strptime(utilities.convert_timedelta_to_string(e['start_time'], '%H:%M:%S'), '%H:%M:%S')
                if (event_begins == slot_begins):
                    # time_dict['reserved'] = True
                    slot_reserved = True
                else:
                    pass
            if slot_reserved is False:
                slots.append(time_dict)

            opens += datetime.timedelta(hours=1)
        return jsonify(slots), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route("/login", methods=['POST'])
def create_token():
    """
    validates email and password information from the user and creates a JWT/token
    :return: one dict containing the token and a (sub) user dict
    """
    try:
        content = request.json #makes dictionary out of json request
        user = email_pass_validation(content['email'], content['password']) #calling validation to make sure email and password will work
        token = auth.create_token(user) 
        store_token(user, token)
        #https://github.com/jpadilla/pyjwt/issues/391 why to do UTF-8 decode here
        #turns the byte token into the correct String version so it can be used in the jsonify
        response_dict = {'token': token.decode('UTF-8'), 'user': user}
        return jsonify(response_dict), 201
    except Exception as e:
        return jsonify({"message": "error logging in"}), 401

@app.route("/authenticate", methods=['GET'])
def get_user():
    try:
        user = validate_token(request.headers.get('Authorization'))
        return jsonify(user), 200
    except Exception as e:
        return jsonify({"message":str(e)}), 401

#Returning a list of users from the database
@app.route("/users", methods=['GET'])
def get_users():
    try:
        validate_token(request.headers.get('Authorization'))
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
        #validate token
        user = validate_token(request.headers.get('Authorization'))
        #if user is not admin, they do not have persmission to add user
        is_admin(user)

        content = request.json # turns the json request body into a dict :D
        #insert name, email, password, and if user is admin or not into users table
        db.session.execute('''INSERT INTO users
                            (name, email, password, administrator)
                            VALUES
                            (:name, :email, :password, :administrator);''',
                            {'name': content['name'], 'email': content['email'], 'password': content['password'], 'administrator': content['administrator']})
        db.session.commit()
        return jsonify({"message": "User Added"}), 201  # returns a 201 status code with a message
    except Exception as e:
        return jsonify({"message": "Error Adding New User"}), 500  # returns a 500 status code with a message


#Returning a list of all the venues
@app.route("/venues", methods=['GET'])
def get_venues():
    try:
        validate_token(request.headers.get('Authorization'))
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
        user = validate_token(request.headers.get('Authorization'))
        is_admin(user)
        content = request.json
        db.session.execute("INSERT INTO venues (name, address, activities) VALUES (:name, :address, :activities)",
                          {'name': content['name'], 'address': content['address'], 'activities': content['activities']})
        db.session.commit()
        return jsonify({"message": "Venue Added"}), 201  # returns a 201 status code with a message
    except Exception as e:
        return jsonify({"message": "Error adding venue"}), 500


@app.route("/events", methods=['GET'])
#Returning events
def get_events():
    try:
        validate_token(request.headers.get('Authorization'))
        venue_id = request.args.get('venueId')
        day = request.args.get('date')
        time = request.args.get('time')
        events = []
        events_dict=[]
              #day, time, venueId provided
        if time is not None and venue_id is not None:
            query = db.session.execute('''SELECT 
                                          e.*, 
                                          v.name as venue_name, 
                                          count(distinct p.participant_id) +sum(p.num_guests) as current_num_players 
                                          FROM events e 
                                          LEFT JOIN venues v ON v.venue_id = e.venue_id 
                                          LEFT JOIN participants p on p.event_id = e.event_id 
                                          WHERE e.start_time = :time AND e.event_day = :day and e.venue_id = :venueId
                                          GROUP BY e.event_id''',
                                        {'time': time, 'day': day, 'venueId': venue_id})
            events = query.fetchall()
            #day, time provided
        elif time is not None:
            query = db.session.execute('''SELECT e.*,
                                          v.name as venue_name, 
                                          count(distinct p.participant_id) +sum(p.num_guests) as current_num_players 
                                          FROM events e 
                                          LEFT JOIN venues v ON v.venue_id = e.venue_id 
                                          LEFT JOIN participants p on p.event_id = e.event_id 
                                          WHERE e.event_day = :day and e.start_time = :time
                                          GROUP BY e.event_id''',
            {'day': day, 'time': time})
            events = query.fetchall()
            #day, venueid provided
        elif venue_id is not None:
            query = db.session.execute('''SELECT e.*,
                                              v.name as venue_name, 
                                              count(distinct p.participant_id) +sum(p.num_guests) as current_num_players 
                                              FROM events e 
                                              LEFT JOIN venues v ON v.venue_id = e.venue_id 
                                              LEFT JOIN participants p on p.event_id = e.event_id 
                                              WHERE e.event_day = :day and e.venue_id = :venue_id
                                              GROUP BY e.event_id''',
                                       {'day': day, 'venue_id': venue_id})
            events = query.fetchall()
            #day provided
        else:
            query = db.session.execute('''SELECT e.*,
                                              v.name as venue_name, 
                                              count(distinct p.participant_id) +sum(p.num_guests) as current_num_players 
                                              FROM events e 
                                              LEFT JOIN venues v ON v.venue_id = e.venue_id 
                                              LEFT JOIN participants p on p.event_id = e.event_id 
                                              WHERE e.event_day = :day
                                              GROUP BY e.event_id''',
                                       {'day': day})
            events = query.fetchall()

        if events is not None:
            events_dict = [{'event_id': e['event_id'],
                            'venue_name': e['venue_name'],
                            'event_day': e['event_day'].strftime('%m/%d/%Y'),
                            'start_time': utilities.convert_timedelta_to_string(e['start_time'], '%H:%M:%S'),
                            'name': e['name'],
                            'max_players': e['max_players'],
                            'created_by': e['created_by'],
                            'current_num_players': int(str(e['current_num_players']))}
                           for e in events]

        return jsonify(events_dict), 200
    except Exception as e:
        return jsonify({"message:" "Error getting event"}), 500


@app.route("/events", methods=['POST'])
def create_event():
    try:
        content = request.json
        venue_id = content['venue_id']
        start_time = content['start_time']
        day = content['event_day']
        user_id = content['created_by']
        event_name = content['name']
        max_players = content['max_players']
        participant_comment = content ['participant_comment']
        num_guests = content['num_guests']

        event_day = datetime.datetime.strptime(day, "%Y-%m-%d")
        #preventing users from creating an event on a past date
        if event_day.date() < datetime.datetime.today().date():
            raise Exception('Can\'t create past events')
        #select all from venues where venueid matches
        venue_query = db.session.execute('''SELECT * 
                                            FROM venues 
                                            WHERE venue_id = :venue_id''',
                                         {'venue_id': venue_id})
        venue = venue_query.fetchone()

        event_start_time = datetime.datetime.strptime(start_time, '%H:%M:%S')
        venue_close_time = datetime.datetime.strptime(utilities.convert_timedelta_to_string(venue['close_time'], '%H:%M:%S'), '%H:%M:%S')
        venue_open_time = datetime.datetime.strptime(utilities.convert_timedelta_to_string(venue['open_time'], '%H:%M:%S'), '%H:%M:%S')
        #making sure event is being held during venue hours
        if event_start_time < venue_open_time or event_start_time >= venue_close_time:
            raise Exception("Your event is outside the venue hours")
        #select all from events where venueid, event day, and start time match
        event_query = db.session.execute('''SELECT 
                                            * FROM events 
                                            WHERE venue_id = :venue_id 
                                            and event_day = :event_day 
                                            and start_time = :start_time''',
                                         {'venue_id': venue_id, 'event_day': event_day.strftime('%Y-%m-%d'), 'start_time': start_time})
        event = event_query.fetchone()
        #making sure there is not an event already at that time
        if event is not None:
            raise Exception("An event already exists for that time.")

        # create the new event
        new_event_query = db.session.execute('''INSERT INTO events
                                                (created_by, event_day, start_time, venue_id, name, max_players) 
                                                VALUES
                                                (:user_id, :event_day, :start_time, :venue_id, :event_name, :max_players)''',
                                             {'user_id': user_id, 'event_day': event_day.strftime('%Y-%m-%d'),
                                              'start_time': start_time, 'venue_id': venue_id,
                                              'event_name': event_name, 'max_players': max_players})
        db.session.commit()
        new_event_id = new_event_query.lastrowid
        add_user_to_event(new_event_id, user_id, participant_comment, num_guests) #calling add user to event for new event
        return jsonify(''), 201
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/events/<event_id>", methods=['DELETE'])
def remove_event(event_id):
    try:
        user = validate_token(request.headers.get('Authorization'))
        #select all from events where event id matches
        event_query = db.session.execute('''SELECT * FROM events WHERE event_id = :event_id''', {'event_id': event_id})
        event = dict(event_query.fetchone()) #fetch the event
        #user must have created event or be an admin to delete event
        if user['user_id'] == event['created_by'] or is_admin(user):
            db.session.execute('''DELETE FROM events WHERE event_id = :event_id''', {'event_id': event_id}) #delete the event
            db.session.commit()
            db.session.execute('''DELETE FROM participants WHERE event_id = :event_id''', {'event_id': event_id}) #delete the participants from event
            db.session.commit()
        else:
            raise Exception('You do not have permission to do that.')
        return jsonify({'message': 'deleted'}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route("/venues/<venue_id>", methods =['DELETE'])
#remove the event
def remove_venue(venue_id):
    try:
        user = validate_token(request.headers.get('Authorization'))
        #select event id from events where venueid matches
        events_at_venue = db.session.execute('''SELECT event_id FROM events where venue_id = :venue_id''', {'venue_id':venue_id})
        events = events_at_venue.fetchall() #fetch all events at venue
        #user must be admin
        is_admin(user)
        for i in events:
            event = dict(i)
            #deleting participants out of events happening at the venue
            db.session.execute('''DELETE FROM participants WHERE event_id =:event_id''', {'event_id': event['event_id']})
            db.session.commit()
            #deleting the events that are happening at the venue
            db.session.execute('''DELETE FROM events WHERE venue_id =:venue_id''', {'venue_id': venue_id})
            db.session.commit()
            #deleting the venue
            db.session.execute('''DELETE FROM venues WHERE venue_id =:venue_id''', {'venue_id': venue_id})
            db.session.commit()
        return jsonify({'message: ''deleted'}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route("/users/<user_id>", methods =['DELETE'])
def remove_user(user_id):
    """
    This function deletes a user, their events, and removes them as a participant in the events they've joined
    :param user_id:
    :return:
    """
    try:
        user = validate_token(request.headers.get('Authorization'))
        #select event id from events where created_by matches
        events_at_venue = db.session.execute('''SELECT event_id FROM events where created_by = :created_by''', {'created_by':user_id})
        events = events_at_venue.fetchall() #fetch all events
        #user must be admin
        is_admin(user)
        for i in events:
            event = dict(i)
            #deleting participants out of events that were created by the user or the user is a participant
            db.session.execute('''DELETE FROM participants WHERE event_id =:event_id or user_id = :user_id''', {'event_id': event['event_id'], 'user_id': user_id})
            db.session.commit()
            #deleting the events that were created by the user
            db.session.execute('''DELETE FROM events WHERE created_by =:created_by''', {'created_by': user_id})
            db.session.commit()
            #deleting the user
            db.session.execute('''DELETE FROM users WHERE user_id =:user_id''', {'user_id': user_id})
            db.session.commit()
        return jsonify({'message: ''deleted'}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route("/register", methods=['POST'])
#if someone wants to register to be a user
def public_registration():
    try:
        content = request.json
        name = content['name']
        password = content['password']
        email = content['email']
        #select email
        email_check_query = db.session.execute('''SELECT * FROM users WHERE lower(email) = lower(:email)''', {'email': email})
        #if email is already in use, raise exception
        if email_check_query.fetchone() is not None:
            raise Exception('Email already in use')
        #insert new user into users table
        db.session.execute('''INSERT INTO
                                users (name, password, email)
                                VALUES
                                (:name, :password, :email)''',
                           {'name': name, 'password': password, 'email': email})
        db.session.commit()
        return jsonify({"message": 'registered'}), 201
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/my-events", methods=['GET'])
#getting events a participant has signed up for
def get_my_events():
    try:
        user = validate_token(request.headers.get('Authorization'))
        #selecting all from events and venue name from participants, left join where event id matches, left join where venue id matches, where userid matches dict
        events_query = db.session.execute('''SELECT e.*, v.name as venue_name
                                            FROM participants p
                                            LEFT JOIN events e on e.event_id = p.event_id
                                            LEFT JOIN venues v on v.venue_id = e.venue_id
                                            WHERE p.user_id = :user_id
                                            ORDER BY e.event_day DESC''',
                                          {'user_id': user['user_id']})

        events = [{
            'event_id': e['event_id'],
            'name': e['name'],
            'created_by': e['created_by'],
            'event_day': datetime.datetime.strftime(e['event_day'], '%m/%d/%Y'),
            'start_time': utilities.convert_timedelta_to_string(e['start_time'], '%H:%M:%S'),
            'venue_name': e['venue_name'],
        } for e in events_query.fetchall()]

        return jsonify(events), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@app.route("/events/<event_id>/join", methods=['POST'])
#participant joining an event
def join_event(event_id):
    try:
        user = validate_token(request.headers.get('Authorization'))
        content = request.json
        num_guests = content['num_guests']
        participant_comment = content['participant_comment']
        user_id = content['user_id']
        #makes sure an admin account is being used to add a user to an event even if ids dont match
        if user_id != user['user_id']:
            is_admin(user)
           #selecting all from participants where eventid and user id match
        p_query = db.session.execute('''SELECT
                                        p*
                                        from participants p
                                        WHERE p.event_id = :event_id
                                        and p.user_id =:user_id''', {'event_id':event_id, 'user_id':user_id})
        participant = p_query.fetchone() #fetch the participant
        #if there is already a participant in event, raise an Exception
        if participant is not None:
            raise Exception('Already in game')
         #selecting the event
        query = db.session.execute('''SELECT e.*, 
                                      (COUNT(distinct p.user_id) + SUM(p.num_guests)) AS num_players 
                                       FROM events e 
                                       LEFT JOIN participants p on p.event_id = e.event_id 
                                       WHERE e.event_id = :event_id''', {'event_id': event_id})
        event = dict(query.fetchone()) #Will return a tuple of Nones if event does not exist
        if event['event_id'] is None:
            raise Exception('Event doesn\'t exist')
        event['num_players']= int(str(event['num_players']))
        if event['max_players'] - event['num_players'] <= 1 + num_guests:
            raise Exception('Not enough space')
        add_user_to_event(event_id,user_id,participant_comment, num_guests) #call add user to event
        return jsonify({'message': 'added'}), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 500


def add_user_to_event(event_id,user_id,participant_comment,num_guests):
                          #inserting into participants
    db.session.execute('''INSERT INTO participants(event_id, user_id, comment, num_guests)
                            VALUES (:event_id, :user_id, :comment, :num_guests)''',
                       {'event_id':event_id, 'user_id':user_id,'comment':participant_comment, 'num_guests':num_guests})
    db.session.commit()



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
