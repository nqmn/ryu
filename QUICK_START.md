# Quick Start Guide - Ryu Enhanced Testing

## 🚀 For Your Current Situation

Since you're already in a virtual environment with Ryu installed, here's the quickest way to run the tests:

### 1. Make Scripts Executable
```bash
chmod +x run_tests_venv.sh
chmod +x setup_remote_server.sh
```

### 2. Verify Your Environment
```bash
# Check if everything is properly set up
python3 verify_environment.py
```

### 3. Run Tests (Recommended Method)
```bash
# Use the virtual environment wrapper script
sudo ./run_tests_venv.sh

# Or with specific options
sudo ./run_tests_venv.sh --topology linear --hosts 6
```

### 4. Alternative: Direct Run
```bash
# If the wrapper doesn't work, run directly
sudo -E env PATH=$PATH python3 test_full_deployment.py
```

## 🔧 Troubleshooting Your Current Issues

### Issue 1: "ryu: not found"
**Solution**: The test script wasn't detecting ryu in your virtual environment.
- ✅ **Fixed**: Updated script to properly detect virtual environment and ryu installation

### Issue 2: "externally-managed-environment"
**Solution**: The script was trying to install packages system-wide instead of in your venv.
- ✅ **Fixed**: Updated script to respect virtual environment and use proper pip commands

### Issue 3: "curl: not found"
**Solution**: curl is optional, the script will use Python requests instead.
- ✅ **Fixed**: Made curl optional and added fallback to Python requests

## 📋 What the Fixed Script Does

1. **Detects Virtual Environment**: Automatically finds and uses your venv
2. **Checks Dependencies**: Verifies all required packages are installed
3. **Installs Missing Packages**: Only installs in venv if needed
4. **Finds Ryu Manager**: Locates ryu-manager in venv or system PATH
5. **Runs Comprehensive Tests**: Full Mininet + Ryu + API testing

## 🎯 Expected Output

After running `sudo ./run_tests_venv.sh`, you should see:

```
[07:04:33] INFO: ✓ Virtual environment detected: /home/user/ryu/venv
[07:04:33] INFO: ✓ python3: Python 3.12.3
[07:04:33] INFO: ✓ mininet: installed
[07:04:33] INFO: ✓ ovs: ovs-vsctl (Open vSwitch) 3.3.0
[07:04:33] INFO: ✓ ryu: available in virtual environment
[07:04:33] INFO: ⚠ curl: not found (will use python requests instead)
[07:04:35] START: Starting Ryu middleware controller...
[07:04:45] INFO: ✓ Ryu middleware API is responding
[07:04:47] START: Creating Mininet topology: simple
[07:04:52] INFO: ✓ 1 switch(es) connected
[07:04:55] TEST: Testing network connectivity (pingall)...
[07:05:05] INFO: ✓ Pingall test passed - all hosts can communicate
```

## 🛠️ If You Still Have Issues

### Check Virtual Environment
```bash
# Verify you're in the right venv
echo $VIRTUAL_ENV
which python3
which ryu-manager

# Should show paths like:
# /home/user/ryu/venv
# /home/user/ryu/venv/bin/python3
# /home/user/ryu/venv/bin/ryu-manager
```

### Install Missing Dependencies
```bash
# In your virtual environment
pip install pydantic pyyaml requests scapy psutil websockets
```

### Manual Test
```bash
# Test Ryu manually first
source venv/bin/activate
ryu-manager ryu.app.middleware.core

# In another terminal, test API
curl http://localhost:8080/v2.0/health
```

## 📊 Test Results

The script will generate:
- **Real-time progress** with color-coded status
- **Comprehensive JSON report** with all test results
- **Overall score** and grade (Excellent/Good/Fair/Poor)
- **Detailed logs** for debugging any issues

## 🌐 Remote Access

After successful tests, you can access:
- **GUI**: `http://YOUR_SERVER_IP:8080/gui`
- **API**: `http://YOUR_SERVER_IP:8080/v2.0/health`

## 📞 Need Help?

If you encounter any issues:

1. **Run verification first**: `python3 verify_environment.py`
2. **Check the generated JSON report** for detailed error information
3. **Look at the console output** for specific error messages
4. **Try manual testing** to isolate the issue

The updated scripts should now work correctly with your virtual environment setup! 🎉
