"""
MongoDB Sample Analytics Data Injector
Generates 24 hours of realistic historical data for testing analytics dashboard
"""

import sys
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING
import random
import math

# MongoDB connection
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "stampede_rakshak"

def connect_mongodb():
    """Connect to MongoDB"""
    print(f"\n[1/5] Connecting to MongoDB: {MONGO_URI}")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    print("[OK] Connected to MongoDB")
    return db

def check_existing_data(db):
    """Check if data already exists"""
    print("\n[2/5] Checking for existing data...")
    
    camera_count = db.camera_metrics.count_documents({})
    area_count = db.area_metrics.count_documents({})
    camera_hourly_count = db.camera_metrics_hourly.count_documents({})
    area_hourly_count = db.area_metrics_hourly.count_documents({})
    
    if camera_count > 0 or area_count > 0:
        print(f"[WARN] Found existing data:")
        print(f"  - Camera metrics: {camera_count}")
        print(f"  - Area metrics: {area_count}")
        print(f"  - Camera hourly: {camera_hourly_count}")
        print(f"  - Area hourly: {area_hourly_count}")
        
        response = input("\nDelete existing data and regenerate? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            print("[INFO] Deleting existing data...")
            db.camera_metrics.delete_many({})
            db.area_metrics.delete_many({})
            db.camera_metrics_hourly.delete_many({})
            db.area_metrics_hourly.delete_many({})
            print("[OK] Existing data deleted")
        else:
            print("[INFO] Keeping existing data, will add new data alongside it")

def get_entities(db):
    """Get cameras and areas from database"""
    print("\n[3/5] Loading cameras and areas...")
    
    cameras = list(db.cameras.find({}, {"camera_id": 1, "name": 1, "_id": 0}))
    areas = list(db.areas.find({}, {"area_id": 1, "name": 1, "_id": 0}))
    
    # If no cameras/areas, create defaults
    if not cameras:
        cameras = [
            {"camera_id": "cam_main", "name": "Main Entrance"},
            {"camera_id": "cam_north", "name": "North Gate"},
            {"camera_id": "cam_south", "name": "South Gate"}
        ]
        db.cameras.insert_many([
            {**cam, "stream_url": f"rtsp://example.com/{cam['camera_id']}", 
             "status": "active", "area_id": "area_main"}
            for cam in cameras
        ])
        print(f"[INFO] Created {len(cameras)} default cameras")
    
    if not areas:
        areas = [
            {"area_id": "area_main", "name": "Main Area"},
            {"area_id": "area_north", "name": "North Section"},
            {"area_id": "area_south", "name": "South Section"}
        ]
        db.areas.insert_many([
            {**area, "capacity": 500, "alert_threshold": 400}
            for area in areas
        ])
        print(f"[INFO] Created {len(areas)} default areas")
    
    print(f"[OK] Found {len(cameras)} cameras and {len(areas)} areas")
    return cameras, areas

def generate_realistic_metrics(hour_of_day, minute_of_hour, base_seed):
    """
    Generate realistic crowd metrics based on time of day
    Patterns: Low at night (0-5am), peaks at 9am, 1pm, 6pm
    """
    # Time-based pattern
    hour_factor = 0.1  # Base nighttime factor
    
    if 6 <= hour_of_day < 9:  # Morning buildup
        hour_factor = 0.3 + (hour_of_day - 6) * 0.2
    elif 9 <= hour_of_day < 12:  # Morning peak
        hour_factor = 0.9 - (hour_of_day - 9) * 0.1
    elif 12 <= hour_of_day < 14:  # Lunch peak
        hour_factor = 0.8 + (13 - hour_of_day) * 0.15
    elif 14 <= hour_of_day < 17:  # Afternoon moderate
        hour_factor = 0.5
    elif 17 <= hour_of_day < 19:  # Evening peak
        hour_factor = 0.7 + (18 - hour_of_day) * 0.15
    elif 19 <= hour_of_day < 22:  # Evening decline
        hour_factor = 0.6 - (hour_of_day - 19) * 0.15
    else:  # Night (22-6am)
        hour_factor = 0.1
    
    # Add minute-level variation (±20%)
    minute_variation = math.sin(minute_of_hour * math.pi / 30) * 0.2
    
    # Add random noise (±10%)
    random.seed(base_seed)
    noise = random.uniform(-0.1, 0.1)
    
    final_factor = max(0.05, min(1.0, hour_factor + minute_variation + noise))
    
    # Generate metrics
    people_count = int(final_factor * random.randint(60, 100))
    density = final_factor * random.uniform(0.8, 1.0)
    
    # Risk score correlates with density but not perfectly
    risk_score = min(100, density * 100 + random.uniform(-10, 10))
    
    # Calculate risk level
    if risk_score >= 80:
        risk_level = "CRITICAL"
    elif risk_score >= 60:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    return {
        "people_count": people_count,
        "density": round(density, 3),
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "avg_speed": round(random.uniform(0.5, 2.5), 2),
        "crowd_flow": round(random.uniform(10, 50), 2)
    }

def generate_historical_data(cameras, areas):
    """Generate 24 hours of minute-by-minute data"""
    print("\n[4/5] Generating 24 hours of realistic data...")
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    camera_metrics = []
    area_metrics = []
    
    current_time = start_time
    minute_count = 0
    
    while current_time <= end_time:
        minute_count += 1
        
        # Generate camera metrics
        for i, camera in enumerate(cameras):
            seed = int(current_time.timestamp()) + i
            metrics = generate_realistic_metrics(
                current_time.hour, 
                current_time.minute, 
                seed
            )
            
            camera_metrics.append({
                "camera_id": camera["camera_id"],
                "timestamp": current_time,
                **metrics
            })
        
        # Generate area metrics (aggregate of cameras in that area)
        for i, area in enumerate(areas):
            seed = int(current_time.timestamp()) + i + 1000
            metrics = generate_realistic_metrics(
                current_time.hour, 
                current_time.minute, 
                seed
            )
            
            # Areas have more people than individual cameras
            metrics["people_count"] = int(metrics["people_count"] * 1.5)
            
            area_metrics.append({
                "area_id": area["area_id"],
                "timestamp": current_time,
                **metrics
            })
        
        current_time += timedelta(minutes=1)
        
        # Progress indicator
        if minute_count % 120 == 0:
            hours_done = minute_count / 60
            print(f"  Generated {minute_count} minutes ({hours_done:.1f} hours)...")
    
    print(f"[OK] Generated {len(camera_metrics)} camera metrics and {len(area_metrics)} area metrics")
    return camera_metrics, area_metrics

def insert_raw_metrics(db, camera_metrics, area_metrics):
    """Insert raw minute-by-minute metrics"""
    print("\n[4.5/5] Inserting raw metrics into database...")
    
    if camera_metrics:
        db.camera_metrics.insert_many(camera_metrics)
        print(f"[OK] Inserted {len(camera_metrics)} camera metrics")
    
    if area_metrics:
        db.area_metrics.insert_many(area_metrics)
        print(f"[OK] Inserted {len(area_metrics)} area metrics")

def create_hourly_aggregates(db, camera_metrics, area_metrics, cameras, areas):
    """Create hourly aggregates for analytics"""
    print("\n[5/5] Creating hourly aggregates...")
    
    camera_hourly = []
    area_hourly = []
    
    # Group by hour
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    for hour_offset in range(25):  # 0 to 24 hours
        hour_time = start_time + timedelta(hours=hour_offset)
        hour_start = hour_time.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)
        
        # Camera hourly aggregates
        for camera in cameras:
            # Filter metrics for this camera and hour
            hourly_data = [
                m for m in camera_metrics 
                if m["camera_id"] == camera["camera_id"] 
                and hour_start <= m["timestamp"] < hour_end
            ]
            
            if hourly_data:
                avg_people = sum(m["people_count"] for m in hourly_data) / len(hourly_data)
                max_people = max(m["people_count"] for m in hourly_data)
                avg_density = sum(m["density"] for m in hourly_data) / len(hourly_data)
                avg_risk = sum(m["risk_score"] for m in hourly_data) / len(hourly_data)
                
                camera_hourly.append({
                    "camera_id": camera["camera_id"],
                    "hour_start": hour_start,
                    "hour_end": hour_end,
                    "avg_people": round(avg_people, 2),
                    "avg_people_count": round(avg_people, 2),
                    "max_people_count": max_people,
                    "avg_density": round(avg_density, 3),
                    "avg_risk_score": round(avg_risk, 2),
                    "data_points": len(hourly_data)
                })
        
        # Area hourly aggregates
        for area in areas:
            hourly_data = [
                m for m in area_metrics 
                if m["area_id"] == area["area_id"] 
                and hour_start <= m["timestamp"] < hour_end
            ]
            
            if hourly_data:
                avg_people = sum(m["people_count"] for m in hourly_data) / len(hourly_data)
                max_people = max(m["people_count"] for m in hourly_data)
                avg_density = sum(m["density"] for m in hourly_data) / len(hourly_data)
                avg_risk = sum(m["risk_score"] for m in hourly_data) / len(hourly_data)
                
                area_hourly.append({
                    "area_id": area["area_id"],
                    "hour": hour_start,
                    "avg_people_count": round(avg_people, 2),
                    "max_people_count": max_people,
                    "avg_density": round(avg_density, 3),
                    "avg_risk_score": round(avg_risk, 2),
                    "data_points": len(hourly_data)
                })
    
    if camera_hourly:
        db.camera_metrics_hourly.insert_many(camera_hourly)
        print(f"[OK] Inserted {len(camera_hourly)} camera hourly aggregates")
    
    if area_hourly:
        db.area_metrics_hourly.insert_many(area_hourly)
        print(f"[OK] Inserted {len(area_hourly)} area hourly aggregates")

def create_indexes(db):
    """Create indexes for hourly collections"""
    print("\n[FINAL] Creating indexes for hourly collections...")
    
    db.camera_metrics_hourly.create_index([("camera_id", ASCENDING), ("hour", ASCENDING)])
    db.area_metrics_hourly.create_index([("area_id", ASCENDING), ("hour", ASCENDING)])
    
    print("[OK] Indexes created")

def main():
    print("=" * 60)
    print("MongoDB Sample Analytics Data Injector")
    print("=" * 60)
    
    try:
        # Connect to MongoDB
        db = connect_mongodb()
        
        # Check existing data
        check_existing_data(db)
        
        # Get entities
        cameras, areas = get_entities(db)
        
        # Generate data
        camera_metrics, area_metrics = generate_historical_data(cameras, areas)
        
        # Insert raw metrics
        insert_raw_metrics(db, camera_metrics, area_metrics)
        
        # Create hourly aggregates
        create_hourly_aggregates(db, camera_metrics, area_metrics, cameras, areas)
        
        # Create indexes
        create_indexes(db)
        
        # Summary
        print("\n" + "=" * 60)
        print("[SUCCESS] Sample data injection complete!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  • Camera metrics: {len(camera_metrics)} records")
        print(f"  • Area metrics: {len(area_metrics)} records")
        print(f"  • Camera hourly: {len([m for m in camera_metrics if True]) // 60} records")
        print(f"  • Area hourly: {len([m for m in area_metrics if True]) // 60} records")
        print(f"  • Time range: {camera_metrics[0]['timestamp']} to {camera_metrics[-1]['timestamp']}")
        print("\nYou can now view analytics at: http://localhost:5500 (Analytics tab)")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to inject data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
