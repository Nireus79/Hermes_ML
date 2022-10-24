import os
from licensespring.api import APIClient

# https://docs.licensespring.com/docs/apiclient-usage-examples
API_KEY_SPRING = 'd83ddf36-82a5-4a02-a518-4768e2bd1336'
SHARED_KEY_SPRING = 'e0KHZ_GDkW9VteqB6ZlnvWsbr63RL8VANyu51OlIyIA'
LICENCE_KEY_SPRING = os.environ['LICENCE_KEY_SPRING']
product = "h1"
api_client = APIClient(api_key=API_KEY_SPRING, shared_key=SHARED_KEY_SPRING)


# Activate key based license
def activation():
    activate_key = api_client.activate_license(product=product, license_key=LICENCE_KEY_SPRING)
    return activate_key


# Check key based license
def check():
    check_key = api_client.check_license(product=product, license_key=LICENCE_KEY_SPRING)
    return check_key
