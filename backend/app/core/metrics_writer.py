"""
Metrics Writer - Non-blocking MongoDB persistence with retry queue
CRITICAL: Never blocks camera pipelines - uses async queue with backpressure
"""
import asyncio
import time
from typing import Dict, Any, Optional
from collections import deque

from app.db.connection import get_database, is_db_connected
from app.db.repositories import MetricsRepository


class MetricsWriter:
    """
    Async writer with retry queue for MongoDB metrics persistence
    
    Design principles:
    - Never block camera pipelines
    - Graceful degradation if MongoDB fails
    - Drop oldest metrics if queue overflows
    - Exponential backoff on failures
    """
    
    def __init__(self, queue_size: int = 500, write_interval: float = 1.0):
        """
        Args:
            queue_size: Maximum metrics batches to buffer (default 500 = ~8 minutes)
            write_interval: Write frequency in seconds (default 1Hz)
        """
        self.queue = asyncio.Queue(maxsize=queue_size)
        self.write_interval = write_interval
        self.running = False
        self.writer_task: Optional[asyncio.Task] = None
        
        # Health metrics
        self.metrics_written = 0
        self.metrics_dropped = 0
        self.metrics_dropped_last_hour = 0
        self.last_hour_reset = time.time()
        self.last_write_time = 0.0
        self.last_error: Optional[str] = None
        self.consecutive_failures = 0
        
        # Retry configuration
        self.max_retries = 3
        self.base_backoff = 1.0  # seconds
    
    async def start(self):
        """Start the writer task"""
        if not self.running:
            self.running = True
            self.writer_task = asyncio.create_task(self._write_loop())
            print("[MetricsWriter] Started")
    
    async def stop(self):
        """Stop the writer task"""
        self.running = False
        if self.writer_task:
            await self.writer_task
        print("[MetricsWriter] Stopped")
    
    async def enqueue(self, metrics: Dict[str, Any]):
        """
        Enqueue metrics for writing (non-blocking)
        
        Args:
            metrics: Dictionary with 'cameras' and 'areas' metrics
        """
        try:
            # Non-blocking put
            self.queue.put_nowait(metrics)
        except asyncio.QueueFull:
            # Queue full - drop oldest metrics to make room
            try:
                self.queue.get_nowait()  # Remove oldest
                self.queue.put_nowait(metrics)  # Add new
                self.metrics_dropped += 1
                self.metrics_dropped_last_hour += 1
                
                # Log warning periodically
                if self.metrics_dropped % 100 == 1:
                    print(f"[MetricsWriter] ⚠️  Queue full - dropped {self.metrics_dropped} metrics total")
            except:
                # Rare race condition - just drop
                self.metrics_dropped += 1
                self.metrics_dropped_last_hour += 1
    
    async def _write_loop(self):
        """Main write loop - pulls from queue and writes to MongoDB"""
        print(f"[MetricsWriter] Write loop started (interval: {self.write_interval}s)")
        
        while self.running:
            try:
                # Wait for interval or queue item
                try:
                    metrics = await asyncio.wait_for(
                        self.queue.get(), 
                        timeout=self.write_interval
                    )
                except asyncio.TimeoutError:
                    # No data this interval
                    await asyncio.sleep(0.1)
                    continue
                
                # Try to write with retries
                success = await self._write_with_retry(metrics)
                
                if success:
                    self.metrics_written += 1
                    self.consecutive_failures = 0
                    self.last_write_time = time.time()
                    self.last_error = None
                else:
                    self.metrics_dropped += 1
                    self.metrics_dropped_last_hour += 1
                
                # Reset hourly counter
                if time.time() - self.last_hour_reset > 3600:
                    self.metrics_dropped_last_hour = 0
                    self.last_hour_reset = time.time()
                
            except Exception as e:
                print(f"[MetricsWriter] Unexpected error in write loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _write_with_retry(self, metrics: Dict[str, Any]) -> bool:
        """
        Write metrics with exponential backoff retry
        
        Returns:
            True if write succeeded, False if all retries failed
        """
        for attempt in range(self.max_retries):
            try:
                # Check if DB is connected
                if not is_db_connected():
                    if attempt == 0:
                        self.last_error = "MongoDB not connected"
                    return False
                
                db = get_database()
                if db is None:
                    self.last_error = "Database instance is None"
                    return False
                
                repo = MetricsRepository(db)
                
                # Prepare camera metrics batch
                camera_docs = []
                for cam_id, cam_metrics in metrics.get('cameras', {}).items():
                    doc = dict(cam_metrics)  # Copy
                    doc['camera_id'] = cam_id
                    camera_docs.append(doc)
                
                # Prepare area metrics batch
                area_docs = []
                for area_id, area_metrics in metrics.get('areas', {}).items():
                    doc = dict(area_metrics)  # Copy
                    doc['area_id'] = area_id
                    area_docs.append(doc)
                
                # Bulk insert (non-blocking async)
                if camera_docs:
                    await repo.bulk_insert_camera_metrics(camera_docs)
                if area_docs:
                    await repo.bulk_insert_area_metrics(area_docs)
                
                # Success
                return True
                
            except Exception as e:
                self.last_error = str(e)
                self.consecutive_failures += 1
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    backoff = self.base_backoff * (2 ** attempt)
                    await asyncio.sleep(backoff)
                else:
                    # All retries failed
                    if self.consecutive_failures == 1:  # Log first failure only
                        print(f"[MetricsWriter] ❌ Write failed after {self.max_retries} retries: {e}")
                    return False
        
        return False
    
    def get_health(self) -> Dict[str, Any]:
        """Get health metrics for /health endpoint"""
        queue_depth = self.queue.qsize()
        
        # Determine status
        if not is_db_connected():
            status = "disconnected"
        elif self.consecutive_failures > 5:
            status = "degraded"
        elif queue_depth > 400:
            status = "critical"
        elif queue_depth > 100:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "mongo_status": status,
            "metrics_queue_depth": queue_depth,
            "metrics_written": self.metrics_written,
            "metrics_dropped": self.metrics_dropped,
            "metrics_dropped_last_hour": self.metrics_dropped_last_hour,
            "last_write_time": self.last_write_time,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures
        }


# Global singleton
metrics_writer = MetricsWriter(queue_size=500, write_interval=1.0)
