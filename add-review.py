import json
import boto3
from botocore.exceptions import ClientError

def put_review(fsqid, user_id, rating, comment):
    dynamodb = boto3.resource('dynamodb')
    
    #Adding review to Reviews table
    reviews = dynamodb.Table('Reviews')
    review = reviews.get_item(
        Key={
            'FSQID': fsqid,
            'UserID': user_id
        }
    )

    if "Item" not in review:
        response1 = reviews.put_item(
           Item={
            'FSQID': fsqid,
            'UserID': user_id,
            'Rating': rating,
            'Review': comment
        }
        )
            
        #Adding review to users table        
        guavah_users = dynamodb.Table('GuavahUsers')
        user = guavah_users.get_item(
            Key={
                "UserID": user_id
            }
            )
        user = user['Item']
        if "ReviewedRestaurants" not in user:
            try:
                response2 = guavah_users.put_item(
                   Item={
                    'UserID': user_id,
                    'VersusViews': [[fsqid, 0]]
                }
                )
            except ClientError as e:
                return e.response
        else:
            try:
                response2 = guavah_users.update_item(
                   Key={
                    'UserID': user_id
                },
                UpdateExpression="SET VersusViews = list_append(VersusViews, :id)",
                ExpressionAttributeValues={
                    ':id': [[fsqid, 0]]
                },
                ReturnValues="UPDATED_NEW"
                )
            except ClientError as e:
                return e.response

    else:
        try:
            response1 = reviews.update_item(
               Key={
                'FSQID': fsqid,
                'UserID': user_id
            },
            UpdateExpression="SET Review = :rev",
            ExpressionAttributeValues={
                ':rev': comment
            },
            ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            return e.response 
            
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            #'Access-Control-Allow-Origin': '*'
        }
    }


def lambda_handler(event, context):
    fsqid = event['FSQID']
    user_id = event['UserID']
    rating = event['Rating']
    comment = event['Comment']
    
    return put_review(fsqid, user_id, rating, comment)
