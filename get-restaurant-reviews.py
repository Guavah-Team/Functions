#DEPRECATED. Must be updated for new review logic. 

import json
import boto3

def get_restaurant_reviews(fsqid):
    dynamodb = boto3.resource('dynamodb')

    guavah_restaurants = dynamodb.Table('GuavahRestaurants')
    restaurant = guavah_restaurants.get_item(
        Key={
            'FSQID': fsqid,
        }
    )
    
    #Check if restaurant exists
    if ("Item" in restaurant):
        restaurant = restaurant["Item"]
        #Check if restaurant has any reviews
        if ("Reviews" in restaurant):
            restaurant_reviews = restaurant["Reviews"]
            return restaurant_reviews
        else:
            return None
    else: 
        return None

def lambda_handler(event, context):
    fsqid = event['FSQID']
    restaurant_reviews = get_restaurant_reviews(fsqid)
    if (restaurant_reviews is not None):
        return {
            'statusCode': 200,
            'body': restaurant_reviews
        }
    else:
        return {
            'statusCode': 404
        }
