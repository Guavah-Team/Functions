import json
import boto3
import math
from math import sqrt
from botocore.exceptions import ClientError

client = boto3.resource('dynamodb')
users_table = client.Table('GuavahUsers')
restaurants_table = client.Table('GuavahRestaurants')

def update_user(user_id, user_level, user_exp, versus_queue, daily_votes, added_xp):
    statusCode = 200
    errorMessage = "Versus Success"
    
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
            user_exp = (user_exp + added_xp) - required_exp
        else:
            user_exp = user_exp + added_xp
    else:
        user_exp = user_exp + added_xp
   
    del versus_queue[0]
    daily_votes += 1
    try:    
        #Update The User
        updated_user = users_table.update_item(
           Key={
            'UserID': user_id
        },
        UpdateExpression="SET #Lvl = :level, XP = :xp, VersusQueue = :vq, DailyVotes = :dv",
        ExpressionAttributeValues={
            ':level': user_level,
            ':xp': user_exp,
            ':vq': versus_queue,
            ':dv': daily_votes
        },
        ExpressionAttributeNames={
            "#Lvl": "Level"
        },
        ReturnValues="UPDATED_NEW"
        )
    except ClientError as e:
        statusCode = 500
        errorMessage = "Oops!\n Versus Error"
        return {
            'statusCode': statusCode,
            'errorMessage': errorMessage
        }
    return {
        'statusCode': statusCode,
        'errorMessage': errorMessage
    }
    
def update_restaurant(fsqid, gor):
    try:    
        updated_restaurant = restaurants_table.update_item(
           Key={
            'FSQID': fsqid
        },
        UpdateExpression="SET GOR = :gor",
        ExpressionAttributeValues={
            ':gor': gor
        },
        ReturnValues="UPDATED_NEW"
        )
    except ClientError as e:
        statusCode = 500
        errorMessage = "Oops!\n Versus Error"
        return {
            'statusCode': statusCode,
            'errorMessage': errorMessage
        }
    statusCode = 200
    errorMessage = "Versus Success"
    return {
        'statusCode': statusCode,
        'errorMessage': errorMessage
    }

# Restaurant_1: Restaurants_1 current gor
# Restaurant_2: Restaurants_2 current gor
# user_weight: The calculated user weight for the multipication of the outcome
# user_selection: 0 if restaurant_1 lost, 1 if restaurant_1 won
def update_gor(restaurant_1, restaurant_2, user):
    user_selection = user["selection"]
    user_level = user["level"]
    
    restaurant_1_expected = calc_expected_outcome(restaurant_2["rating"], restaurant_1["rating"])
    restaurant_2_expected = calc_expected_outcome(restaurant_1["rating"], restaurant_2["rating"])
    
    weight = calc_weight(restaurant_1, restaurant_2)
    user_weight = calc_user_weight(user_level)

    restaurant_1_gor = restaurant_1["rating"] + ((weight + user_weight)*(user_selection - restaurant_1_expected))
    restaurant_2_gor = restaurant_2["rating"] + ((weight + user_weight)*(0 - restaurant_2_expected)) if user_selection == 1 else restaurant_2_expected["rating"] + ((weight + user_weight) * (1 - restaurant_2_expected))
    restaurant_1_gor = math.trunc(restaurant_1_gor)
    restaurant_2_gor = math.trunc(restaurant_2_gor)
    return [restaurant_1_gor, restaurant_2_gor]


# Restaurant_1_Rank: GOR value of restaurant 1
# Restaurant_2_Rank: GOR value of restaurant 2
# Has to be ran TWICE (Once for each restaurant)
def calc_expected_outcome(r1_rank, r2_rank):
    return 1.0 / (1 + pow(10, ((r1_rank - r2_rank)/1000)))
    

# Calculates how much impact
def calc_weight(r1, r2):
    distance = 1/((sqrt(pow((r2["long"] - r1["long"]), 2) + pow((r2["lat"] - r1["lat"]), 2)))*10)

    cost = 1 - (abs((1/(1+pow(10, (r1["cost"]-r2["cost"]/3)))
                     ) - (1/(1+pow(10, (r2["cost"]-r1["cost"]/3))))))
    types = len(r1["types"].intersection(r2["types"]))
    print(distance)

    return distance + cost + types
    

def calc_user_weight(user_level):
    return 1 + (user_level/25)

def lambda_handler(event, context):
    
    r1 = {
        "rating": event["restaurants"][0]["gor"],
        "lat": event["restaurants"][0]["location"]["latitude"],
        "long": event["restaurants"][0]["location"]["longitude"],
        "cost": event["restaurants"][0]["price"],
        "types": set(event["restaurants"][0]["categories"]),
    }
    
    r2 = {
        "rating": event["restaurants"][1]["gor"],
        "lat": event["restaurants"][1]["location"]["latitude"],
        "long": event["restaurants"][1]["location"]["longitude"],
        "cost": event["restaurants"][1]["price"],
        "types": set(event["restaurants"][1]["categories"]),
    }
    
    user = {
        "level": event["user"]["Level"],
        "selection": event["userSelection"]
    }
    
    update_user(event["user"]["UserID"], event["user"]["Level"], event["user"]["XP"], event["user"]["VersusQueue"], event["user"]["DailyVotes"], 5)
    new_scores = update_gor(r1,r2,user)
    r1["rating"] = new_scores[0]
    r2["rating"] = new_scores[1]
    update_restaurant(event["restaurants"][0]["id"], new_scores[0])
    update_restaurant(event["restaurants"][1]["id"], new_scores[1])
    
    return {
        
    }
