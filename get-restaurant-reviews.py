import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')

def get_users(users_id_list):
    guavah_users = dynamodb.Table('GuavahUsers')
    
    batch_keys = {
        guavah_users.name:{
            'Keys': [{'UserID': user_id} for user_id in users_id_list]
        }
    }
    
    users = dynamodb.batch_get_item(RequestItems=batch_keys)["Responses"]["GuavahUsers"]
    users_dictionary = {}
    for user in users:
        users_dictionary[user["UserID"]] = [user["Name"], user["ProfilePhoto"], user["Level"]]
    return users_dictionary
    

def get_restaurant_reviews(fsqid):
    reviews = dynamodb.Table('Reviews')
    restaurant_reviews = reviews.query(
        KeyConditionExpression = Key('FSQID').eq(fsqid)
    )
    
    restaurant_reviews = restaurant_reviews["Items"]
    if not restaurant_reviews:
        return []
        
    users_id_list = []
    for review in restaurant_reviews:
        users_id_list.append(review["UserID"])
    
    users = get_users(users_id_list)
    for review in restaurant_reviews:
        review["Name"] = users[review["UserID"]][0]
        review["ProfilePhoto"] = users[review["UserID"]][1]
        review["Level"] = users[review["UserID"]][2]
    
    return restaurant_reviews

def lambda_handler(event, context):
    fsqid = event['FSQID']
    restaurant_reviews = get_restaurant_reviews(fsqid)
    return restaurant_reviews

