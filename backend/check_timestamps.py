from pymongo import MongoClient
from datetime import datetime, timedelta

client = MongoClient('mongodb://localhost:27017')
db = client['stampede_rakshak']

now = datetime.utcnow()
one_hour_ago = now - timedelta(hours=1)
one_day_ago = now - timedelta(hours=24)

count_1h = db.camera_metrics.count_documents({'camera_id': 'cam_stampede', 'timestamp': {'$gte': one_hour_ago}})
count_24h = db.camera_metrics.count_documents({'camera_id': 'cam_stampede', 'timestamp': {'$gte': one_day_ago}})
count_all = db.camera_metrics.count_documents({'camera_id': 'cam_stampede'})

print(f'Documents in last hour: {count_1h}')
print(f'Documents in last 24 hours: {count_24h}')
print(f'Total documents: {count_all}')
print(f'\nNow: {now}')
print(f'One hour ago: {one_hour_ago}')
print(f'One day ago: {one_day_ago}')

latest = db.camera_metrics.find_one({'camera_id': 'cam_stampede'}, sort=[('timestamp', -1)])
oldest = db.camera_metrics.find_one({'camera_id': 'cam_stampede'}, sort=[('timestamp', 1)])

if latest:
    print(f'\nLatest timestamp: {latest.get("timestamp")}')
if oldest:
    print(f'Oldest timestamp: {oldest.get("timestamp")}')
