###################################################################################################  
# 
# Code for scraping YELP data and pushing it to DynamoDB and indexing to Opensearch (ES)
# Authors: Shubhkirti Sharma (wowufoundme) & Rijul Nandy (rijul10)
# 
################################################################################################### 

################################################################################################### 
# Imports
################################################################################################### 
import boto3
import datetime
import requests
from decimal import *
from time import sleep
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

################################################################################################### 
# Global Variables [Remember to not publicly expose these variables]
################################################################################################### 
aws_access_key_id       = ""
aws_secret_access_key   = ""
region                  = ""
service                 = ""
host                    = ""

################################################################################################### 
# Create BOTO3 client with dynamoDB paramater and IAM access keys
################################################################################################### 
client = boto3.resource (
                            service_name            = "",
                            aws_access_key_id       = "",
                            aws_secret_access_key   = "",
                            region_name             = "",
                        )

################################################################################################### 
# Initialize DynamoDB table
################################################################################################### 
table = client.Table('yelp-restaurants-db')

################################################################################################### 
# Create authentication client and access
################################################################################################### 
auth = AWS4Auth(aws_access_key_id, aws_secret_access_key, region, service)

################################################################################################### 
# Create OpenSearch client
################################################################################################### 
es = OpenSearch(
    hosts = [
        {
            'host' : host, 
            'port' : 443
        }
    ],
    http_auth = auth,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection
)
restaurants = {}
def addItems(data, cuisine):
    print("Writing batch for... ", cuisine)
    global restaurants
    with table.batch_writer() as batch:
            for rec in data:
                esData = {}
                try:
                    # Check if restaurant is already processed
                    if rec["alias"] in restaurants:
                        continue;

                    
                    # Creating data for ES Search Indexing
                    esData['cuisine'] = cuisine
                    esData['Business ID'] = str(rec["id"])

                    # Creating data for DynamoDB objects
                    rec["Business ID"] = str(rec["id"])
                    rec["rating"] = Decimal(str(rec["rating"]))
                    restaurants[rec["alias"]] = 0
                    rec['cuisine'] = cuisine
                    rec['insertedAtTimestamp'] = str(datetime.datetime.now())
                    rec["coordinates"]["latitude"] = Decimal(str(rec["coordinates"]["latitude"]))
                    rec["coordinates"]["longitude"] = Decimal(str(rec["coordinates"]["longitude"]))
                    rec['address'] = rec['location']['display_address']
                    rec['zip_code'] = " ".join(rec['address']).split(" ")[-1]
                    rec.pop("distance", None)
                    rec.pop("location", None)
                    rec.pop("transactions", None)
                    rec.pop("display_phone", None)
                    rec.pop("categories", None)
                    if rec["phone"] == "":
                        rec.pop("phone", None)
                    if rec["image_url"] == "":
                        rec.pop("image_url", None)
          
                    batch.put_item(Item = rec)
                    
                    es.index(index = "yelp-restaurants", doc_type = "Restaurants", body = esData)

                    sleep(0.01)
                except Exception as e:
                    print("")
    print("Written batch for... ", cuisine)
################################################################################################### 

# YELP API HIT POINT 
# Change cuisine acccording to the list given below every time and run it for each instance
# cuisines = ['indian', 'thai', 'mediterranean', 'chinese', 'italian']

################################################################################################### 
cuisines = ['italian']

################################################################################################### 
# Paste your YELP API key below
################################################################################################### 
api_key = ""
headers = {'Authorization': 'Bearer {}'.format(api_key)}

################################################################################################### 
# Start scraping data and hit ES endpoint
################################################################################################### 
LOCATIONS = [ 'Manhattan', 'Brooklyn', 'Bronx', 'Queens', 'Staten Island' ]
for LOCATION in LOCATIONS:
    for cuisine in cuisines:
        for i in range(0, 1000, 50):
            params = {
                'location' : LOCATION, 
                'offset' : i, 
                'limit' : 50, 
                'term' : cuisine + " restaurants"
            }
            response = requests.get("https://api.yelp.com/v3/businesses/search", headers = headers, params = params, timeout = None)
            js = response.json()
            addItems(js["businesses"], cuisine)
            response.close()