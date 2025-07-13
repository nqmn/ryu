# Ryu Enhanced SDN Middleware - Remote Server Deployment

This directory contains scripts for deploying and testing Ryu Enhanced SDN Middleware on a remote Linux server.

## 📁 Files

- **`test_full_deployment.py`** - Comprehensive test script that sets up Mininet, runs Ryu middleware, and tests all functionality
- **`setup_remote_server.sh`** - Setup script that installs all dependencies and prepares the environment
- **`DEPLOYMENT_README.md`** - This documentation file

## 🚀 Quick Start

### 1. Initial Setup (Run Once)

```bash
# Upload files to your remote server
scp test_full_deployment.py setup_remote_server.sh user@your-server:/home/user/

# SSH to your server
ssh user@your-server

# Make setup script executable and run it
chmod +x setup_remote_server.sh
./setup_remote_server.sh
```

### 2. Run Tests

```bash
# Use the generated launcher script
./run_tests.sh

# Or run with specific options
./run_tests.sh --topology linear --hosts 6
./run_tests.sh --topology tree --controller-port 6633
```

### 3. Manual Testing

```bash
# Activate environment
source venv/bin/activate
cd ryu

# Start middleware manually
ryu-manager ryu.app.middleware.core

# In another terminal, test API
curl http://localhost:8080/v2.0/health

# Access GUI
http://YOUR_SERVER_IP:8080/gui
```

## 🧪 Test Script Features

### Comprehensive Testing
- **Dependency Check** - Verifies all required software is installed
- **Ryu Controller** - Starts middleware with all components
- **Mininet Topology** - Creates and configures network topology
- **Network Connectivity** - Tests pingall between all hosts
- **API Endpoints** - Tests all REST API endpoints
- **GUI Interface** - Verifies web dashboard accessibility
- **Traffic Generation** - Tests traffic generation capabilities

### Topology Options
- **Simple** (default) - Single switch with N hosts
- **Linear** - Linear chain of switches
- **Tree** - Tree topology with multiple levels

### Test Output
- **Real-time Progress** - Color-coded status updates
- **Comprehensive Report** - Detailed JSON report with all results
- **Score Calculation** - Overall test score and grade
- **Error Handling** - Graceful handling of failures

## 📊 Example Test Output

```
=== Ryu Enhanced SDN Middleware Test Suite ===
Topology: simple, Hosts: 4
Controller Port: 6653, API Port: 8080
Start Time: 2025-07-13 15:30:00
============================================================

[15:30:01] CHECK: Checking dependencies...
[15:30:02] INFO: ✓ python3: Python 3.10.12
[15:30:02] INFO: ✓ mininet: mininet 2.3.0
[15:30:03] INFO: ✓ ryu: ryu 4.34

[15:30:05] START: Starting Ryu middleware controller...
[15:30:15] INFO: ✓ Ryu middleware API is responding

[15:30:17] START: Creating Mininet topology: simple
[15:30:22] INFO: ✓ 1 switch(es) connected

[15:30:25] TEST: Testing network connectivity (pingall)...
[15:30:35] INFO: ✓ Pingall test passed - all hosts can communicate

[15:30:37] TEST: Testing API endpoints...
[15:30:38] INFO: ✓ health: SUCCESS
[15:30:39] INFO: ✓ topology: SUCCESS
[15:30:40] INFO: ✓ controllers: SUCCESS

[15:30:42] TEST: Testing GUI interface...
[15:30:43] INFO: ✓ GUI main page accessible

=== TEST REPORT ===
Overall Score: 95.2% (20/21) - EXCELLENT
Detailed report saved to: test_report_20250713_153045.json
```

## 🔧 Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Make sure to run test script with sudo
   sudo python3 test_full_deployment.py
   ```

2. **Port Already in Use**
   ```bash
   # Clean up existing processes
   sudo mn -c
   sudo pkill -f ryu-manager
   ```

3. **Mininet Not Found**
   ```bash
   # Install Mininet
   sudo apt install mininet
   ```

4. **API Not Responding**
   ```bash
   # Check if middleware started correctly
   ps aux | grep ryu-manager
   netstat -tlnp | grep 8080
   ```

### Firewall Configuration

The setup script automatically configures firewall rules, but you may need to manually open ports:

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 8080/tcp
sudo ufw allow 6653/tcp

# RHEL/CentOS (firewalld)
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-port=6653/tcp
sudo firewall-cmd --reload
```

## 📋 System Requirements

### Minimum Requirements
- **OS**: Ubuntu 18.04+, Debian 10+, CentOS 7+, RHEL 7+
- **RAM**: 2GB (4GB recommended)
- **CPU**: 2 cores
- **Storage**: 5GB free space
- **Network**: Internet access for package installation

### Recommended Requirements
- **OS**: Ubuntu 20.04+ or CentOS 8+
- **RAM**: 4GB or more
- **CPU**: 4 cores or more
- **Storage**: 10GB free space
- **Network**: Dedicated network interface for testing

## 🌐 Remote Access

### GUI Access
After starting the middleware, access the web GUI at:
```
http://YOUR_SERVER_IP:8080/gui
```

### API Access
Test API endpoints remotely:
```bash
curl http://YOUR_SERVER_IP:8080/v2.0/health
curl http://YOUR_SERVER_IP:8080/v2.0/topology/view
```

### SSH Tunneling (Optional)
For secure access through SSH tunnel:
```bash
# On your local machine
ssh -L 8080:localhost:8080 user@your-server

# Then access locally
http://localhost:8080/gui
```

## 📈 Performance Testing

The test script includes performance metrics:
- **Startup Time** - Time to initialize all components
- **Response Time** - API endpoint response times
- **Network Latency** - Mininet ping times
- **Throughput** - Traffic generation performance

## 🔄 Continuous Testing

For automated testing, you can run the script periodically:

```bash
# Add to crontab for daily testing
0 2 * * * cd /home/user && ./run_tests.sh --topology simple > test_$(date +\%Y\%m\%d).log 2>&1
```

## 📞 Support

If you encounter issues:
1. Check the generated test report JSON file
2. Review system logs: `journalctl -u openvswitch-switch`
3. Verify network configuration: `ip addr show`
4. Check process status: `ps aux | grep -E "(ryu|mininet)"`

## 🎯 Next Steps

After successful deployment:
1. Explore the web GUI interface
2. Test with different topologies
3. Integrate with your SDN applications
4. Set up monitoring and alerting
5. Configure production deployment
