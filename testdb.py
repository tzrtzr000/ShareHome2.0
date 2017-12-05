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

except:
    pass


sql = 'SELECT groupName, taskTitle, taskContent, taskDuration, taskUser, taskSolved FROM %s WHERE groupName =\'%s\'' % ('Tasks', 'lambdaTestGroup')
print(sql)
cursor.execute(sql)
rows = cursor.fetchall()

rowarray_list = []
for row in rows:
    d = collections.OrderedDict()
    d['groupName'] = row[0]
    d['taskTitle'] = row[1]
    d['taskContent'] = row[2]
    d['taskDuration'] = row[3]
    d['taskUser'] = row[4]
    d['taskSolved'] = row[5]
    rowarray_list.append(d)

data = json.dumps(rowarray_list)
print(data)

