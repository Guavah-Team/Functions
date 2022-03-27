import json
import boto3


def lambda_handler(event, context):
    count = 0
    client = boto3.resource('dynamodb')
    table = client.Table('guavahTableCounter')

    try:
        for record in event['Records']:
            if record['eventName'] == "INSERT":
                count = count + 1
    except Exception as e:
        print(e)

    try:
        table.update_item(
            Key={
                'Count': 'Users'
            },
            UpdateExpression="SET Amount = if_not_exists(Amount, :start) + :inc",

            ExpressionAttributeValues={
                ':inc': count,
                ':start': 0,
            },
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        print(e)

    return {
        'statusCode': 200,
    }
