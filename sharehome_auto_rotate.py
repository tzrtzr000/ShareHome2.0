from __future__ import print_function

import os
from datetime import datetime
import pymysql


def init_db_connection():
    host_name = rds_config.host_name
    db_username = rds_config.db_username
    db_password = rds_config.db_password
    db_name = rds_config.db_name
    global cnx
    global cursor
    cnx = pymysql.connect(host=host_name, user=db_username, password=db_password,
                            db=db_name, autocommit=True)
    cursor = cnx.cursor()
    print("db connection established")
    return
      


def validate(res):
    pass

def lambda_handler(event, context):
    pass