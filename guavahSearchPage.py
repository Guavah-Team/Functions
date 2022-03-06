import json
import requests
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
# put_restaurant takes in an id and assigns a default gor value
# of 150. Places this value as an Item into the DyanmoDB table.
###
def put_restaurant(id, gor=150):
    client = boto3.resource('dynamodb')
    table = client.Table('GuavahRestaurants')

    response = table.put_item(
       Item={
            'FSQID': id,
            'GOR': gor
        }
    )

###
# get_restaurant takes in an id and attempts to get it from the table.
# if it does not find the restaurant in the table it will throw an error.
# ALL CALLS MUST BE PLACED IN A TRY EXCEPT BLOCK!
###
def get_restaurant(id):
    client = boto3.resource('dynamodb')
    table = client.Table('GuavahRestaurants')
    response = table.get_item(
        Key={
            'FSQID': id
        }
    )
    return response["Item"]

###
# lambda_handler is the main method envoked by
# our api. Pings FSQ API and then cross refs our
# own NoSQL database for GOR score and reviews.
# Returns a list of dictionaries with POI data.
#
# If data is not found by FSQ we set that field to None.
###
def lambda_handler(event, context):
    radius = event['radius'] #2000
    latlong = event['latlong'] #41.8781%2C-87.6298
    term = event['term'] #Olive%20Garden
    is_open = event['isOpen'] #true
    category = event['category'] #13000
    min_price = event['minPrice'] #1
    max_price = event['maxPrice'] #2
    do_chains = event['doChains'] #true
    fields = event['fields'] #fsq_id,name,description,tel,website,distance,price,categories,popularity,location,photos
    limit = event['limit'] #1
    
    url = f"https://api.foursquare.com/v3/places/search?query={term}&ll={latlong}&radius={radius}&categories={category}&exclude_all_chains={do_chains}&fields={fields}&min_price={min_price}&max_price={max_price}&open_now={is_open}&limit={limit}"

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
        
    for poi in fsq_results:
        resp = {}
        try:
            resp = get_restaurant(poi["id"])
        except:
            put_restaurant(poi["id"])
            resp = get_restaurant(poi["id"])
        finally:
            poi["gor"] = resp["GOR"]
            poi["reviews"] = resp["reviews"]
            
    fsq_results.sort(reverse=True,key=get_gor)
    
    return {
        'statusCode': 200,
        'body': fsq_results
    }
