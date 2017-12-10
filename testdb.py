import json
import datetime
# import pymysql
import logging
# import rds_config
import aws_config
import boto3
import collections
import index
from time import gmtime, strftime
from collections import deque


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Create a sql database connection
# host_name = rds_config.host_name
# db_username = rds_config.db_username
# db_password = rds_config.db_password
# db_name = rds_config.db_name
# # try:
#     global cnx
#     global cursor
#     cnx = pymysql.connect(host=host_name, user=db_username, password=db_password,
#                           db=db_name)
#     cursor = cnx.cursor()
#     print("db connection established")
#
# except:
#     pass

#
# sql = 'SELECT groupName, taskTitle, taskContent, taskDuration, taskUser, taskSolved FROM %s WHERE groupName =\'%s\'' % ('Tasks', 'lambdaTestGroup')
# print(sql)
# cursor.execute(sql)
# rows = cursor.fetchall()
#
# rowarray_list = []
# for row in rows:
#     d = collections.OrderedDict()
#     d['groupName'] = row[0]
#     d['taskTitle'] = row[1]
#     d['taskContent'] = row[2]
#     d['taskDuration'] = row[3]
#     d['taskUser'] = row[4]
#     d['taskSolved'] = row[5]
#     rowarray_list.append(d)
#
# data = json.dumps(rowarray_list)
# print(data)


origin_data = "{\"groupName\":\"lastone\",\"postContent\":\"gvjjy\",\"postTitle\":\"gjhgyjr\",\"postUrgent\":false}"

sql_op = 'UPDATE'
table_name = 'sss'
data = json.loads(origin_data)
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

    elif sql_op == 'INSERT':
        if index != 0:
            sql_column = ',' + sql_column
            sql_column_value = ',' + sql_column_value
        sql_insert_into += sql_column
        sql_insert_value += sql_column_value

if sql_op == 'UPDATE':
    sql = 'UPDATE %s SET %s' % (table_name, sql_set)
elif sql_op == 'INSERT':
    sql = 'INSERT INTO %s (%s) VALUES (%s)' % (table_name, sql_insert_into, sql_insert_value)
#print (sql)


def push_notification (user_name, group_name, push_title, push_body):
    # response = boto_pinpoint_client.get_segments(
    #     ApplicationId=aws_config.pinpoint_application_id
    # )
    # print(response)
    current_time = strftime('%Y-%m-%dT%H:%M:%S', gmtime())
    print(current_time)
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


def init_boto3_client():
    global boto_cognito_client, boto_pinpoint_client
    boto_cognito_client = boto3.client(
        'cognito-idp',
        aws_access_key_id=aws_config.aws_access_key_id,
        aws_secret_access_key=aws_config.aws_secret_access_key,
        region_name=aws_config.region

    )
    boto_pinpoint_client = boto3.client(
        'pinpoint',
        region_name=aws_config.region,
        aws_access_key_id=aws_config.aws_access_key_id,
        aws_secret_access_key=aws_config.aws_secret_access_key
    )
    return

init_boto3_client()
push_notification("s", "s", "fyfsb", "fyfsb2")


def rotateUser (user):
    if user is None:
        return None
    else:
        list = user.split(",")
        list = deque(list)
        list.rotate(-1)
        result = ','.join(list)
        return result


print(rotateUser('a,b,c'))

