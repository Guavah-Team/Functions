import json
import boto3
import random
from random import randrange
from time import gmtime, strftime
from botocore.exceptions import ClientError

#Shuffle the name into random letters and numbers
def shuffle_name(name):
    hashed_name = []
    for char in name:
        if ord(char) % 2 == 0:
            hashed_name.append(str(randrange(99)))
        else:
            diceroll = randrange(2)
            if diceroll == 1:
                hashed_name.append(str(chr(randrange(65, 90))))
            elif diceroll == 2:
                hashed_name.append(str(chr(randrange(97, 122))))
    return ''.join(hashed_name)

#Generate a random valid hexcode
def shuffle_color():
    color = []
    for hex in range(6):
        hex = str(randrange(15))
        if hex == '10':
            hex = 'a'
        elif hex == '11':
            hex = 'b'
        elif hex == '12':
            hex = 'c'
        elif hex == '13':
            hex = 'd'
        elif hex == '14':
            hex = 'e'
        elif hex == '15':
            hex = 'f'
        color.append(hex)
    return ''.join(color)

#Should the profile be flipped on the y-axis
def shuffle_flip():
    diceroll = randrange(2)
    return 'false' if diceroll == 1 else 'true'

#Used to pick a gender neutral mouth (Removed ones with lipstick)
def shuffle_mouth():
    mouths = ["01", "02", "03", "04", "09", "10", "11", "12", "13", "14", "15", "16",
              "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30"]
    return "variant" + random.choice(mouths)

#Shuffles the rotation of the users head randomly
def shuffle_rotate():
    rotate = '0'
    diceroll = randrange(8)
    if diceroll == 2:
        rotate = '345'
    if diceroll == 6:
        rotate = '15'
    return rotate

#Generate a new profile photo
def generateProfilePhoto(username):
    name = shuffle_name(username)
    color = shuffle_color()
    flip = shuffle_flip()
    mouth = shuffle_mouth()
    rotate = shuffle_rotate()

    url = f"https://avatars.dicebear.com/api/adventurer-neutral/:{name}.svg?backgroundColor=%23{color}&flip={flip}&accessoiresProbability=40&mouth={mouth}&rotate={rotate}&radius=50"
    #webbrowser.open(url, new=2)
    return url


#Write user data to the GuavahUsers table in DynamoDB
def put_user(user_ID, name, email, dt):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('GuavahUsers')
    response = table.put_item(
       Item={
            'UserID': user_ID,
            'Name': name,
            'Email': email,
            'CreatedAt': dt,
            'Level': 0,
            'XP': 0,
            'DarkTheme': 0,
            'Vegan': 0,
            'Radius': 8046,
            'VersusViews': {},
            'VersusQueue': [],
            'VersusPairs': [],
            'DailyVotes': 0,
            'Badges': [],
            'ProfilePhoto': generateProfilePhoto(name)
        }
    )
    return response


def lambda_handler(event, context):
    
    #Get user info from Cognito event
    user_ID = event['userName']
    name = event['request']['userAttributes']['name']
    email = event['request']['userAttributes']['email']
    
    #Current date
    dt = strftime("%Y-%m-%d %H:%M:%S", gmtime())
    dt = str(dt)
    
    #Writes to DynamoDB
    #NOTICE: A new user account will be successffully created despite this function failing.
    #If this function fails, user data will NOT be available in DynamoDB.
    put_user(user_ID, name, email, dt)
   
    return event
