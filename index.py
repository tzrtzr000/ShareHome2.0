import json
import datetime
import pymysql
import logging
import rds_config
import aws_config
import boto3
import collections


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Create a sql database connection
def database_connect():
    host_name = rds_config.host_name
    db_username = rds_config.db_username
    db_password = rds_config.db_password
    db_name = rds_config.db_name
    try:
        global cnx
        global cursor
        cnx = pymysql.connect(host=host_name, user=db_username, password=db_password,
                              db=db_name)
        cursor = cnx.cursor()
        print("db connection established")
        return cursor
    except:
        return generate_error_response(500,
                                       "Database connection failed, please try again"
                                       "Database connection failed")
def establish_boto3_client():
    global boto_client
    boto_client = boto3.client(
        'cognito-idp',
        aws_access_key_id=aws_config.aws_access_key_id,
        aws_secret_access_key=aws_config.aws_secret_access_key
    )
    return


def generate_error_response(error_code, body):
    return {'statusCode': error_code,
            'body': body,
            'headers': {'Content-Type': 'application/json'}
            }


def group_handler(event, context):
    body = event['body']
    print('In Group handler, request body is ' + body)
    json_body = json.loads(event['body'])

    if 'operation' not in json_body:
        return generate_error_response(400, 'Missing \'operation\' key in request body')
    
    establish_boto3_client()
    # Now we have the client
    operation = json_body['operation']

    if operation == 'createGroup':
        pass
    elif operation == 'addUser':
        pass
    elif operation == 'removeUser':
        pass
    response = boto_client.list_users(
        UserPoolId=aws_config.UserPoolId
    )


    #if body['operation'] == 'create':
    #    # create a new group
    #    cursor = database_connect()
    return generate_success_response(json.loads(response))


def task_handler(event, context):
    queryStringParameters = event["queryStringParameters"]
    #print('In task handler, query parameter is ' + queryStringParameters)

    if 'operation' not in queryStringParameters:
        return generate_error_response(400, 'Missing \'operation\' key in request body')

    # establish_boto3_client()
    # Now we have the client
    operation = queryStringParameters['operation']

    database_connect()

    table_name = 'Tasks'
    group_name = queryStringParameters['groupName']

    # sql = 'SELECT * FROM %s WHERE groupName =\'%s\'' % (table_name, group_name)
    # print(sql)
    # cursor.execute(sql)
    # rows = cursor.fetchall()
    #
    # data = {
    #     'result': json.dumps(rows),
    #     'timestamp': datetime.datetime.utcnow().isoformat()
    # }
    if event['httpMethod'] == "GET":
        sql = 'SELECT groupName, taskTitle, taskContent, taskDuration, taskUser, taskSolved FROM %s WHERE groupName =\'%s\'' % (
        'Tasks', 'lambdaTestGroup')
        print(sql)
        cursor.execute(sql)
        rows = cursor.fetchall()
        row_array_list = []
        for row in rows:
            d = collections.OrderedDict()
            d['groupName'] = row[0]
            d['taskTitle'] = row[1]
            d['taskContent'] = row[2]
            d['taskDuration'] = row[3]
            d['taskUser'] = row[4]
            d['taskSolved'] = True if row[5] else False
            row_array_list.append(d)

        data = json.dumps(row_array_list)


    elif operation == 'addTask':
        sql = 'INSERT INTO Tasks (groupName, taskTitle, taskContent, taskDuration, taskUsers, taskSolved)' % (table_name, group_name)
        print(sql)
        cursor.execute(sql)
        rows = cursor.fetchall()

        data = {
            'result': json.dumps(rows),
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
    elif operation == 'removeTask':
        pass
    elif operation == 'removeTask':
        pass

    # if body['operation'] == 'create':
    #    # create a new group
    #    cursor = database_connect()
    return generate_success_response(data)


def handler(event, context):
    print(json.dumps(event, sort_keys=True))
    print(context)

    resource_path = event['path']

    if resource_path == '/group':
        return group_handler(event, context)
    elif resource_path == '/task':
        return task_handler(event, context)

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
        'body': data,
        'headers': {'Content-Type': 'application/json'}
    }
