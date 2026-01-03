import asyncio
from pymongo import MongoClient
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient

async def test_query():
    # Use Motor for async
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['stampede_rakshak']
    collection = db['camera_metrics']
    
    camera_id = 'cam_stampede'
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=48)
    
    print(f"Querying for camera: {camera_id}")
    print(f"Start time: {start_time}")
    print(f"End time: {end_time}")
    
    query = {
        "camera_id": camera_id,
        "timestamp": {"$gte": start_time, "$lte": end_time}
    }
    
    cursor = collection.find(query).sort("timestamp", -1).limit(10)
    results = []
    async for doc in cursor:
        doc.pop('_id', None)
        if isinstance(doc.get('timestamp'), datetime):
            doc['timestamp'] = doc['timestamp'].timestamp()
        results.append(doc)
    
    print(f"\nFound {len(results)} documents")
    if results:
        print("\nFirst document:")
        print(results[0])
        print("\nLast document:")
        print(results[-1])
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_query())
    print(f"\nTotal results: {len(results)}")
