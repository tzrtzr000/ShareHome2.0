import json
import datetime
import pymysql
import logging
import rds_config
import aws_config
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Create a sql database connection
def database_connect():
    host_name = rds_config.host_name
    db_username = rds_config.db_username
    db_password = rds_config.db_password
    db_name = rds_config.db_name
    try:
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
    client = boto3.client(
    'cognito-idp',
    aws_access_key_id=aws_config.aws_access_key_id,
    aws_secret_access_key=aws_config.aws_secret_access_key
    )
    return client


def generate_error_response(error_code, body):
    return {'statusCode': error_code,
            'body': body,
            'headers': {'Content-Type': 'application/json'}
            }


def group_handler(event, context):
    body = event['body']
    print('In Group handler, request body is ' + body)
    if 'operation' not in body:
        return generate_error_response(400, 'Missing \'operation\' key in request body')
    
    client = establish_boto3_client()
    response = client.list_users(
    UserPoolId=aws_config.UserPoolId,
    AttributesToGet=[
        'group_id',
    ],
    Limit=123
)

    if body['operation'] == 'create':
        # create a new group
        cursor = database_connect()
    return generate_success_response(body)


def handler(event, context):
    print(json.dumps(event, sort_keys=True))
    print(context)

    resource_path = event['path']

    if resource_path == '/group':
        return group_handler(event, context)

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
        'body': json.dumps(data),
        'headers': {'Content-Type': 'application/json'}
    }
