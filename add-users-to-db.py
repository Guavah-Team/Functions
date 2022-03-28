import json
import boto3
from time import gmtime, strftime

#Write user data to the GuavahUsers table in DynamoDB
def put_user(user_ID, name, email, dt):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('GuavahUsers')
    response = table.put_item(
       Item={
            'UserID': user_ID,
            'Name': name,
            'Email': email,
            'CreatedAt': dt,
            'VersusViews': {},
            'VersusQueue': [],
            'VersusPairs': [],
            'DailyVotes': 0
        }
    )
    return response
    
    

def lambda_handler(event, context):
    
    #Get user info from Cognito event
    user_ID = event['userName']
    name = event['request']['userAttributes']['name']
    email = event['request']['userAttributes']['email']
    
    #Current date
    dt = strftime("%Y-%m-%d %H:%M:%S", gmtime())
    dt = str(dt)
    
    #Writes to DynamoDB
    #NOTICE: A new user account will be successffully created despite this function failing.
    #If this function fails, user data will NOT be available in DynamoDB.
    put_user(user_ID, name, email, dt)
   
    return event
