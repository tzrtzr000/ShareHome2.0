import json
import datetime
import pymysql
def database_connect():
    
    ####################################
    db_name = 'shareHome'
    table_name = 'Groups'
    host_name = 'alexadb.yishen.org'
    db_user_name = 'webAccess'
    db_password = 'G32xsj!klXex&8sl45'
    ####################################

    try:
        cnx = pymysql.connect(host=host_name, user=db_user_name, password=db_password,
                              db=db_name)
        cursor = cnx.cursor()
        print("connection success")
        sql = "SELECT * FROM %s" % (table_name)
        cursor.execute(sql)

    except:
        return generate_error_response(201, 
            "Database connection failed, please try again"
            "Database connection failed")

    if cursor.rowcount == 0:
        return generate_error_response(201, "Please download and run the client software on your computer to complete"
                                  " account linking and pairing."
                                  " You can find the download link in the skill's description part.")

def generate_error_response(errorCode, bodyString):
    return {'statusCode': errorCode,
        'body': bodyString,
        'headers': {'Content-Type': 'application/json'}
    }



def handler(event, context):
    return database_connect()
    data = {
        'output': 'Hello World 333',
        'timestamp': datetime.datetime.utcnow().isoformat()
    }
    return {'statusCode': 200,
            'body': json.dumps(data),
            'headers': {'Content-Type': 'application/json'}}
