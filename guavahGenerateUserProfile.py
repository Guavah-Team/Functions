import json
import requests
from random import randrange

def lambda_handler(event, context):
    name = event['name'] + str(randrange(9999))
    
    url = f"https://avatars.dicebear.com/api/avataaars/jake%20speyer.svg?"
    
    response = requests.get(url)
    print(response.json())
    
    return {
        'statusCode': 200,
        'body': "Hello"
    }
