from app import dailyMission

import os

airkey=os.environ['AIRTABLE_KEY']
airDB=os.environ['AIRTABLE_BASE_ID']


if __name__ == '__main__':
    os.environ['PROXY_URL'] = 'http://127.0.0.1:7890'

    dailyMission()