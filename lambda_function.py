"""
This sample demonstrates a simple skill built with the Amazon Alexa Skills Kit.
The Intent Schema, Custom Slots, and Sample Utterances for this skill, as well
as testing instructions are located at http://amzn.to/1LzFrj6

For additional samples, visit the Alexa Skills Kit Getting Started guide at
http://amzn.to/1LGWsLG
"""

from __future__ import print_function
import logging
import urllib2
import json
import pymysql
import sys

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# --------------- Helpers that build all of the responses ----------------------



def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }

def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Welcome to Computer Music Control. " \
                    "Please make sure your music player " \
                    "and companion app are running on your computer. " \
                    "You can ask me to control your computer to play or pause music, change songs. " \
                    "Please tell me what to do."
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = ""
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "OK"
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))



def set_color_in_session(intent, session):
    """ Sets the color in the session and prepares the speech to reply to the
    user.
    """

    card_title = intent['name']
    session_attributes = {}
    should_end_session = False

    if 'Color' in intent['slots']:
        favorite_color = intent['slots']['Color']['value']
        session_attributes = create_favorite_color_attributes(favorite_color)
        speech_output = "I now know your favorite color is " + \
                        favorite_color + \
                        ". You can ask me your favorite color by saying, " \
                        "what's my favorite color?"
        reprompt_text = "You can ask me your favorite color by saying, " \
                        "what's my favorite color?"
    else:
        speech_output = "I'm not sure what your favorite color is. " \
                        "Please try again."
        reprompt_text = "I'm not sure what your favorite color is. " \
                        "You can tell me your favorite color by saying, " \
                        "my favorite color is red."
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def get_color_from_session(intent, session):
    session_attributes = {}
    reprompt_text = None

    if session.get('attributes', {}) and "favoriteColor" in session.get('attributes', {}):
        favorite_color = session['attributes']['favoriteColor']
        speech_output = "Your favorite color is " + favorite_color + \
                        ". Goodbye."
        should_end_session = True
    else:
        speech_output = "I'm not sure what your favorite color is. " \
                        "You can say, my favorite color is red."
        should_end_session = False

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']
    print("Intent: " + intent_name)

    if intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent":
        return handle_session_end_request()

    access_token = session["user"]["accessToken"]
    uid = get_user_id(access_token)
    if uid == "":
        return errorHandle("Access token error", "access token incorrect, please try again", "")

    ####################################
    db_name = 'alexa'
    table_name = 'userinfo'
    host_name = 'alexadb.yishen.org'
    db_user_name = 'webAccess'
    db_password = 'G32xsj!klXex&8sl45'
    ####################################

    try:
        cnx = pymysql.connect(host=host_name, user=db_user_name, password=db_password,
                              db=db_name)
        cursor = cnx.cursor()
        print("connection success")
        sql = "SELECT * FROM %s WHERE uid = '%s'" % (table_name, uid)
        cursor.execute(sql)

    except:
        return errorHandle(
            "Database connection failed, please try again",
            "Database connection failed", "")

    if cursor.rowcount == 0:
        return error_link_account("Please download and run the client software on your computer to complete"
                                  " account linking and pairing."
                                  " You can find the download link in the skill's description part.")

    control_type = 0
    control_target = 1
    control_value = 0

    # special string param, maybe for future use?
    control_value2 = ""
    action_title = ""
    # Dispatch to your skill's intent handlers
    if intent_name == "AMAZON.ResumeIntent":
        control_type = 100
        action_title = "Start the music"
    elif intent_name == "AMAZON.PauseIntent":
        control_type = 101
        action_title = "Pause the music"
    elif intent_name == "AMAZON.StopIntent":
        control_type = 102
        action_title = "Stop the music"
    elif intent_name == "AMAZON.NextIntent":
        control_type = 103
        action_title = "Next song"
    elif intent_name == "AMAZON.PreviousIntent":
        control_type = 104
        action_title = "Previous song"
    elif intent_name == "VolumeUp":
        control_type = 107
        action_title = "Increase volume"
    elif intent_name == "VolumeDown":
        control_type = 108
        action_title = "Decrease volume"
    elif intent_name == "TurnOff" or intent_name == "TurnOn":
        control_type = 2 if (intent_name == "TurnOff") else 1
        if not intent_request['intent'].get('slots', {}):
            return developer_error("No intents found")
        if not intent_request['intent']['slots']['device'].get('value',{}):
            return errorHandle("Sorry, I didn't hear you clearly, please try again",
                               "Please try again", "")
        intent_slot_value = intent_request['intent']['slots']['device']['value']
        print("Turn off " + intent_slot_value)
        if intent_slot_value == "computer":
            control_target = 4
            if intent_name == "TurnOn":
                return errorHandle("Sorry, Turning on computer is not supported yet", "Turn on is unsupported", "")
        elif intent_slot_value == "monitor" or intent_slot_value == "computer monitor":
            control_target = 2
        elif intent_slot_value == "receiver":
            control_target = 3
        elif intent_slot_value == "everything":
            control_target = 10
        else:
            return errorHandle("Sorry, I don't know how to control " + intent_slot_value + " yet.",
                               "Unsupported device", "")

    elif intent_name == "AMAZON.YesIntent":
        if session.get('attributes', {}) and "confirm_type" in session.get('attributes', {}):
            session['attributes']['confirm_valid'] = True
            control_type = session['attributes']['confirm_type']
            control_value = session['attributes']['confirm_value']
            control_target = session['attributes']['confirm_target']
        else:
            # print(session.get('attributes', {}))
            # print("confirm_type" in session.get('attributes', {}))
            # control_target = -1  # don't understand
            return errorHandle("Sorry, I don't understand that.",
                               "Could not understand", "")
    elif intent_name == "AMAZON.NoIntent":
        control_target = 0
        
    else:
        return developer_error("Unrecognized intent")

    return handle_control(intent, session, cnx, cursor, uid, control_type, control_target, control_value, control_value2, action_title)


def handle_control(intent, session, cnx, cursor, uid, control_type, control_target, control_value, control_value2, action_title):
    print('Control Target: {} Control Type: {}'.format(control_target, control_type))

    session_attributes = {}
    speech_output = ""
    reprompt_text = None

    send_sql = True
    should_end_session = True

    if control_target == 0:
        # User responded no
        speech_output = "Never mind."
        send_sql = False

    elif control_target == 4:
        # Control Computer Power (off)

        if session.get('attributes', {}) and "confirm_type" in session.get('attributes', {}):
            if session['attributes']['confirm_valid']:
                print("Shutdown success!")
            else:
                # send_sql = False
                return developer_error("This should not happen in Computer Power off")
        else:
            # First time in this turn off process
            session_attributes = {'confirm_type': control_type,
                                  'confirm_value': control_value,
                                  'confirm_valid': False,
                                  'confirm_target': control_target}
            send_sql = False
            speech_output = "Please Confirm for turning off your computer"
            reprompt_text = speech_output
            should_end_session = False
            #print ("First reprompt for shut down")

    if send_sql:
        sql = "UPDATE alexa.userinfo SET actionType = %d, actionValue = %d, deviceId = %d, lastAccess = CURDATE() WHERE uid = '%s'" % (
        control_type, control_value, control_target, uid)
        cursor.execute(sql)

        if speech_output == "":
            if control_type == 100:
                speech_output = "Enjoy"
            else:
                speech_output = "OK"

    cnx.commit()
    cnx.close()
    return build_response(session_attributes, build_speechlet_response(
        action_title, speech_output, reprompt_text, should_end_session))


def errorHandle(speech_output, error_title, error_message):
    print("ERROR: {}".format(error_title))
    session_attributes = {}
    
    should_end_session = True
    reprompt_text = ""
    
    return build_response(session_attributes, build_speechlet_response(
                error_title, speech_output, reprompt_text, should_end_session))


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    # print("on_session_ended requestId=" + session_ended_request['requestId'] +
    #      ", sessionId=" + session['sessionId'])
    # add cleanup logic here


def get_user_id(access_token):
    try:
        req = urllib2.Request('https://api.amazon.com/user/profile')
        req.add_header('Authorization', 'bearer ' + access_token)
        response = urllib2.urlopen(req)
        json_data = json.load(response)
        return json_data['user_id']
    except:
        return ""


def error_link_account(speech_output):
    print("Account not linked")
    session_attributes = {}
    should_end_session = True
    reprompt_text = ""
    title = ""
    response = build_response(session_attributes, build_speechlet_response(
        title, speech_output, reprompt_text, should_end_session))
    response['response']['card'] = {'type': 'LinkAccount'}
    return response


def developer_error(error_name):
    print("Developer ERROR: " + error_name)
    session_attributes = {}
    should_end_session = True
    speech_output = "Sorry, the developer made an error called " + error_name + ". Please Try again"
    reprompt_text = ""
    title = ""
    return build_response(session_attributes, build_speechlet_response(
        title, speech_output, reprompt_text, should_end_session))

# --------------- Main handler ------------------


def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """

#################################

    application_id_1 = 'amzn1.ask.skill.79870062-6be6-463a-9a9a-6b480eef9008'
    application_id_2 = 'amzn1.ask.skill.751cf9a6-5192-495d-9bf2-03d99c4db908'

#################################

    if (event['session']['application']['applicationId'] != application_id_1 and
            event['session']['application']['applicationId'] != application_id_2 ):
        return developer_error("Application ID mismatch")

    # check the accessToken
    if 'accessToken' not in event["session"]["user"]:
        return error_link_account('Sorry, account linking is required to use this skill. '
                                  'Check more in your alexa app.')

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
