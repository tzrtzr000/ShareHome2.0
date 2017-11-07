import json
import datetime
import pymysql


# Create a sql database connection
def database_connect():
    ####################################
    db_name = 'shareHome'
    host_name = 'alexadb.yishen.org'
    db_user_name = 'webAccess'
    db_password = 'G32xsj!klXex&8sl45'
    ####################################

    try:
        cnx = pymysql.connect(host=host_name, user=db_user_name, password=db_password,
                              db=db_name)
        cursor = cnx.cursor()
        print("db connection established")
        return cursor

    except:
        return generate_error_response(500,
                                       "Database connection failed, please try again"
                                       "Database connection failed")


def generate_error_response(error_code, body):
    return {'statusCode': error_code,
            'body': body,
            'headers': {'Content-Type': 'application/json'}
            }


def group_handler(event, context):
    body = event['body']
    print('In Group handler, request body is ' + body)
    return generate_success_response(body)


def handler(event, context):
    print(json.dumps(event, sort_keys=True))
    print(context)

    resource_path = event['path']

    if resource_path == '/group':
        return group_handler(event, context)

    # cursor = database_connect()

    # table_name = 'Groups'
    # sql = "SELECT * FROM %s" % (table_name)
    # cursor.execute(sql)
    # if cursor.rowcount == 0:
    #     return generate_error_response(201, "Please download and run the client software on your computer to complete"
    #                                         " account linking and pairing."
    #                                         " You can find the download link in the skill's description part.")
    #
    # cursor_result = [item['id'] for item in cursor.fetchall()]
    # data = {
    #     'output': json.dumps(event),
    #     'timestamp': datetime.datetime.utcnow().isoformat()
    # }

    return generate_error_response(404, 'Unsupported path')


def generate_success_response(data):
    return {
        'statusCode': 200,
        'body': json.dumps(data),
        'headers': {'Content-Type': 'application/json'}
    }
