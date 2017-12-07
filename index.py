import json
import datetime
import pymysql
import logging
import rds_config
import aws_config
import boto3
import collections
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cnx = None
cursor = None


# Create a sql database connection
def init_db_connection():
    host_name = rds_config.host_name
    db_username = rds_config.db_username
    db_password = rds_config.db_password
    db_name = rds_config.db_name
    try:
        global cnx
        global cursor
        cnx = pymysql.connect(host=host_name, user=db_username, password=db_password,
                              db=db_name, autocommit=True)
        cursor = cnx.cursor()
        print("db connection established")
        return
    except:
        return generate_error_response(500,
                                       "Database connection failed, please try again"
                                       "Database connection failed")


def init_boto3_client():
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
    table_name = 'Groups'
    init_boto3_client()

    query_string_parameters = event["queryStringParameters"]
    if query_string_parameters is None:
        return generate_error_response(404, 'Missing query_string_parameters')

    if 'userName' not in query_string_parameters:
        return generate_error_response(400, 'Missing \'userName\' key in request body')
    user_name = query_string_parameters['userName']

    if event['httpMethod'] == "GET":
        response = boto_client.admin_list_groups_for_user(
                Username=user_name,
                UserPoolId=aws_config.UserPoolId,
                Limit=60
            )
        if len(response['Groups']) != 0:
            group_name = response['Groups'][0]['GroupName']
        else:
            group_name = None
        data = { "groupName": group_name}
        return generate_success_response(json.dumps(data))

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

    # if body['operation'] == 'create':
    #    # create a new group
    #    cursor = database_connect()
    return generate_success_response(json.loads(response))


def task_handler(event, context):
    init_db_connection()

    table_name = 'Tasks'

    query_string_parameters = event["queryStringParameters"]
    if query_string_parameters is None:
        return generate_error_response(400, 'Missing query_string_parameters')

    if event['httpMethod'] == "GET":
        if 'groupName' not in query_string_parameters:
            return generate_error_response(400, 'Missing \'groupName\' key in request body')
        group_name = query_string_parameters['groupName']

        sql = 'SELECT groupName, taskTitle, taskContent, taskDuration, taskUser, taskSolved, taskID, lastRotated FROM %s WHERE groupName =\'%s\'' % (
            table_name, group_name)
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
            d['taskID'] = row[6]
            d['lastRotated'] = row[7].strftime('%Y-%m-%d %H:%M:%S')
            row_array_list.append(d)

        data = json.dumps(row_array_list)
    elif event['httpMethod'] == "POST":
        if 'operation' not in query_string_parameters:
            return generate_error_response(400, 'Missing \'operation\' key in request body')
        operation = query_string_parameters['operation']

        task = json.loads(event['body'])

        if operation == 'add':
            insert_time = time.strftime('%Y-%m-%d %H:%M:%S')
            sql = 'INSERT INTO %s (groupName, taskTitle, taskContent, taskDuration, taskUser, taskSolved, lastRotated) ' \
                  'VALUES (\'%s\',\'%s\',\'%s\',%s,null,%s, \'%s\')' % (
                      table_name, task['groupName'], task['taskTitle'], task['taskContent'], task['taskDuration'],
                      task['taskSolved'], insert_time)

            print(sql)
            cursor.execute(sql)
            rows = cursor.fetchall()

            sql = 'SELECT taskID from %s where groupName = \'%s\' and lastRotated = \'%s\'' % (
            table_name, task['groupName'], insert_time)
            cursor.execute(sql)
            rows = cursor.fetchall()

            data = json.dumps({"taskID": rows[0][0]})

        if operation == 'removeTask':
            data = {
                'unknown': 'unknown'
            }
            pass

    return generate_success_response(data)


def handler(event, context):
    print(json.dumps(event, sort_keys=True))
    print(context)

    resource_path = event['path']

    if resource_path == '/group':
        return group_handler(event, context)
    elif resource_path == '/task':
        return task_handler(event, context)

    return generate_error_response(404, 'Unsupported path')


def generate_success_response(data):
    global cnx
    if cnx is not None:
        cursor.close()
        cnx.close()
        cnx = None

    return {
        'statusCode': 200,
        'body': data,
        'headers': {'Content-Type': 'application/json'}
    }
