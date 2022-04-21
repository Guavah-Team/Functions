import json
import boto3
import requests
from cmath import sqrt

#For interacting with the database
client = boto3.resource('dynamodb')
table = client.Table('GuavahUsers')
table_restaurants = client.Table('GuavahRestaurants')

def lambda_handler(event, context):
    statusCode = 200
    #details of each restaurant
    fsq_response = []
    restaurant_details = []
    
    user = table.get_item(
        Key={
            "UserID": event['UserID']
        }
    )['Item']
    
    #Does the user have anymore restaurants to display and are they allowed to submit another versus?
    if len(user['VersusQueue']) > 0 and user['DailyVotes'] < 10:
        restaurants = user['VersusQueue'][0]
        
        for restaurant in restaurants:
            url = f"https://api.foursquare.com/v3/places/{restaurant}?fields=fsq_id%2Cname%2Cprice%2Ccategories%2Cgeocodes%2Cphotos%2Crating"
            
            headers = {
                "Accept": "application/json",
                "Authorization": "fsq331oOD5fSvDUla7PwS5kJ8Ttw2V07DMrldp8XJxCU8mg="
            }

            response = requests.request("GET", url, headers=headers)
            fsq_response.append(response.json())
            
        for poi in fsq_response:
            categories = []
            for category in poi["categories"]:
                categories.append(category["id"])
                
            dict = {
                "id": poi["fsq_id"], #FSQ id used to bind a restaurant with a gor value.
                "name": poi["name"],
                "gor": 0, #Our gor value (defaults to zero-- entire list is updated after.)
                "price": poi["price"] if poi["price"] < 4 else 3,
                "location": poi["geocodes"]["main"],
                "categories": categories,
                "photo": poi["photos"][0]["prefix"] + "original" + poi["photos"][0]["suffix"] if ("photos" in poi and len(poi["photos"]) > 0) else None,
                "venue": "http://foursquare.com/v/" + poi["fsq_id"]
            }
            
            try:
                dict["gor"] = table_restaurants.get_item(
                    Key={
                        "FSQID": poi["fsq_id"]
                    }
                )['Item']['GOR']
                print(dict["gor"])
            except:
                statusCode = 503
                break
            
            restaurant_details.append(dict)

        return {
            'statusCode': statusCode,
            'restaurants': restaurant_details,
            'user': user
        }
    else:
        statusCode = 404
        errorMessage = "An unknown error occured."
        if len(user['VersusQueue']) <= 1:
            errorMessage = "Try reviewing some restaurants you have been to and come back later :)"
        elif user['DailyVotes'] >= 10:
            errorMessage = "You have exceeded your daily votes (10)! Come back tomorrow :)"
        
        return {
            'statusCode': statusCode,
            'message': errorMessage,
        }
