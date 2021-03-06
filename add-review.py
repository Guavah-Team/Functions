import json
import boto3
from itertools import combinations
from botocore.exceptions import ClientError

client = boto3.resource('dynamodb')
users_table = client.Table('GuavahUsers')

def increase_user_level(user_id, user_level, user_exp, added_xp):
    
    exp_map = {
        0: 15,
        1: 60,
        2: 63,
        3: 68,
        4: 75,
        5: 84,
        6: 95,
        7: 108,
        8: 123,
        9: 140,
        10: 159,
        11: 180,
        12: 203,
        13: 228,
        14: 255,
        15: 284,
        16: 315,
        17: 348,
        18: 383,
        19: 420,
        20: 459,
        21: 500,
        22: 543,
        23: 588,
        24: 635,
        25: 999
    }
    
    required_exp = exp_map[user_level]
    if (user_exp + added_xp) >= required_exp:
        if user_level < 25: 
            user_level = user_level + 1
            user_exp = (user_exp+added_xp) - required_exp
        else:
            user_exp = user_exp+added_xp
    else:
        user_exp = user_exp+added_xp
   
    try:    
        #Update The User
        updated_user = users_table.update_item(
           Key={
            'UserID': user_id
        },
        UpdateExpression="SET #Lvl = :level, XP = :xp",
        ExpressionAttributeValues={
            ':level': user_level,
            ':xp': user_exp
        },
        ExpressionAttributeNames={
            "#Lvl": "Level"
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
        user_level = user["Level"]
        user_xp = user["XP"]
        user["VersusViews"][fsqid] = 0
        
        if user["DailyVotes"] < 10 and len(user["VersusQueue"]) < 5 and len(user["VersusViews"]) > 1:
            restaurant_combinations = set(combinations(user['VersusViews'].keys(),2))
            versus_pairs = set([tuple(l) for l in user['VersusPairs']]) #O(n^2)
            restaurant_combinations = (restaurant_combinations | versus_pairs) - (restaurant_combinations & versus_pairs)
            
            for x in range(5):
                if (5 - len(user['VersusQueue'])) > 1 and len(restaurant_combinations) >= 1:
                    new_pair = list(restaurant_combinations.pop())
                    if valid_pair(new_pair, user):
                        user['VersusQueue'].append(new_pair)
                else:
                    break
        increase_user_level(user_id, user_level, user_xp, 5)
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
