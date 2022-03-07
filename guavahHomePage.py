import json
import requests
from requests.structures import CaseInsensitiveDict
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

###
# get_gor returns the gor of the passed poi.
# used as the key to sort search results before returning them.
###
def get_gor(poi):
    return poi["gor"]

###
# put_restaurants takes in a list and preforms a batch write.
# This write will not update items and will only add them to DynamoDB
# if the key does not exist.
###
def put_restaurants(results, gor=150):
    client = boto3.resource('dynamodb')
    table = client.Table('GuavahRestaurants')
    
    with table.batch_writer() as batch:
        for poi in results:
            batch.put_item(
                    Item={
                        'FSQID': poi["id"],
                        'GOR': gor
                    }
                )
                
def get_restaurants(results):
    client = boto3.resource('dynamodb')
    table = client.Table('GuavahRestaurants')
    
    results_keys = []
    for poi in results:
        results_keys.append(poi["id"])
    
    batch_keys = {
        table.name:{
            'Keys': [{'FSQID': id} for id in results_keys]
        }
    }
    
    response = client.batch_get_item(RequestItems=batch_keys)
    response_dictionary = {}
    for poi in response['Responses']['GuavahRestaurants']:
        response_dictionary[poi["FSQID"]] = poi["GOR"]
    return response_dictionary
    

def lambda_handler(event, context):
    latlong = event['latlong'].split(",") #41.8781%2C-87.6298
    radius = event['radius'] #2000
    category = "13000"
    fields = "fsq_id,name,description,tel,website,distance,price,categories,popularity,location,photos"
    limit = "50"
    
    url = f"https://api.geoapify.com/v1/geocode/reverse?lat={latlong[0]}&lon={latlong[1]}&type=city&apiKey=66ec9b5933914a9baacdd17e5c3437f0"
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"

    response = requests.get(url, headers=headers)
    
    #Generates results for "<current city>'s Local Gems"
    if(response.status_code == 200): #Do we still have credits for today? 
        response = response.json()
        message = response["features"][0]["properties"]["city"]+"\'s Local Gems"
        ne = str(response["features"][0]["bbox"][3])+","+str(response["features"][0]["bbox"][2])
        sw = str(response["features"][0]["bbox"][1])+","+str(response["features"][0]["bbox"][0])
        
        url = f"https://api.foursquare.com/v3/places/search?categories={category}&exclude_all_chains=true&fields={fields}&min_price=3&open_now=true&ne={ne}&sw={sw}&limit=50"
        headers = {
            "Accept": "application/json",
            "Authorization": "fsq331oOD5fSvDUla7PwS5kJ8Ttw2V07DMrldp8XJxCU8mg="
        }
        response = requests.request("GET", url, headers=headers)
        response = response.json()
        
        fsq_results = [] #Results from fsq that will be modified and then returned.
    
        for poi in response["results"]:
            categories = []
            for category in poi["categories"]:
                categories.append(category["id"])
            dict = {
                "id": poi["fsq_id"], #FSQ id used to bind a restaurant with a gor value.
                "name": poi["name"],
                "gor": 0, #Our gor value (defaults to zero-- entire list is updated after.)
                "tel": poi["tel"] if ("tel" in poi) else None,
                "website": poi["website"] if ("website" in poi) else None,
                "price": poi["price"] if poi["price"] < 4 else 3,
                "location": poi["location"]["formatted_address"],
                "distance": poi["distance"],
                "categories": categories,
                "photo": poi["photos"][0]["prefix"] + "original" + poi["photos"][0]["suffix"] if ("photos" in poi and len(poi["photos"]) > 0) else None,
                "venue": "http://foursquare.com/v/" + poi["fsq_id"]
            }
            fsq_results.append(dict)
            
        put_restaurants(fsq_results)
        gor_results = get_restaurants(fsq_results)
        
        for poi in fsq_results:
            poi["gor"] = gor_results[poi["id"]]
        
        fsq_results.sort(reverse=True,key=get_gor)
        
        if(len(fsq_results) > 10):
            fsq_results = fsq_results[:10]
        
    return {
        'statusCode': 200,
        'body': fsq_results
    }
