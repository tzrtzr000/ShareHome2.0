from __future__ import print_function

import os
import library
import index
import boto3
import aws_config
from datetime import datetime, timedelta
from collections import deque


def lambda_handler(event, context):
    library.init()
    index.init_db_connection()

    global boto_cognito_client
    boto_cognito_client = boto3.client(
        'cognito-idp',
        aws_access_key_id=aws_config.aws_access_key_id,
        aws_secret_access_key=aws_config.aws_secret_access_key
    )

    table_name = 'Tasks'

    timeFormat =  "%Y-%m-%dT%H:%M:%S"
    sql = 'SELECT taskDuration, taskUser, taskID, lastRotated, taskTitle ' \
          'FROM %s ' \
          'WHERE taskSolved = FALSE' % (
            table_name)

    rows = index.execute_sql(sql)

    for row in rows:
        d = {}
        d['taskUser'] = row[1]
        d['lastRotated'] = row[3]
        # print("old:" + str(d['lastRotated']))
        # if d['lastRotated'] + d['taskDuration'] <
        d['lastRotated'] = row[3] + timedelta(minutes=row[0])
        # print("new: " + str(d['lastRotated']))

        if (datetime.now() - d['lastRotated']).total_seconds() > 0:
            new_order = rotate_user(d['taskUser'])
            d['taskUser'] = new_order[0]
            sql = index.generate_sql_clause("UPDATE", table_name, d)
            sql += " WHERE taskID = %s" % row[2]
            index.execute_sql(sql)

            # send notification to user
            user_name = new_order[1]
            try:
                boto_cognito_client.admin_get_user(
                    UserPoolId=aws_config.UserPoolId,
                    Username=user_name
                    )
            except boto_cognito_client.exceptions.UserNotFoundException as e:
                pass
                print("Invalid user: %s" % user_name)
            else:
                index.push_notification(user_name, None, row[4], "It's your turn now")
                print("%s has been notified for %s" % (user_name, row[4]))
    index.close_db_connection()


def rotate_user(user):
    if user is None:
        return None
    else:
        user_list = user.split(",")
        user_list = deque(user_list)
        user_list.rotate(-1)
        result = ','.join(user_list)
        return [result, user_list[0]]

