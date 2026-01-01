"""
MongoDB Connection Manager
Async Motor driver for FastAPI with graceful degradation
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import os


class DatabaseManager:
    """Singleton MongoDB connection manager"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.connected: bool = False
        
        # Connection string from env or default (localhost, no auth)
        self.connection_string = os.getenv(
            "MONGODB_URL", 
            "mongodb://localhost:27017"
        )
        self.database_name = os.getenv("MONGODB_DB", "stampede_rakshak")
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            print(f"[MongoDB] Connecting to {self.connection_string}")
            self.client = AsyncIOMotorClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000  # 5 second timeout
            )
            self.db = self.client[self.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            self.connected = True
            print(f"[MongoDB] ✅ Connected to database: {self.database_name}")
            
            # Create indexes
            await self._create_indexes()
            print("[MongoDB] ✅ Indexes created")
            
        except Exception as e:
            self.connected = False
            print(f"[MongoDB] ❌ Connection failed: {e}")
            print("[MongoDB] System will run without persistence (graceful degradation)")
            # Don't raise - allow system to continue without persistence
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.connected = False
            print("[MongoDB] Disconnected")
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        if self.db is None or not self.connected:
            return
        
        try:
            # Camera indexes
            await self.db.cameras.create_index("camera_id", unique=True)
            await self.db.cameras.create_index("enabled")
            
            # Area indexes
            await self.db.areas.create_index("area_id", unique=True)
            await self.db.areas.create_index("enabled")
            
            # Metrics history indexes (for time-series queries)
            await self.db.camera_metrics.create_index([
                ("camera_id", 1),
                ("timestamp", -1)
            ])
            # TTL index - auto-delete after 7 days (604800 seconds)
            await self.db.camera_metrics.create_index(
                "timestamp", 
                expireAfterSeconds=604800
            )
            
            # Area metrics history
            await self.db.area_metrics.create_index([
                ("area_id", 1),
                ("timestamp", -1)
            ])
            await self.db.area_metrics.create_index(
                "timestamp", 
                expireAfterSeconds=604800
            )
            
        except Exception as e:
            print(f"[MongoDB] Warning: Index creation failed: {e}")
    
    def get_database(self) -> Optional[AsyncIOMotorDatabase]:
        """Get database instance (returns None if not connected)"""
        return self.db if self.connected else None
    
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self.connected


# Global instance
db_manager = DatabaseManager()


async def init_db():
    """Initialize database connection"""
    await db_manager.connect()


async def close_db():
    """Close database connection"""
    await db_manager.disconnect()


def get_database() -> Optional[AsyncIOMotorDatabase]:
    """Get database instance for use in routes (returns None if disconnected)"""
    return db_manager.get_database()


def is_db_connected() -> bool:
    """Check if MongoDB is available"""
    return db_manager.is_connected()
