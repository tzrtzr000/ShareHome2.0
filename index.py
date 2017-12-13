import json
import pymysql
import logging
import rds_config
import aws_config
import boto3
import time
from time import gmtime, strftime
import library

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Create a sql database connection
def init_db_connection():
    try:
        library.cnx = pymysql.connect(
            host=rds_config.host_name,
            user=rds_config.db_username,
            password=rds_config.db_password,
            db=rds_config.db_name,
            autocommit=True
        )
        library.cursor = library.cnx.cursor()
        # print("db connection established")
        return
    except pymysql.err.Error as e:
        return generate_error_response(500, e.args)


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


def generate_success_response(data):
    close_db_connection()
    logger.info("Run success, return data:")
    logger.info(data)
    return {
        'statusCode': 200,
        'body': data,
        'headers': {'Content-Type': 'application/json'}
    }


def generate_error_response(error_code, body):
    close_db_connection()
    logger.error("generate error response: " + str(error_code) + body)
    return {
        'statusCode': error_code,
        'body': json.dumps({"result": body}),
        'headers': {'Content-Type': 'application/json'}
    }


def boto_admin_list_groups_for_user(user_name):
    return boto_cognito_client.admin_list_groups_for_user(
        Username=user_name,
        UserPoolId=aws_config.UserPoolId,
        Limit=60
    )


# query string to dictionary, used because AWS SDK sometimes put query string into body (bug?)
def qs_to_dict(qs):
    final_dict = dict()
    for item in qs.split("&"):
        final_dict[item.split("=")[0]] = item.split("=")[1]
    return final_dict


# Return None if not in any group
def boto_get_group_of_a_user(user_name):
    response = boto_cognito_client.admin_list_groups_for_user(
        Username=user_name,
        UserPoolId=aws_config.UserPoolId,
        Limit=60
    )
    if len(response['Groups']) == 1:
        return response['Groups'][0]['GroupName']
    elif len(response['Groups']) == 0:
        return None
    else:
        raise Exception("User %s in more than one group!" % user_name)


# /group + POST / GET
def group_handler(event, context):
    init_boto3_client()

    query_string_parameters = event["queryStringParameters"]
    if query_string_parameters is None:
        if event['body'] is not None:
            # print("SDK just fucked up again")
            query_string_parameters = qs_to_dict(event['body'])
        else:
            return generate_error_response(400, 'Missing query_string_parameters (it is null)')
    if 'operation' not in query_string_parameters:
        return generate_error_response(400, 'Missing \'operation\' key in query_string')
    operation = query_string_parameters['operation']

    if 'userName' not in query_string_parameters:
        return generate_error_response(400, 'Missing \'userName\' key in query_string')
    user_name = query_string_parameters['userName']

    if event['httpMethod'] == "GET":
        # This function always returns a list of strings
        if operation == 'listMembers':
            try:
                group_name = boto_get_group_of_a_user(user_name)
                if group_name is None:
                    return generate_error_response(400, "User: %s is not in any group!" % user_name)
                response = boto_cognito_client.list_users_in_group(
                    UserPoolId=aws_config.UserPoolId,
                    GroupName=group_name,
                    Limit=60
                )
                return_list = [user['Username'] for user in response['Users']]
                return generate_success_response(json.dumps(return_list))
            except Exception as e:
                # User in multiple groups
                return generate_error_response(400, e.args)

        elif operation == 'getGroupName':
            try:
                group_name = boto_get_group_of_a_user(user_name)
                return generate_success_response(json.dumps([group_name]))
            except Exception as e:
                # User in multiple groups
                return generate_error_response(400, e.args)

        else:
            return generate_error_response(400, "Not supported operation: " + operation)

    elif event['httpMethod'] == "POST":

        if 'groupName' not in query_string_parameters:
            return generate_error_response(400, 'Missing \'groupName\' key in request body')
        group_name = query_string_parameters['groupName']

        # add a user into existing group
        if operation == 'add':
            # First check if group Name and UserName are valid.
            try:
                boto_cognito_client.get_group(
                    GroupName=group_name,
                    UserPoolId=aws_config.UserPoolId
                )
                boto_cognito_client.admin_get_user(
                    UserPoolId=aws_config.UserPoolId,
                    Username=user_name
                    )
            except boto_cognito_client.exceptions.ResourceNotFoundException:
                return generate_error_response(400, "Group '%s' does not exist!" % group_name)
            except boto_cognito_client.exceptions.UserNotFoundException:
                return generate_error_response(400, "User '%s' does not exist!" % user_name)

            # Then check if user is already in a group & remove user from that group
            boto_add_user_to_only_one_group(user_name, group_name)

            # push notification
            new_segment = create_pinpoint_segment(None, group_name)
            create_campaign(new_segment, group_name + ":" + user_name,
                            "User added", "User '%s' has been added to group %s" %
                            (user_name, group_name))
            return generate_success_response(generate_result_response("User '%s' has been added to group %s" %
                                                                      (user_name, group_name)))

        # Create new group and add username to that group
        elif operation == 'create':
            # First check is group already exists
            try:
                boto_cognito_client.get_group(
                    GroupName=group_name,
                    UserPoolId=aws_config.UserPoolId
                )
            except boto_cognito_client.exceptions.ResourceNotFoundException:
                boto_cognito_client.create_group(
                    GroupName=group_name,
                    UserPoolId=aws_config.UserPoolId
                )
                # Then add user to the group
                boto_add_user_to_only_one_group(user_name, group_name)
                return generate_success_response(
                    generate_result_response("Group '%s' created. You're the first member." % group_name))

            else:
                # Group existed
                return generate_error_response(400, "Group '%s' already exists!" % group_name)


# Assume user_name and group_name are both valid
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
        print("User " + user_name + " removed from group: " + old_group_name)

    boto_cognito_client.admin_add_user_to_group(
        UserPoolId=aws_config.UserPoolId,
        Username=user_name,
        GroupName=group_name
    )
    print("User " + user_name + " added into group: " + group_name)


def create_campaign(new_segment, campaign_name, push_title, push_body):
    current_time = strftime('%Y-%m-%dT%H:%M:%S', gmtime())
    boto_pinpoint_client.create_campaign(
        ApplicationId=aws_config.pinpoint_application_id,
        WriteCampaignRequest={
            'Description': 'Campaign created by lambda function',
            'IsPaused': False,
            'MessageConfiguration': {
                'GCMMessage': {
                    'Action': 'OPEN_APP',
                    'Body': push_body,
                    'SilentPush': False,
                    'Title': push_title,
                }
            },
            'Name': campaign_name,
            'Schedule': {
                'Frequency': 'ONCE',
                'IsLocalTime': False,
                'StartTime': current_time
            },
            'SegmentId': new_segment['Id'],
            'SegmentVersion': new_segment['Version']
        }
    )


def create_pinpoint_segment(user_name, group_name):
    logger.info("Create segment: userName: %s, groupName: %s" % (user_name, group_name))
    response = boto_pinpoint_client.create_segment(
        ApplicationId=aws_config.pinpoint_application_id,
        WriteSegmentRequest={
            'Dimensions': {
                'Attributes': {
                    'UserName' if user_name is not None else 'GroupName': {
                        'AttributeType': 'INCLUSIVE',
                        'Values': [
                            user_name if user_name is not None else group_name,
                        ]
                    }
                },
                'Behavior': {
                    'Recency': {
                        'Duration': 'DAY_30',
                        'RecencyType': 'ACTIVE'
                    }
                }
            },
            'Name': user_name if user_name is not None else group_name
        }
    )
    return response['SegmentResponse']


def task_handler(event, context):
    init_db_connection()
    init_boto3_client()

    table_name = 'Tasks'
    sample_task = {
        "groupName": "sample_task_group",
        "taskTitle": "sample_task_title",
        "taskContent": "sample_task_content",
        "taskDuration": 60,
        "taskUser": "userID,userID2,userID3",
        "taskSolved": False,
        "taskID": 15,
        "lastRotated": "dateString"
    }
    query_string_parameters = event["queryStringParameters"]
    if query_string_parameters is None:
        return generate_error_response(400, 'Missing query_string_parameters')

    if event['httpMethod'] == "GET":
        if 'groupName' not in query_string_parameters:
            return generate_error_response(400, 'Missing \'groupName\' key in request body')
        group_name = query_string_parameters['groupName']
        sql_clause = generate_sql_clause("SELECT", table_name, sample_task)
        sql = '%s WHERE groupName = \'%s\' AND taskSolved = False' % (
            sql_clause, group_name)

        rows = execute_sql(sql)

        row_array_list = []
        for row in rows:
            d = dict()
            d['groupName'] = row[0]
            d['taskTitle'] = row[1]
            d['taskContent'] = row[2]
            d['taskDuration'] = row[3]
            d['taskUser'] = row[4]
            d['taskSolved'] = True if row[5] else False
            d['taskID'] = row[6]
            if row[7] is None:
                d['lastRotated'] = time.strftime('%Y-%m-%d %H:%M:%S')
                logger.error("USE CURRENT TIME as lastRotated")
            else:
                d['lastRotated'] = row[7].strftime('%Y-%m-%d %H:%M:%S')
            row_array_list.append(d)

        data = json.dumps(row_array_list)
        return generate_success_response(data)

    elif event['httpMethod'] == "POST":
        if 'operation' not in query_string_parameters:
            return generate_error_response(400, 'Missing \'operation\' key in request body')
        operation = query_string_parameters['operation']

        task = json.loads(event['body'])

        if operation == 'add':
            if 'taskID' in task:
                # we want to update

                if task['taskSolved'] is True:
                    if 'userName' not in query_string_parameters:
                        return generate_error_response(400, 'Missing \'userName\' key in query_string')
                    user_name = query_string_parameters['userName']

                    sql = "SELECT solvedUser, taskTitle, groupName FROM %s WHERE taskID = %d" % (
                        table_name, task['taskID'])
                    row = execute_sql(sql)
                    solvedUser = row[0][0]
                    task['taskTitle'] = row[0][1]
                    task['solvedUser'] = add_user_name_non_duplicate_in_user_list_string(solvedUser, user_name)
                    if not verify_task_finished_or_notify_users_task_to_solve(task):
                        task['taskSolved'] = False
                    else:
                        new_segment = create_pinpoint_segment(None, row[0][2])
                        create_campaign(new_segment, row[0][2], task['taskTitle'], task['taskTitle'] + " has resolved")

                    print("real task status:" + str(task['taskSolved']))

                update_clause = generate_sql_clause("UPDATE", table_name, task)
                sql = '%s WHERE taskID = %d' % \
                      (update_clause, task['taskID'])
                data = generate_result_response("Task '%s' updated" % task['taskTitle'])

            else:
                sql = generate_sql_clause("INSERT", table_name, task)
                data = generate_result_response("Task '%s' added" % task['taskTitle'])

            execute_sql(sql)
        else:
            return generate_error_response(400, "Unsupported operation: " + operation)

        return generate_success_response(data)

    else:
        return generate_error_response(400, "Unsupported httpMethod: " + event['httpMethod'])


def add_user_name_non_duplicate_in_user_list_string(user_list_string, user_name):
    if user_list_string is None or user_list_string is "":
        user_list_string = []
    else:
        user_list_string = user_list_string.split(",")
    if user_name not in user_list_string:
        user_list_string.append(user_name)
    return ','.join(user_list_string)


def verify_task_finished_or_notify_users_task_to_solve(task):
    solved_user_string = task['solvedUser']

    if solved_user_string is None or solved_user_string is "":
        logger.error("Program ERROR! user_list_string should never be null, at least it should have the user")
        return generate_error_response(400, generate_result_response("Check log right now."))
    else:
        solved_user_list = solved_user_string.split(",")

    response = boto_cognito_client.list_users_in_group(
        UserPoolId=aws_config.UserPoolId,
        GroupName=task['groupName'],
        Limit=60
    )
    all_users_in_group = [user['Username'] for user in response['Users']]

    pushed_user_count = 0
    for user in all_users_in_group:
        if user not in solved_user_list:
            pushed_user_count = pushed_user_count + 1
            new_segment = create_pinpoint_segment(user, None)
            create_campaign(new_segment, user, task['taskTitle'], "Please verify task '%s' completion" % task['taskTitle'])
    return pushed_user_count == 0


def execute_sql(sql):
    try:
        print(sql)
        library.cursor.execute(sql)
        rows = library.cursor.fetchall()
        return rows
    except pymysql.Error as e:
        logger.error("SQL execution error: " + sql)
        logger.error(e)
        raise e


def generate_result_response(result):
    return json.dumps(
        {
            "result": result
        }
    )


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

    if event['httpMethod'] == "GET":
        if 'groupName' not in query_string_parameters:
            return generate_error_response(400, 'Missing \'groupName\' key in request body')
        group_name = query_string_parameters['groupName']

        select_cause = generate_sql_clause("SELECT", table_name, post_sample)
        sql = '%s WHERE groupName =\'%s\' ORDER BY postUrgent desc' % (select_cause, group_name)
        rows = execute_sql(sql)

        row_array_list = []
        for row in rows:
            d = dict()
            d['groupName'] = row[0]
            d['postTitle'] = row[1]
            d['postContent'] = row[2]
            d['postUrgent'] = True if row[3] else False
            d['postID'] = row[4]
            row_array_list.append(d)
        data = json.dumps(row_array_list)
        return generate_success_response(data)

    elif event['httpMethod'] == "POST":
        if 'operation' not in query_string_parameters:
            return generate_error_response(400, 'Missing \'operation\' key in request body')
        operation = query_string_parameters['operation']

        post = json.loads(event['body'])

        if operation == 'add':
            if 'postID' in post:
                # we want to update
                update_clause = generate_sql_clause("UPDATE", table_name, post)
                sql = '%s WHERE postID = %d' % \
                      (update_clause, post['postID'])
            else:
                sql = generate_sql_clause("INSERT", table_name, post)

            execute_sql(sql)

            data = generate_result_response("Add post '%s' success" % post['postTitle'])
        elif operation == 'remove':
            if 'postID' not in post:
                return generate_error_response(400, "Remove must have postID ")
            sql = "DELETE FROM %s WHERE postID = %d" % (table_name, post['postID'])
            execute_sql(sql)
            data = generate_result_response("Remove post success")

        else:
            return generate_error_response(400, "Unsupported operation: " + operation)
        return generate_success_response(data)

    else:
        return generate_error_response(400, "Unsupported httpMethod: " + event['httpMethod'])


def profile_handler(event, context):
    sample_profile = {
        "result": "string"
    }
    init_db_connection()
    table_name = 'Profiles'
   
    query_string_parameters = event["queryStringParameters"]
    if query_string_parameters is None:
        return generate_error_response(400, 'Missing query_string_parameters')

    if event['httpMethod'] == "GET":
        if 'userName' not in query_string_parameters:
            return generate_error_response(400, 'Missing \'userName\' key in request body')
        user_name = query_string_parameters['userName']
        select_cause = generate_sql_clause("SELECT", table_name, sample_profile)
        sql = '%s WHERE userName =\'%s\'' % (select_cause, user_name)
        rows = execute_sql(sql)
        if len(rows) != 0:
            result = {
                "result": rows[0][0]
            }
        else:
            return generate_error_response(400, generate_result_response("User '%s' has no profile picture" % user_name))

        data = json.dumps(result)
        return generate_success_response(data)

    elif event['httpMethod'] == "POST":
        if 'userName' not in query_string_parameters:
            return generate_error_response(400, 'Missing \'userName\' key in request body')
        user_name = query_string_parameters['userName']

        profile = json.loads(event['body'])

        sql_check = generate_sql_clause("SELECT", table_name, profile)
        sql_check = sql_check + " WHERE userName = '%s'" % user_name
        rows = execute_sql(sql_check)
        if len(rows) != 0:
            # we want to update
            update_clause = generate_sql_clause("UPDATE", table_name, profile)
            sql = '%s WHERE userName = "%s"' % \
                        (update_clause, user_name)
        else:
            sql = "INSERT INTO %s (userName, result) VALUES (\'%s\', \'%s\') " % (table_name, user_name, profile['result'])
        execute_sql(sql)
        return generate_success_response(generate_result_response("success?"))


def generate_sql_clause(sql_op, table_name, data):
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
    else:
        raise Exception("Unsupported sql operation in generate_sql_clause")
    return sql


def handler(event, context):
    print(json.dumps(event, sort_keys=True))
    library.init()
    resource_path = event['path']

    if resource_path == '/group':
        return group_handler(event, context)
    elif resource_path == '/task':
        return task_handler(event, context)
    elif resource_path == '/post':
        return post_handler(event, context)
    elif resource_path == '/profile':
        return profile_handler(event, context)
    return generate_error_response(400, 'Unsupported path: ' + resource_path)


def close_db_connection():
    if library.cnx is not None:
        library.cursor.close()
        library.cnx.close()
        library.cnx = None
    return
