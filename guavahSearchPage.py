import json
import requests
import boto3
import math
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
###
# get restaurants takes in a list and performs a batch read.
# Should only be preformed after a batch write to ensure that
# all items in list are returned.
###


def get_restaurants(results):
    client = boto3.resource('dynamodb')
    table = client.Table('GuavahRestaurants')

    results_keys = []
    for poi in results:
        results_keys.append(poi["id"])

    batch_keys = {
        table.name: {
            'Keys': [{'FSQID': id} for id in results_keys]
        }
    }

    response = client.batch_get_item(RequestItems=batch_keys)
    response_dictionary = {}
    for poi in response['Responses']['GuavahRestaurants']:
        response_dictionary[poi["FSQID"]] = poi["GOR"]
    return response_dictionary

###
# Given the users current lattitude and longitude and a search radius
# calculate the upper right and bottom left corner of the box that this radius
# would have searched in (ne corner and sw corner).
#
# Used for large search radius' provided by the user (anything greater than 10 miles).
# These calculated values are then passed into calc_geocoding to slice this grid in half
# and return 100 results as opposed to 50 (limitations caused by the API we are using).
###


def get_ne_sw(latlong, radius):
    latlong = latlong.split(",")
    user_lat, user_long = latlong[0], latlong[1]
    radius_km = float(float(radius)/1000)

    ne = str(float(user_lat) + (radius_km / 6378) * (180/math.pi)) + \
        ","+str(float(user_long) + (radius_km / 6378) * (180/math.pi))
    sw = str(float(user_lat) - (radius_km / 6378) * (180/math.pi)) + \
        ","+str(float(user_long) - (radius_km / 6378) * (180/math.pi))
    return [ne, sw]

###
# calc_geocoding takes in the ne and sw geocode cordinates
# (recieved from geoapify and altered) to fit the foursquare syntax.
#
# Splits the provided geocode grid in half to increase the maximum amount
# of results returned by foursquare (since we are limited to 50 per call).
#
# Example:
# +---+      +---+
# |   |      |_1_|
# | 1 | ---> | 2 |
# +---+      +---+
# (50x)      (100x)
###


def calc_geocoding(ne, sw):
    ne_lat = ne.split(",")[0]
    ne_long = ne.split(",")[1]
    sw_lat = sw.split(",")[0]
    sw_long = sw.split(",")[1]

    # Calculating the mid right corner
    midpoint_1 = (str((float(ne_lat)+float(sw_lat))/2.0))+","+str(sw_long)
    midpoint_2 = (str((float(ne_lat)+float(sw_lat))/2.0))+","+str(ne_long)
    return [midpoint_1, midpoint_2]

###
# Takes in returned results from FSQ api, adds them to a list,
# and then returns it.
###


def add_results(response):
    # Results from fsq that will be modified and then returned.
    fsq_results = []
    for poi in response["results"]:
        categories = []
        for category in poi["categories"]:
            categories.append(category["id"])
        dict = {
            # FSQ id used to bind a restaurant with a gor value.
            "id": poi["fsq_id"],
            "name": poi["name"],
            # Our gor value (defaults to zero-- entire list is updated after.)
            "gor": 0,
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
    return fsq_results

###
# lambda_handler is the main method envoked by
# our api. Pings FSQ API and then cross refs our
# own NoSQL database for GOR score and reviews.
# Returns a list of dictionaries with POI data.
#
# If data is not found by FSQ we set that field to None.
###


def lambda_handler(event, context):
    status_code = 200
    # Results from fsq that will be modified and then returned.
    fsq_results = []

    radius = event['radius']  # 2000
    latlong = event['latlong']  # 41.8781%2C-87.6298
    term = event['term']  # Olive%20Garden
    is_open = event['isOpen']  # true
    category = event['category']  # 13000
    min_price = event['minPrice']  # 1
    max_price = event['maxPrice']  # 2
    do_chains = event['doChains']  # true
    fields = "fsq_id,name,description,tel,website,distance,price,categories,popularity,location,photos"
    limit = event['limit']  # 1

    # If it is a small search radius less than 10 miles
    if(float(radius) < 16254.37):
        url = f"https://api.foursquare.com/v3/places/search?query={term}&ll={latlong}&radius={radius}&categories={category}&exclude_all_chains={do_chains}&fields={fields}&min_price={min_price}&max_price={max_price}&open_now={is_open}&limit={limit}"

        headers = {
            "Accept": "application/json",
            "Authorization": "fsq331oOD5fSvDUla7PwS5kJ8Ttw2V07DMrldp8XJxCU8mg="
        }

        response = requests.request("GET", url, headers=headers)
        response = response.json()

        fsq_results = (add_results(response))

    # If it is a large search radius > than 10 miles
    else:
        corners = get_ne_sw(latlong, radius)
        midpoints = calc_geocoding(corners[0], corners[1])

        # First Sector
        url = f"https://api.foursquare.com/v3/places/search?query={term}&categories={category}&exclude_all_chains={do_chains}&fields={fields}&min_price={min_price}&max_price={max_price}&open_now={is_open}&sort=POPULARITY&ne={corners[0]}&sw={midpoints[0]}&limit=50"
        headers = {
            "Accept": "application/json",
            "Authorization": "fsq331oOD5fSvDUla7PwS5kJ8Ttw2V07DMrldp8XJxCU8mg="
        }
        response = requests.request("GET", url, headers=headers)
        response = response.json()
        fsq_results = (add_results(response))

        # Second Sector
        url = f"https://api.foursquare.com/v3/places/search?query={term}&categories={category}&exclude_all_chains={do_chains}&fields={fields}&min_price={min_price}&max_price={max_price}&open_now={is_open}&sort=POPULARITY&ne={midpoints[1]}&sw={corners[1]}&limit=50"
        headers = {
            "Accept": "application/json",
            "Authorization": "fsq331oOD5fSvDUla7PwS5kJ8Ttw2V07DMrldp8XJxCU8mg="
        }
        response = requests.request("GET", url, headers=headers)
        response = response.json()
        fsq_results.extend(add_results(response))

    if(len(fsq_results) > 0):
        put_restaurants(fsq_results)
        gor_results = get_restaurants(fsq_results)

        for poi in fsq_results:
            poi["gor"] = gor_results[poi["id"]]

        fsq_results.sort(reverse=True, key=get_gor)

        if(len(fsq_results) > 50):
            fsq_results = fsq_results[:50]
    else:
        status_code = 503

    return {
        'statusCode': status_code,
        'body': fsq_results
    }
