import json
import requests
from requests.structures import CaseInsensitiveDict
import boto3
import random
from botocore.exceptions import ClientError


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

    #Calculating the mid right corner
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


def lambda_handler(event, context):
    status_code = 200
    # Horizontal Field to be returned. (Outcome of this field will depend on if we have the credits to reverse geocode)
    section_a = ""
    section_b = ""  # Vertical Field to be returned.

    latlong = event['latlong'].split(",")  # 41.8781%2C-87.6298
    radius = event['radius']  # 2000
    category = "13000"
    fields = "fsq_id,name,description,tel,website,distance,price,categories,popularity,location,photos"
    limit = "50"

    fsq_results = []
    message_a = ""
    message_b = ""

    url = f"https://api.geoapify.com/v1/geocode/reverse?lat={latlong[0]}&lon={latlong[1]}&type=city&apiKey=66ec9b5933914a9baacdd17e5c3437f0"
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"

    response = requests.get(url, headers=headers)

    ########################################################################
    # ALL OF THIS IS FOR JUST SECTION A
    # SECTION B IS CALCULATED AFTER
    ########################################################################

    #Generates results for "<current city>'s Local Gems"
    if(response.status_code == 200):  # Do we still have credits for today?
        response = response.json()

        message_a = response["features"][0]["properties"]["city"] + \
            "\'s Local Gems"
        ne = str(response["features"][0]["bbox"][3])+"," + \
            str(response["features"][0]["bbox"][2])
        sw = str(response["features"][0]["bbox"][1])+"," + \
            str(response["features"][0]["bbox"][0])
        midpoints = calc_geocoding(ne, sw)

        #First Sector
        url = f"https://api.foursquare.com/v3/places/search?categories={category}&exclude_all_chains=true&fields={fields}&min_price=2&sort=POPULARITY&ne={ne}&sw={midpoints[0]}&limit=50"
        headers = {
            "Accept": "application/json",
            "Authorization": "fsq331oOD5fSvDUla7PwS5kJ8Ttw2V07DMrldp8XJxCU8mg="
        }
        response = requests.request("GET", url, headers=headers)
        response = response.json()
        fsq_results = (add_results(response))

        #Second Sector
        url = f"https://api.foursquare.com/v3/places/search?categories={category}&exclude_all_chains=true&fields={fields}&min_price=2&sort=POPULARITY&ne={midpoints[1]}&sw={sw}&limit=50"
        headers = {
            "Accept": "application/json",
            "Authorization": "fsq331oOD5fSvDUla7PwS5kJ8Ttw2V07DMrldp8XJxCU8mg="
        }
        response = requests.request("GET", url, headers=headers)
        response = response.json()
        fsq_results.extend(add_results(response))

    #Generates results for "Highest Rated Near You"
    else:
        message_a = "Highest Rated Near You"
        latlong = event['latlong']
        url = f"https://api.foursquare.com/v3/places/search?categories={category}&exclude_all_chains=false&fields={fields}&min_price=1&sort=POPULARITY&ll={latlong}&limit=50"
        headers = {
            "Accept": "application/json",
            "Authorization": "fsq331oOD5fSvDUla7PwS5kJ8Ttw2V07DMrldp8XJxCU8mg="
        }
        response = requests.request("GET", url, headers=headers)
        response = response.json()
        fsq_results = (add_results(response))

    if(len(fsq_results) > 0):
        #Triggers regardless of the content of section a
        put_restaurants(fsq_results)
        gor_results = get_restaurants(fsq_results)

        for poi in fsq_results:
            poi["gor"] = gor_results[poi["id"]]

        fsq_results.sort(reverse=True, key=get_gor)

        if(len(fsq_results) > 10):
           section_a = fsq_results[:10]
        else:
            section_a = fsq_results
    else:
        status_code = 503

    ########################################################################
    # ALL OF THIS IS FOR JUST SECTION B
    ########################################################################
    category_taxonomy = {
        13002: "Best Bakeries",
        13003: "Bars With Game",
        13032: "Killer Cafés",
        13040: "Sinful Desserts",
        13026: "Best Backyard BBQ",
        13039: "Feeling Like A Sandwich?",
        13382: "Refuel On Snacks"
    }
    do_chains = "true"
    category, message_b = random.choice(list(category_taxonomy.items()))

    if(category == 13032):
        do_chains = "false"

    latlong = event['latlong']

    url = f"https://api.foursquare.com/v3/places/search?categories={category}&exclude_all_chains={do_chains}&fields={fields}&min_price=1&sort=POPULARITY&ll={latlong}&limit=50"
    headers = {
        "Accept": "application/json",
        "Authorization": "fsq331oOD5fSvDUla7PwS5kJ8Ttw2V07DMrldp8XJxCU8mg="
    }
    response = requests.request("GET", url, headers=headers)
    response = response.json()
    fsq_results = add_results(response)

    #Triggers regardless of the content of section b
    if(len(fsq_results) > 0):
        put_restaurants(fsq_results)
        gor_results = get_restaurants(fsq_results)

        for poi in fsq_results:
            poi["gor"] = gor_results[poi["id"]]

        fsq_results.sort(reverse=True, key=get_gor)
        section_b = fsq_results
    else:
        status_code = 503

    return {
        'statusCode': status_code,
        'messageA': message_a,
        'messageB': message_b,
        'sectionA': section_a,
        'sectionB': section_b
    }
