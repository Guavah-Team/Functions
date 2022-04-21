import json
import boto3
import random
from boto3.dynamodb.conditions import Attr
from itertools import combinations

def lambda_handler(event, context):
    # 1. Get users (With queue < 10, length of views > 1 ) >>
    # 2. Get their views  >>
    # 3. Generate combination of reviews >>
    # 4. Union-Intersection it with the versus pairs >>
    # 5. Pick x (x is the amount needed to get to a total of 10 in queue)
    # 6. Update queue with the new items
    
    client = boto3.resource('dynamodb')
    table = client.Table('GuavahUsers')
    
    response = table.scan(
        FilterExpression=Attr("VersusQueue").size().lt(10) and Attr("VersusViews").size().gt(1)
    )
    
    for user in response['Items']:
        user_id = user['UserID']
        restaurant_combinations = set(combinations(user['VersusViews'].keys(),2))
        versus_pairs = set([tuple(l) for l in user['VersusPairs']]) #O(n^2)
        restaurant_combinations = (restaurant_combinations | versus_pairs) - (restaurant_combinations & versus_pairs)
        
        for x in range(10):
            if (10 - len(user['VersusQueue'])) > 1 and len(restaurant_combinations) > 1:
                
                new_pair = list(restaurant_combinations.pop())
                
                for pair in new_pair:
                    if user['VersusViews']:
                
                
                user['VersusQueue'].append(new_pair)
            else:
                break
        
        response = table.update_item(
            Key={
                'UserID': user_id,
            },
            UpdateExpression="set info.rating=:r, info.plot=:p, info.actors=:a",
            ExpressionAttributeValues={
                ':r': Decimal(rating),
                ':p': plot,
                ':a': actors
            },
            ReturnValues="UPDATED_NEW"
        )
        
    return response
    
    return {
        'statusCode': 200,
        'body': response['Items']
    }

