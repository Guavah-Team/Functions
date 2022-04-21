import json
import boto3

client = boto3.resource('dynamodb')
users_table = client.Table('GuavahUsers')

def increase_user_level(user_id, user_level, user_exp, added_xp):
    print("Ran Succuessfully")
    exp_map = {
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
        
    #Update The User
    updated_user = users_table.update_item(
       Key={
        'UserID': user_id
    },
    UpdateExpression="SET Level = :Level, XP = :XP",
    ExpressionAttributeValues={
        ':Level': user_level,
        ':XP': user_xp
    },
    ReturnValues="UPDATED_NEW"
    )
    
    

def lambda_handler(event, context):
    statusCode = 200

    try:
        user = users_table.get_item(
            Key={
                "UserID": event['UserID']
            }
        )['Item']
    except:
        statusCode = 404
        user = "Could not find user."
    
    return {
        'statusCode': statusCode,
        'body': user
    }
