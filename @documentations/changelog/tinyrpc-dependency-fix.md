# TinyRPC Dependency Fix

## Issue Description

Users were encountering the following error when running `ryu-manager`:

```
ModuleNotFoundError: No module named 'tinyrpc'
```

This error occurred because `tinyrpc` was listed as a dependency in `tools/pip-requires` but was missing from the main `pyproject.toml` dependencies list, causing installation issues with modern pip installations.

## Root Cause

The `tinyrpc` library is a core dependency for Ryu's WSGI and RPC functionality, specifically used by:
- `ryu.app.wsgi` module for RPC server functionality
- BGP speaker components for RPC communication

However, it was not properly declared in the main `pyproject.toml` dependencies, leading to inconsistent installations.

## Solution

### 1. Updated pyproject.toml

Added `tinyrpc>=1.1.0` to the core dependencies list in `pyproject.toml`:

```toml
dependencies = [
    "eventlet>=0.40.0",
    "msgpack>=1.1.0",
    "netaddr>=1.3.0",
    "oslo.config>=10.0.0",
    "ovs>=3.5.0",
    "packaging>=25.0",
    "routes>=2.5.1",
    "tinyrpc>=1.1.0",  # Added this line
    "webob>=1.8.9",
]
```

### 2. Updated MyPy Configuration

Added `tinyrpc.*` to the MyPy overrides section to handle missing type stubs:

```toml
[[tool.mypy.overrides]]
module = [
    # ... other modules ...
    "tinyrpc.*",  # Added this line
    # ... other modules ...
]
ignore_missing_imports = true
```

### 3. Updated Documentation

#### Installation Guide (@documentations/installation/README.md)

- Added a "Core Dependencies" section listing all required dependencies including `tinyrpc`
- Added troubleshooting section for the specific `tinyrpc` import error
- Provided clear installation commands for fixing the issue

#### Main README.md

- Added a "Core Dependencies" section in the Prerequisites
- Listed `tinyrpc` as a core dependency for WSGI functionality

## Files Modified

1. `pyproject.toml` - Added `tinyrpc>=1.1.0` to core dependencies and MyPy overrides
2. `@documentations/installation/README.md` - Added core dependencies section and troubleshooting
3. `README.md` - Added core dependencies information
4. `@documentations/changelog/tinyrpc-dependency-fix.md` - This documentation

## Verification

After the fix:

1. ✅ `pip install -e .` now automatically installs `tinyrpc>=1.1.0`
2. ✅ `ryu-manager --version` works without import errors
3. ✅ `ryu-manager ryu.app.simple_switch_13` loads successfully
4. ✅ `python -c "import tinyrpc"` works correctly

## Impact

- **Positive**: Resolves installation issues for new users
- **Positive**: Ensures consistent dependency management
- **Positive**: Improves documentation clarity
- **Minimal**: No breaking changes for existing installations

## Future Prevention

This issue highlights the importance of:
1. Keeping `pyproject.toml` as the single source of truth for dependencies
2. Regular testing of fresh installations
3. Maintaining consistency between legacy requirement files and modern packaging standards

## Related Issues

This fix resolves the `ModuleNotFoundError: No module named 'tinyrpc'` error that users encountered when running Ryu applications that depend on WSGI or RPC functionality.
