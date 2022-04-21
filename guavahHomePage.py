import json
import requests
from requests.structures import CaseInsensitiveDict
import boto3
import random
import botocore

client = boto3.resource('dynamodb')
table = client.Table('GuavahRestaurants')

###
# Picks the rank icon based on their current gor value
###
def pick_rank_icons(restaurants):
    rungs = [0, 91, 181, 271, 361, 451, 541, 631, 721, 811, 901, 1000]
    
    
    for restaurant in restaurants:
        for i in range(len(rungs)):
            if restaurant["gor"] < rungs[i]:
                restaurant["badge"] = f"https://guavah-image-bucket.s3.us-west-1.amazonaws.com/ranks/gor_{rungs[i-1]}.png"
                break


###
# top_image generates the random image at the top of the application.
###
def top_image():
    images = {
        "message_1": "https://guavah-image-bucket.s3.us-west-1.amazonaws.com/home/message_1.jpg",
        "message_2": "https://guavah-image-bucket.s3.us-west-1.amazonaws.com/home/message_2.jpg",
        "message_3": "https://guavah-image-bucket.s3.us-west-1.amazonaws.com/home/message_3.jpg",
        "message_4": "https://guavah-image-bucket.s3.us-west-1.amazonaws.com/home/message_4.jpg",
        "message_5": "https://guavah-image-bucket.s3.us-west-1.amazonaws.com/home/message_5.jpg",
        "message_6": "https://guavah-image-bucket.s3.us-west-1.amazonaws.com/home/message_6.jpg",
        "message_7": "https://guavah-image-bucket.s3.us-west-1.amazonaws.com/home/message_7.jpg",
        "message_8": "https://guavah-image-bucket.s3.us-west-1.amazonaws.com/home/message_8.jpg"
    }
    
    messages = {
        "message_1": ["Tired?","Coffee is calling your name!"],
        "message_2": ["Staying in tonight?","Find the best takeout!"],
        "message_3": ["Celebrating?","Find the best drinks!"],
        "message_4": ["Dining alone?","Find the best bars!"],
        "message_5": ["Have a party?","Let's celebrate!"],
        "message_6": ["Feeling fancy?","We're way ahead of you."],
        "message_7": ["Love the crunch?","Find the best sandwiches!"],
        "message_8": ["BBQ better than","your dad's. Sorry."]   
    }
    
    urls = {
        "message_1": f"todo",
        "message_2": f"todo",
        "message_3": f"todo",
        "message_4": f"todo",
        "message_5": f"todo",
        "message_6": f"todo",
        "message_7": f"todo",
        "message_8": f"todo"   
    }

    message_index = random.choice(list(images))
    
    return {
        "image": images.get(message_index),
        "message_1": messages.get(message_index)[0],
        "message_2": messages.get(message_index)[1],
        "url": urls.get(message_index)
    }
    

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
    for poi in results:        
        try:
            table.put_item(
                Item={
                    'FSQID': poi["id"],
                    'GOR': poi["gor"],
                },
                ConditionExpression='attribute_not_exists(FSQID)'
            )
        except botocore.exceptions.ClientError as e:
            pass
            
###
# get restaurants takes in a list and performs a batch read.
# Should only be preformed after a batch write to ensure that
# all items in list are returned.
###


def get_restaurants(results):
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
    photo_placeholder = "https://guavah-image-bucket.s3.us-west-1.amazonaws.com/placeholders/placeholder_deli.jpg"
    for poi in response["results"]:
        categories = []
        for category in poi["categories"]:
            categories.append(category["id"])
        
        photo_gallary = []
        if len(poi["photos"]) > 0:
            total_photos = 0
            for photo in poi["photos"]:
                if total_photos < 10:
                    photo_gallary.append({"photo": photo["prefix"] + "original" + photo["suffix"]})
            
                    
        dict = {
            # FSQ id used to bind a restaurant with a gor value.
            "id": poi["fsq_id"],
            "name": poi["name"],
            # Our gor value (defaults to zero-- entire list is updated after.)
            "gor": 200,
            "tel": poi["tel"] if ("tel" in poi) else None,
            "website": poi["website"] if ("website" in poi) else None,
            "price": poi["price"] if poi["price"] < 4 else 3,
            "location": poi["location"]["formatted_address"],
            "distance": poi["distance"],
            "categories": categories,
            "photo": poi["photos"][0]["prefix"] + "original" + poi["photos"][0]["suffix"] if ("photos" in poi and len(poi["photos"]) > 0) else photo_placeholder,
            "photo_gallary": photo_gallary,
            "badge": "https://guavah-image-bucket.s3.us-west-1.amazonaws.com/ranks/gor_0.png",
            "venue": "http://foursquare.com/v/" + poi["fsq_id"]
        }
        if "rating" in poi:
            dict["gor"] = int((poi["rating"]/10) * 370)
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
    fields = "fsq_id,name,description,tel,website,distance,price,categories,popularity,location,photos,hours,rating"
    limit = "50"

    fsq_results = []
    message_a = ""
    message_b = ""
    
    
    url = f"https://api.geoapify.com/v1/geocode/reverse?lat={latlong[0]}&lon={latlong[1]}&type=city&apiKey=66ec9b5933914a9baacdd17e5c3437f0"
    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"

    response = requests.get(url, headers=headers, timeout=1)
    #response = geo.reverse(query=(latlong[0], latlong[1]), exactly_one=True, timeout=5)

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
        url = f"https://api.foursquare.com/v3/places/search?categories={category}&exclude_all_chains=True&fields={fields}&min_price=2&sort=POPULARITY&ne={ne}&sw={midpoints[0]}&limit=50"
        headers = {
            "Accept": "application/json",
            "Authorization": "fsq331oOD5fSvDUla7PwS5kJ8Ttw2V07DMrldp8XJxCU8mg="
        }
        response = requests.request("GET", url, headers=headers)
        response = response.json()
        fsq_results = (add_results(response))

        #Second Sector
        url = f"https://api.foursquare.com/v3/places/search?categories={category}&exclude_all_chains=True&fields={fields}&min_price=2&sort=POPULARITY&ne={midpoints[1]}&sw={sw}&limit=50"
        headers = {
            "Accept": "application/json",
            "Authorization": "fsq331oOD5fSvDUla7PwS5kJ8Ttw2V07DMrldp8XJxCU8mg="
        }
        response = requests.request("GET", url, headers=headers, timeout=1)
        response = response.json()
        fsq_results.extend(add_results(response))

    #Generates results for "Highest Rated Near You"
    else:
        message_a = "Highest Rated Near You"
        latlong = event['latlong']
        url = f"https://api.foursquare.com/v3/places/search?categories={category}&exclude_all_chains=True&fields={fields}&min_price=1&sort=POPULARITY&ll={latlong}&limit=50&radius=16093"
        headers = {
            "Accept": "application/json",
            "Authorization": "fsq331oOD5fSvDUla7PwS5kJ8Ttw2V07DMrldp8XJxCU8mg="
        }
        response = requests.request("GET", url, headers=headers, timeout=1)
        response = response.json()
        fsq_results = (add_results(response))

    if(len(fsq_results) > 0):
        #Triggers regardless of the content of section a
        put_restaurants(fsq_results)
        gor_results = get_restaurants(fsq_results)

        for poi in fsq_results:
            poi["gor"] = gor_results[poi["id"]]

        fsq_results.sort(reverse=True, key=get_gor)
        pick_rank_icons(fsq_results)

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
        13039: "Feeling Like A Sandwich?"
    }
    do_chains = "true"
    category, message_b = random.choice(list(category_taxonomy.items()))

    if(category == 13032):
        do_chains = "false"
    b_latlong = event['latlong']
    url = f"https://api.foursquare.com/v3/places/search?categories={category}&exclude_all_chains=True&fields={fields}&min_price=1&sort=POPULARITY&ll={b_latlong}&limit=50&radius=16093"
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
        pick_rank_icons(section_b)
    else:
        status_code = 503
        
    ########################################################################
    # ALL OF THIS IS FOR JUST SECTION C
    ########################################################################
    section_c = top_image()
    

    return {
        'statusCode': status_code,
        'messageA': message_a,
        'messageB': message_b,
        'sectionA': section_a,
        'sectionB': section_b,
        'sectionC': section_c
    }
