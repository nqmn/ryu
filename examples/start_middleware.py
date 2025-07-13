#!/usr/bin/env python3
"""
Ryu Middleware Startup Script

This script starts the Ryu middleware with proper configuration and
provides helpful information about the available APIs.
"""

import sys
import os
import subprocess
import time
import requests
import argparse

def check_dependencies():
    """Check if required dependencies are available"""
    print("Checking dependencies...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print("✓ Python version OK")
    
    # Check Ryu installation
    try:
        import ryu
        print("✓ Ryu framework available")
    except ImportError:
        print("❌ Ryu framework not installed")
        return False
    
    # Check middleware
    try:
        from ryu.app.middleware import MiddlewareAPI
        print("✓ Middleware components available")
    except ImportError as e:
        print(f"❌ Middleware import failed: {e}")
        return False
    
    # Check optional dependencies
    optional_deps = {
        'yaml': 'pyyaml',
        'requests': 'requests',
        'scapy': 'scapy',
        'psutil': 'psutil'
    }
    
    for module, package in optional_deps.items():
        try:
            __import__(module)
            print(f"✓ {package} available")
        except ImportError:
            print(f"⚠ {package} not available (some features may be limited)")
    
    return True

def start_middleware(apps=None, config_file=None, verbose=False):
    """Start the Ryu middleware"""
    
    # Build command
    cmd = ['ryu-manager']
    
    if verbose:
        cmd.append('--verbose')
    
    if config_file and os.path.exists(config_file):
        cmd.extend(['--config-file', config_file])
    
    # Add middleware app
    cmd.append('ryu.app.middleware.core')
    
    # Add additional apps
    if apps:
        cmd.extend(apps)
    
    print(f"Starting Ryu middleware...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        # Start Ryu
        process = subprocess.Popen(cmd)
        
        # Wait a bit for startup
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            print("✓ Ryu middleware started successfully!")
            print_api_info()
            
            # Wait for process to complete
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\nShutting down...")
                process.terminate()
                process.wait()
        else:
            print("❌ Ryu middleware failed to start")
            return False
            
    except FileNotFoundError:
        print("❌ ryu-manager not found. Please install Ryu framework.")
        return False
    except Exception as e:
        print(f"❌ Error starting middleware: {e}")
        return False
    
    return True

def print_api_info():
    """Print API information"""
    print("\n🌐 API Endpoints Available:")
    print("=" * 50)
    print("REST API Base: http://localhost:8080/v2.0/")
    print("WebSocket Events: ws://localhost:8080/v2.0/events/ws")
    print()
    print("Key Endpoints:")
    print("  Health Check:     GET /v2.0/health")
    print("  Topology View:    GET /v2.0/topology/view")
    print("  Create Topology:  POST /v2.0/topology/create")
    print("  Host List:        GET /v2.0/host/list")
    print("  Generate Traffic: POST /v2.0/traffic/generate")
    print("  Flow Stats:       GET /v2.0/stats/flow")
    print("  ML Models:        GET /v2.0/ml/models")
    print()
    print("📚 Documentation: See MIDDLEWARE_README.md")
    print("🧪 Testing: Run 'python test_middleware.py'")
    print("📝 Examples: Run 'python examples/middleware_usage.py'")
    print()

def test_api_connectivity():
    """Test if the API is responding"""
    print("Testing API connectivity...")
    
    try:
        response = requests.get("http://localhost:8080/v2.0/health", timeout=5)
        if response.status_code == 200:
            print("✓ API is responding")
            return True
        else:
            print(f"⚠ API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("⚠ API not yet available (this is normal during startup)")
        return False
    except Exception as e:
        print(f"⚠ API test error: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Start Ryu Middleware API")
    parser.add_argument('--apps', nargs='*', help='Additional Ryu apps to load')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--check-only', action='store_true', help='Only check dependencies')
    parser.add_argument('--test-api', action='store_true', help='Test API connectivity')
    
    args = parser.parse_args()
    
    print("Ryu Middleware Startup")
    print("=" * 30)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed")
        sys.exit(1)
    
    if args.check_only:
        print("\n✅ All dependencies OK")
        sys.exit(0)
    
    if args.test_api:
        success = test_api_connectivity()
        sys.exit(0 if success else 1)
    
    # Start middleware
    success = start_middleware(
        apps=args.apps,
        config_file=args.config,
        verbose=args.verbose
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
