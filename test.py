from app import dailyMission
import os

if __name__ == '__main__':
    os.environ['PROXY_URL'] = 'http://127.0.0.1:7890'
    dailyMission()