from __future__ import print_function

import os
from datetime import datetime, timedelta
import pymysql
import rds_config
import collections
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def init_db_connection():
    try:
        global cnx
        global cursor
        cnx = pymysql.connect(
            host=rds_config.host_name,
            user=rds_config.db_username,
            password=rds_config.db_password,
            db=rds_config.db_name,
            autocommit=True
        )
        cursor = cnx.cursor()
        # print("db connection established")
        return
    except pymysql.err.Error as e:
        return generate_error_response(500, e.args)


def generate_success_response(data):
    close_db_connection()
    logger.info("Run success, return data:")
    logger.info(data)


def generate_error_response(error_code, body):
    close_db_connection()
    logger.error(str(error_code) + body)


def close_db_connection():
    global cnx
    if cnx is not None:
        cursor.close()
        cnx.close()
        cnx = None
    return


def validate(res):
    pass


def lambda_handler(event, context):
    init_db_connection()
    table_name = 'Tasks'

    sql = 'SELECT groupName, taskTitle, taskContent, taskDuration, taskUser, taskSolved, lastRotated FROM %s' % (
        table_name)
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
        d['lastRotated'] = row[6]
        print(d['lastRotated'])
        # if d['lastRotated'] + d['taskDuration'] <
        lastTime_object = datetime.strftime(row[6]) + timedelta(minutes=row[3])
        print(lastTime_object)

        row_array_list.append(d)
    cnx.close()
