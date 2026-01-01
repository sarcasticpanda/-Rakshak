"""
WebSocket API - Live Metrics Broadcast @ 1Hz
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.metrics_aggregator import metrics_aggregator


router = APIRouter(tags=["websocket"])


@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """
    WebSocket endpoint for live metrics
    Broadcasts metrics @ 1Hz to all connected clients
    
    Client receives:
    {
        "timestamp": 1234567890.123,
        "cameras": {
            "cam_1": {
                "people_count": 452,
                "risk_score": 85.3,
                "risk_level": "HIGH",
                ...
            }
        }
    }
    """
    await websocket.accept()
    metrics_aggregator.register_connection(websocket)
    
    try:
        # Keep connection alive - aggregator will push metrics
        while True:
            # Wait for client messages (ping/pong)
            data = await websocket.receive_text()
            
            # Echo back (for connection health check)
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected")
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
    finally:
        metrics_aggregator.unregister_connection(websocket)
