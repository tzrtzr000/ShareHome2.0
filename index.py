import json
import datetime
import pymysql
import rds_config


# Create a sql database connection
def database_connect():
    try:
        cnx = pymysql.connect(host=host_name, user=db_username, password=db_password,
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
    if 'operation' not in body:
        return generate_error_response(400, 'Missing \'operation\' key in request body')
    
    if body['operation'] == 'create':
        # create a new group
        
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
