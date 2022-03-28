import json
import boto3
from itertools import combinations
from botocore.exceptions import ClientError

#Checks if both restaurants in the given pair have not exceeded the maximum number of views of 10
def valid_pair(new_pair, user):
    count = 0
    for pair in new_pair:
        if pair not in user["VersusViews"]:
            break
        elif user["VersusViews"][pair] < 9:
            user["VersusViews"][pair] += 1
            count += 1
        else: 
            user["VersusViews"][pair].pop();
            count += 1
    return count == 2

def put_review(fsqid, user_id, rating, comment):
    statusCode = 200
    errorMessage = "Thank you for your feedback!\nYour review is being processed and will be added shortly."
    dynamodb = boto3.resource('dynamodb')
    
    #Adding review to Reviews table
    reviews = dynamodb.Table('Reviews')
    review = reviews.get_item(
        Key={
            'FSQID': fsqid,
            'UserID': user_id
        }
    )
    
    #If incoming review is new, put into Reviews and Users tables
    if "Item" not in review:
        response1 = reviews.put_item(
           Item={
            'FSQID': fsqid,
            'UserID': user_id,
            'Rating': rating,
            'Review': comment
        }
        )
            
        guavah_users = dynamodb.Table('GuavahUsers')
        try:
            user = guavah_users.get_item(
                Key={
                    'UserID': user_id
                }
            )
        except ClientError as e:
            statusCode = 500
            errorMessage = "Oops!\n Unable to fetch your review at this time."
            return {
                'statusCode': statusCode,
                'errorMessage': errorMessage
            }
            
        user = user["Item"]
        user["VersusViews"][fsqid] = 0
        
        if user["DailyVotes"] < 10 and len(user["VersusQueue"]) < 5 and len(user["VersusViews"]) > 1:
            restaurant_combinations = set(combinations(user['VersusViews'].keys(),2))
            versus_pairs = set([tuple(l) for l in user['VersusPairs']]) #O(n^2)
            restaurant_combinations = (restaurant_combinations | versus_pairs) - (restaurant_combinations & versus_pairs)
            
            for x in range(5):
                if (10 - len(user['VersusQueue'])) > 1 and len(restaurant_combinations) >= 1:
                    new_pair = list(restaurant_combinations.pop())
                    if valid_pair(new_pair, user):
                        user['VersusQueue'].append(new_pair)
                else:
                    break
        try:            
            response2 = guavah_users.update_item(
               Key={
                'UserID': user_id
            },
            UpdateExpression="SET VersusViews = :VersusViews, VersusQueue = :VersusQueue",
            ExpressionAttributeValues={
                ':VersusViews': user["VersusViews"],
                ':VersusQueue': user["VersusQueue"]
            },
            ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            statusCode = 500
            errorMessage = "Oops!\n Unable to add your review at this time."
            return {
                'statusCode': statusCode,
                'errorMessage': errorMessage
            }
        
            
    #If incoming review exists (is being updated), update inside of the Reviews table
    else:
        try:
            response1 = reviews.update_item(
               Key={
                'FSQID': fsqid,
                'UserID': user_id
            },
            UpdateExpression="SET Review = :rev, Rating = :rating",
            ExpressionAttributeValues={
                ':rev': comment,
                ':rating': rating
            },
            ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            statusCode = 500
            errorMessage = "Oops!\n Unable to update your review at this time."
            return {
                'statusCode': statusCode,
                'errorMessage': errorMessage
            }
            
    return {
        'statusCode': statusCode,
        'errorMessage': errorMessage,

    }


def lambda_handler(event, context):
    fsqid = event['FSQID']
    user_id = event['UserID']
    rating = event['Rating']
    comment = event['Comment']
    
    return put_review(fsqid, user_id, rating, comment)
