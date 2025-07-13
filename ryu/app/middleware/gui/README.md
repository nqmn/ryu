# SDN Middleware - Network Topology Dashboard

A modern, responsive, and interactive HTML GUI for visualizing and managing SDN network topologies. This dashboard provides real-time visualization of OpenFlow and P4Runtime networks with comprehensive monitoring and control capabilities.

## 🌟 Features

### 🎯 Core Functionality
- **Real-time Topology Visualization** - Interactive network graph with live updates
- **Multi-Protocol Support** - OpenFlow and P4Runtime switch visualization
- **Node Inspection** - Detailed information panels for switches, hosts, and links
- **Search & Filtering** - Find and filter network elements quickly
- **Layout Controls** - Multiple graph layout algorithms
- **Export Capabilities** - Export topology as JSON or PNG images

### 🎨 User Interface
- **Modern Responsive Design** - Works on desktop, tablet, and mobile
- **Dark/Light Theme** - Toggle between themes with system preference detection
- **Interactive Controls** - Sidebar with comprehensive network controls
- **Real-time Statistics** - Live network metrics and counters
- **Toast Notifications** - Non-intrusive status updates
- **Mini-map Navigation** - Overview and navigation for large topologies

### 🔄 Real-time Features
- **WebSocket Integration** - Live topology updates via WebSocket events
- **Event Notifications** - Real-time alerts for network changes
- **Connection Status** - Visual connection status indicators
- **Auto-reconnection** - Automatic WebSocket reconnection with backoff

## 🏗️ Architecture

### Frontend Components
```
src/
├── api/
│   └── topology.js          # REST API and WebSocket client
├── components/
│   ├── network-graph.js     # Cytoscape.js graph visualization
│   └── detail-panel.js      # Node/link detail panels
├── state/
│   └── topology-store.js    # Reactive state management
├── styles/
│   ├── main.css            # Core styles and variables
│   ├── components.css      # Component-specific styles
│   └── responsive.css      # Responsive design rules
└── app.js                  # Main application controller
```

### Backend Integration
- **Middleware API** - Connects to `/v2.0/` REST endpoints
- **WebSocket Events** - Real-time updates via `/v2.0/events/ws`
- **Static File Serving** - Served by middleware GUI controller

## 🚀 Getting Started

### Prerequisites
- Ryu SDN Controller with middleware installed
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Network topology (Mininet, physical switches, or emulated)

### Installation & Setup

1. **Start the Middleware**
   ```bash
   # Navigate to the Ryu directory
   cd /path/to/ryu
   
   # Start Ryu with middleware
   ryu-manager ryu.app.middleware.core
   ```

2. **Access the Dashboard**
   ```
   Open your web browser and navigate to:
   http://localhost:8080/gui
   
   # Or directly to the root:
   http://localhost:8080/
   ```

3. **Verify Connection**
   - Check the connection status indicator in the header
   - Should show "Connected" with a green indicator
   - If disconnected, check middleware logs and network connectivity

### Quick Start with Mininet

1. **Create a Test Topology**
   ```bash
   # In a separate terminal, start Mininet
   sudo mn --controller=remote --topo linear,3
   ```

2. **View in Dashboard**
   - Refresh the dashboard or wait for auto-discovery
   - You should see 3 switches and 3 hosts
   - Links should appear between connected elements

## 📖 User Guide

### Navigation & Controls

#### Header
- **Connection Status** - Shows WebSocket connection state
- **Theme Toggle** - Switch between light and dark themes

#### Sidebar Controls
- **Search** - Find nodes by ID, MAC, or IP address
- **Filters** - Show/hide switches, hosts, and links
- **Layout** - Choose from multiple layout algorithms:
  - Force-directed (default)
  - Grid
  - Circle
  - Hierarchical
- **Statistics** - Real-time network metrics
- **Actions** - Refresh, export, and utility functions

#### Graph Interaction
- **Click** - Select nodes or links for detailed information
- **Double-click** - Fit graph to viewport
- **Right-click** - Context menu (future feature)
- **Drag** - Pan the graph
- **Scroll** - Zoom in/out
- **Escape** - Clear selection and close panels

### Node Types & Visualization

#### Switches
- **OpenFlow Switches** - Blue rectangles
- **P4Runtime Switches** - Green rectangles
- **Label** - Shows last 4 digits of DPID

#### Hosts
- **Hosts** - Yellow circles
- **Label** - Shows last 2 octets of MAC address

#### Links
- **Active Links** - Gray lines with arrows
- **Selected Links** - Blue highlighted lines

### Detail Panels

#### Switch Details
- **Basic Information** - DPID, address, connection status
- **Port Information** - Port list with status
- **Flow Statistics** - Number of installed flows
- **Actions** - Refresh data, view flows

#### Host Details
- **Network Information** - MAC address, IP addresses
- **Connection** - Connected switch and port
- **Actions** - Ping host, refresh data

### Real-time Updates

The dashboard automatically receives and displays:
- **Switch Events** - Connection/disconnection
- **Link Events** - Link discovery/removal
- **Host Events** - Host discovery
- **Port Events** - Port status changes

## 🔧 Configuration

### API Endpoints
The dashboard connects to these middleware endpoints:
- `GET /v2.0/topology/view` - Initial topology data
- `GET /v2.0/stats/topology` - Topology statistics
- `GET /v2.0/health` - Health check
- `WS /v2.0/events/ws` - Real-time events

### Customization

#### Themes
- Modify CSS variables in `src/styles/main.css`
- Add custom color schemes
- Adjust layout dimensions

#### Graph Styling
- Edit Cytoscape styles in `src/components/network-graph.js`
- Customize node shapes, colors, and sizes
- Modify edge styles and animations

#### Layout Algorithms
- Add new layouts in `NetworkGraph.layoutOptions`
- Configure existing layout parameters
- Set default layout preferences

## 🧪 Testing

### Manual Testing Checklist

1. **Initial Load**
   - [ ] Dashboard loads without errors
   - [ ] Connection status shows "Connected"
   - [ ] Topology data loads and displays

2. **Graph Interaction**
   - [ ] Nodes are clickable and show details
   - [ ] Graph can be panned and zoomed
   - [ ] Layout controls work correctly

3. **Real-time Updates**
   - [ ] Start/stop Mininet topology
   - [ ] Verify switches appear/disappear
   - [ ] Check link discovery works

4. **UI Features**
   - [ ] Search functionality works
   - [ ] Filters hide/show elements
   - [ ] Theme toggle works
   - [ ] Export functions work

5. **Responsive Design**
   - [ ] Test on different screen sizes
   - [ ] Mobile layout works correctly
   - [ ] Touch interactions work

### Browser Compatibility
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## 🐛 Troubleshooting

### Common Issues

#### Dashboard Won't Load
- Check middleware is running on port 8080
- Verify browser console for JavaScript errors
- Ensure network connectivity to middleware

#### No Topology Data
- Check middleware logs for API errors
- Verify topology exists (run Mininet or connect switches)
- Try refreshing the topology manually

#### WebSocket Connection Failed
- Check firewall settings
- Verify WebSocket endpoint is accessible
- Look for proxy/load balancer issues

#### Performance Issues
- Reduce topology size for testing
- Check browser memory usage
- Disable animations for large topologies

### Debug Mode
Enable browser developer tools and check:
- Console for JavaScript errors
- Network tab for API request failures
- WebSocket messages in Network tab

## 🤝 Contributing

### Development Setup
1. Make changes to files in `src/`
2. Test with a running middleware instance
3. Verify responsive design on multiple devices
4. Check browser compatibility

### Code Style
- Use ES6+ JavaScript features
- Follow existing naming conventions
- Add comments for complex logic
- Maintain responsive design principles

## 📄 License

This project is part of the Ryu SDN Framework and follows the same Apache License 2.0.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review middleware logs for API errors
3. Test with a simple Mininet topology
4. Check browser developer console for errors

---

**Built with** ❤️ **for the SDN community**
