import json
import datetime
import pymysql
import logging
import rds_config
import aws_config
import boto3
import collections
import time
from time import gmtime, strftime


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
    global boto_cognito_client, boto_pinpoint_client
    boto_cognito_client = boto3.client(
        'cognito-idp',
        aws_access_key_id=aws_config.aws_access_key_id,
        aws_secret_access_key=aws_config.aws_secret_access_key
    )
    boto_pinpoint_client = boto3.client(
        'pinpoint',
        region_name=aws_config.region,
        aws_access_key_id=aws_config.aws_access_key_id,
        aws_secret_access_key=aws_config.aws_secret_access_key
    )
    return


def generate_error_response(error_code, body):
    return {'statusCode': error_code,
            'body': body,
            'headers': {'Content-Type': 'application/json'}
            }


def boto_admin_list_groups_for_user(user_name):
    return boto_cognito_client.admin_list_groups_for_user(
        Username=user_name,
        UserPoolId=aws_config.UserPoolId,
        Limit=60
    )

# query string to dictionary
def qs_to_dict(qs):
    final_dict = dict()
    for item in qs.split("&"):
        final_dict[item.split("=")[0]] = item.split("=")[1]
    return final_dict


def group_handler(event, context):
    table_name = 'Groups'
    init_boto3_client()

    query_string_parameters = event["queryStringParameters"]
    if query_string_parameters is None:
        if event['body'] is not None:
            print("SDK just fucked up again")
            query_string_parameters = qs_to_dict(event['body'])
        else:
            return generate_error_response(404, 'Missing query_string_parameters')
    if 'operation' not in query_string_parameters:
        return generate_error_response(400, 'Missing \'operation\' key in query_string')
    operation = query_string_parameters['operation']

    if 'userName' not in query_string_parameters:
        return generate_error_response(400, 'Missing \'userName\' key in query_string')
    user_name = query_string_parameters['userName']

    if event['httpMethod'] == "GET":

        if operation == 'listMembers':
            response = boto_admin_list_groups_for_user(user_name)
            if len(response['Groups']) != 0:
                group_name = response['Groups'][0]['GroupName']
                response = boto_cognito_client.list_users_in_group(
                    UserPoolId=aws_config.UserPoolId,
                    GroupName=group_name,
                    Limit=60
                )
                return_list = [user['Username'] for user in response['Users']]
            else:
                return_list = []
            return generate_success_response(json.dumps(return_list))
        elif operation == 'getGroupName':
            response = boto_admin_list_groups_for_user(user_name)
            if len(response['Groups']) != 0:
                group_name = response['Groups'][0]['GroupName']
            else:
                group_name = None
            data = [group_name]
            return generate_success_response(json.dumps(data))
        else:
            return generate_error_response(404, "Not supported operation: " + operation)
    elif event['httpMethod'] == "POST":
        # Now we have the client

        if 'groupName' not in query_string_parameters:
            return generate_error_response(400, 'Missing \'groupName\' key in request body')
        group_name = query_string_parameters['groupName']

        if operation == 'add':
            # first check if user is already in a group
            response = boto_admin_list_groups_for_user(user_name)['Groups']
            for group in response:
                # user in a group already
                group_name = group['GroupName']
                boto_cognito_client.admin_remove_user_from_group(
                    UserPoolId=aws_config.UserPoolId,
                    Username=user_name,
                    GroupName=group_name
                )

                boto_cognito_client.admin_add_user_to_group(
                UserPoolId=aws_config.UserPoolId,
                Username=user_name,
                GroupName=group_name
            )
            # push notification
            push_notification(user_name, group_name, "User added", "User " + user_name +" has been added to group" + group_name)
        elif operation == 'create':
            boto_cognito_client.create_group(
                GroupName=group_name,
                UserPoolId=aws_config.UserPoolId
            )
            # Then add user to the group
            boto_add_user_to_only_one_group(user_name, group_name)

        return generate_success_response(json.dumps({"result": "success"}))


def push_notification (user_name, group_name, push_title, push_body):
    current_time = strftime('%Y-%m-%dT%H:%M:%S', gmtime())
    response = boto_pinpoint_client.create_campaign(
        ApplicationId=aws_config.pinpoint_application_id,
        WriteCampaignRequest={
            'Description': 'Campaign created by backend lambda',
            'IsPaused': False,
            'MessageConfiguration': {
                'GCMMessage': {
                    'Action': 'OPEN_APP',
                    'Body': push_body,
                    'SilentPush': False,
                    'Title': push_title,
                }
            },
            'Name': 'Lambda Campaign',
            'Schedule': {
                'Frequency': 'ONCE',
                'IsLocalTime': False,
                'StartTime': current_time
            },
            'SegmentId': 'a1a378598b1346c0bb199874181ff542',
            'SegmentVersion': 1
        }
    )


def boto_add_user_to_only_one_group(user_name, group_name):
    # first check if user is already in a group
    response = boto_admin_list_groups_for_user(user_name)['Groups']
    for group in response:
        # user in a group already
        old_group_name = group['GroupName']
        boto_cognito_client.admin_remove_user_from_group(
            UserPoolId=aws_config.UserPoolId,
            Username=user_name,
            GroupName=old_group_name
        )
        print("user " + user_name + " removed from group: " + group_name)

        boto_cognito_client.admin_add_user_to_group(
        UserPoolId=aws_config.UserPoolId,
        Username=user_name,
        GroupName=group_name
    )


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


def post_handler(event, context):
    init_db_connection()

    table_name = 'Posts'
    post_sample = {
        "groupName": "post_sample_group",
        "postTitle": "post_sample_title",
        "postContent": "post_sample_content",
        "postUrgent": False,
        "postID": 100
    }

    query_string_parameters = event["queryStringParameters"]
    if query_string_parameters is None:
        return generate_error_response(400, 'Missing query_string_parameters')

    #
    if event['httpMethod'] == "GET":
        if 'groupName' not in query_string_parameters:
            return generate_error_response(400, 'Missing \'groupName\' key in request body')
        group_name = query_string_parameters['groupName']

        select_cause = dict_to_sql("SELECT", table_name, post_sample)
        sql = '%s WHERE groupName =\'%s\'' % (select_cause, group_name)
        cursor.execute(sql)
        rows = cursor.fetchall()
        row_array_list = []
        for row in rows:
            d = collections.OrderedDict()
            d['groupName'] = row[0]
            d['postTitle'] = row[1]
            d['postContent'] = row[2]
            d['postUrgent'] = True if row[3] else False
            d['postID'] = row[4]
            row_array_list.append(d)
        data = json.dumps(row_array_list)
    elif event['httpMethod'] == "POST":
        if 'operation' not in query_string_parameters:
            return generate_error_response(400, 'Missing \'operation\' key in request body')
        operation = query_string_parameters['operation']

        post = json.loads(event['body'])

        if operation == 'add':
            if 'postID' in post:
                # we want to update
                update_clause = dict_to_sql("UPDATE", table_name, post)
                sql = '%s WHERE postID = %d' % \
                      (update_clause, post['postID'])
            else:
                insert_clause = dict_to_sql("INSERT", table_name, post)
                sql = insert_clause

            print(sql)
            cursor.execute(sql)
            rows = cursor.fetchall()

            sql = 'SELECT postID from %s where groupName = \'%s\' and postTitle = \'%s\'' % (
                table_name, post['groupName'], post['postTitle'])
            cursor.execute(sql)
            rows = cursor.fetchall()

            data = json.dumps({"result": rows[0][0]})

        if operation == 'removeTask':
            data = {
                'unknown': 'unknown'
            }
            pass
    return generate_success_response(data)


def dict_to_sql(sql_op, table_name, data):
    sql_set = ""
    sql_insert_into = ""
    sql_insert_value = ""
    for index, row in enumerate(data):

        sql_column = row
        if isinstance(data[row], (int, bool)):
            sql_column_value = str(data[row])
        else:
            sql_column_value = '\'%s\'' % (data[row])

        if sql_op == 'UPDATE':
            sql_set_chunk = sql_column + ' = ' + sql_column_value
            if index != 0:
                sql_set_chunk = ", " + sql_set_chunk
            sql_set += sql_set_chunk

        elif sql_op == 'INSERT' or sql_op == 'SELECT':
            if index != 0:
                sql_column = ',' + sql_column
                sql_column_value = ',' + sql_column_value
            sql_insert_into += sql_column
            sql_insert_value += sql_column_value

    if sql_op == 'UPDATE':
        sql = 'UPDATE %s SET %s' % (table_name, sql_set)
    elif sql_op == 'INSERT':
        sql = 'INSERT INTO %s (%s) VALUES (%s)' % (table_name, sql_insert_into, sql_insert_value)
    elif sql_op == 'SELECT':
        sql = 'SELECT %s FROM %s' % (sql_insert_into, table_name)

    return sql


def handler(event, context):
    print(json.dumps(event, sort_keys=True))
    print(context)

    resource_path = event['path']

    if resource_path == '/group':
        return group_handler(event, context)
    elif resource_path == '/task':
        return task_handler(event, context)
    elif resource_path == '/post':
        return post_handler(event, context)
    return generate_error_response(404, 'Unsupported path: ' + resource_path)


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
