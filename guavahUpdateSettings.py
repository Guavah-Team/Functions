import json
import boto3
from botocore.exceptions import ClientError

client = boto3.resource('dynamodb')
users_table = client.Table('GuavahUsers')

def lambda_handler(event, context):
    statusCode = 200
    radius = 1609 * event['Radius']
    try:    
        #Update The User
        updated_user = users_table.update_item(
           Key={
            'UserID': event['UserID']
        },
        UpdateExpression="SET DarkMode = :dark_mode, Vegan = :vegan, Radius = :radius",
        ExpressionAttributeValues={
            ':dark_mode': event['DarkMode'],
            ':vegan': event['Vegan'],
            ':radius': radius
        },
        ReturnValues="UPDATED_NEW"
        )
    except ClientError as e:
        statusCode = 500
        errorMessage = "Oops!\n Unable to update your settings."
        return {
            'statusCode': statusCode,
            'errorMessage': errorMessage
        }
        
    return {
        'statusCode': statusCode,
    }
