# जनRakshak - Frontend Dashboard

Real-time stampede detection and crowd monitoring dashboard.

## Features

✅ **Live Camera Feeds** - MJPEG streams from all cameras  
✅ **Real-Time Metrics** - WebSocket connection for instant updates  
✅ **Alert System** - Automatic alerts for high-risk situations  
✅ **Analytics Dashboard** - Crowd density trends and patterns  
✅ **Camera Management** - View and manage all connected cameras  

## Quick Start

### 1. Start Backend Server
```bash
cd ../backend
python main.py
```

Server should be running at: http://localhost:8000

### 2. Open Frontend
Simply open `index.html` in your browser:
- Double-click `index.html`, or
- Use Live Server extension in VS Code, or
- Run a simple HTTP server:

```bash
# Python
python -m http.server 8080

# Node.js
npx http-server -p 8080
```

Then open: http://localhost:8080

### 3. Verify Connection
Look for the connection status indicator in the dashboard header:
- **● Connected** (green) - Backend connected, receiving live data
- **● Disconnected** (red) - Backend not reachable

## Pages

### Dashboard
- Overview of all cameras
- Total people count
- Average density
- Active alerts
- Real-time charts

### Camera Feeds
- Live MJPEG streams
- Individual camera metrics
- Status indicators

### Camera Management
- List all cameras
- View camera details
- Check connection status

### Alerts
- Real-time alert notifications
- Filter by priority (High/Medium/Low)
- Alert history

### Analytics
- Crowd density trends
- Historical data visualization

## Configuration

Edit `app.js` to change backend URL:

```javascript
const API_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws/metrics';
```

## Troubleshooting

### No connection
- Ensure backend server is running
- Check console for errors (F12)
- Verify backend URL is correct

### No video feeds
- Check if cameras are running in backend
- Visit http://localhost:8000/cameras to verify
- Check browser console for CORS errors

### Slow updates
- Check network connection
- Reduce number of active cameras
- Check backend server CPU usage

## Browser Support

- Chrome/Edge (recommended)
- Firefox
- Safari (limited WebSocket support)

## Development

The dashboard uses vanilla JavaScript with:
- Chart.js for visualizations
- Native WebSocket API
- Fetch API for REST calls

No build process required!
