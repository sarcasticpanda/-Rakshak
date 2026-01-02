"""
Metrics Aggregator - Pulls metrics @ 1Hz and broadcasts
Never blocks pipelines
"""
import asyncio
import time
from typing import Dict, Set, Any
from collections import deque
from app.core.shared_store import shared_store
from app.core.area_risk_engine import area_risk_engine
from app.core.metrics_writer import metrics_writer


class MetricsAggregator:
    """
    Aggregates metrics from all cameras and broadcasts @ 1Hz
    
    Design:
    - Pulls from SharedStore (never blocks pipelines)
    - Throttles to 1Hz (frontend doesn't need 30 FPS metrics)
    - Maintains connection registry
    """
    
    def __init__(self, broadcast_interval: float = 1.0):
        """
        Args:
            broadcast_interval: Seconds between broadcasts (default 1Hz)
        """
        self.broadcast_interval = broadcast_interval
        self.websocket_connections: Set = set()
        self.running = False
        self.aggregator_task = None
        
        # Metrics history for smoothing
        self.metrics_history: Dict[str, deque] = {}
        self.history_size = 5  # Keep last 5 seconds
    
    def register_connection(self, websocket) -> None:
        """Register new WebSocket connection"""
        self.websocket_connections.add(websocket)
        print(f"[MetricsAggregator] Connection registered. Total: {len(self.websocket_connections)}")
    
    def unregister_connection(self, websocket) -> None:
        """Unregister WebSocket connection"""
        self.websocket_connections.discard(websocket)
        print(f"[MetricsAggregator] Connection closed. Total: {len(self.websocket_connections)}")
    
    async def collect_and_broadcast(self) -> None:
        """
        Main loop - collect metrics and broadcast
        Runs continuously @ 1Hz
        """
        self.running = True
        print(f"[MetricsAggregator] Started (broadcast interval: {self.broadcast_interval}s)")
        
        while self.running:
            try:
                # Collect metrics from all cameras
                all_metrics = self._collect_metrics()
                
                # Enqueue for MongoDB persistence (non-blocking)
                if all_metrics:
                    await metrics_writer.enqueue(all_metrics)
                
                # Broadcast to all connected WebSockets
                if self.websocket_connections and all_metrics:
                    await self._broadcast_metrics(all_metrics)
                
                # Wait for next tick
                await asyncio.sleep(self.broadcast_interval)
                
            except Exception as e:
                print(f"[MetricsAggregator] Error: {e}")
                await asyncio.sleep(1.0)
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """
        Collect metrics from SharedStore
        
        Returns:
            Dictionary with per-camera and per-area metrics
        """
        all_states = shared_store.get_all_states()
        
        metrics_snapshot = {
            'timestamp': time.time(),
            'cameras': {},
            'areas': {}
        }
        
        for camera_id, state in all_states.items():
            if state.metrics:
                # Add to history for smoothing
                if camera_id not in self.metrics_history:
                    self.metrics_history[camera_id] = deque(maxlen=self.history_size)
                
                self.metrics_history[camera_id].append(state.metrics)
                
                # Calculate smoothed metrics
                smoothed = self._smooth_metrics(camera_id)
                
                metrics_snapshot['cameras'][camera_id] = {
                    'camera_id': camera_id,
                    'timestamp': time.time(),  # Required for MongoDB TTL index
                    'status': state.status,
                    'people_count': state.metrics.get('people_count', 0),
                    'density': smoothed.get('density', 0.0),
                    'risk_score': smoothed.get('risk_score', 0.0),
                    'risk_level': state.metrics.get('risk_level', 'LOW'),
                    'avg_speed': smoothed.get('avg_speed', 0.0),
                    'compression': smoothed.get('compression', 0.0),
                    'velocity_variance': smoothed.get('velocity_variance', 0.0),
                    # Observability
                    'capture_fps': state.capture_fps,
                    'processing_fps': state.processing_fps,
                    'latency_ms': state.latency_ms,
                    'queue_depth': state.queue_depth,
                    'age_seconds': time.time() - state.metrics_timestamp
                }
        
        # Collect area-level metrics
        area_metrics = area_risk_engine.get_all_area_metrics()
        for area_id, area_data in area_metrics.items():
            metrics_snapshot['areas'][area_id] = {
                'area_id': area_data.area_id,
                'timestamp': time.time(),  # Required for MongoDB TTL index
                'total_people': area_data.total_people,
                'avg_density': area_data.avg_density,
                'max_density': area_data.max_density,
                'avg_risk_score': area_data.avg_risk_score,
                'max_risk_score': area_data.max_risk_score,
                'area_risk_level': area_data.area_risk_level,
                'current_occupancy': area_data.current_occupancy,
                'total_visits_today': area_data.total_visits_today,
                'total_entries': area_data.total_entries,
                'total_exits': area_data.total_exits,
                'status': area_data.status,
                'active_cameras': area_data.active_cameras,
                'total_cameras': area_data.total_cameras
            }
        
        return metrics_snapshot
    
    def _smooth_metrics(self, camera_id: str) -> Dict[str, float]:
        """
        Apply temporal smoothing to reduce flicker
        
        Returns:
            Smoothed metrics (moving average)
        """
        history = self.metrics_history.get(camera_id, deque())
        if not history:
            return {}
        
        # Calculate moving average for key metrics
        smoothed = {}
        keys = ['density', 'risk_score', 'avg_speed', 'compression', 'velocity_variance']
        
        for key in keys:
            values = [m.get(key, 0.0) for m in history if key in m]
            if values:
                smoothed[key] = sum(values) / len(values)
        
        return smoothed
    
    async def _broadcast_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Broadcast metrics to all connected WebSockets
        
        Args:
            metrics: Metrics dictionary to broadcast
        """
        # Remove dead connections
        dead_connections = set()
        
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(metrics)
            except Exception as e:
                print(f"[MetricsAggregator] Failed to send to connection: {e}")
                dead_connections.add(websocket)
        
        # Clean up dead connections
        self.websocket_connections -= dead_connections
    
    async def start(self) -> None:
        """Start aggregator task"""
        if not self.running:
            self.aggregator_task = asyncio.create_task(self.collect_and_broadcast())
    
    async def stop(self) -> None:
        """Stop aggregator task"""
        self.running = False
        if self.aggregator_task:
            await self.aggregator_task


# Global singleton instance
metrics_aggregator = MetricsAggregator(broadcast_interval=1.0)
