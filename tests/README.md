# Tests Directory

This directory contains test scripts and integration tests for the Ryu Enhanced SDN Framework.

## 📁 Contents

### 🧪 Integration Tests
- **`test_middleware.py`** - Comprehensive middleware API testing
- **`test_multi_controller.py`** - Multi-controller functionality tests
- **`test_p4runtime_integration.py`** - P4Runtime integration testing

### 🖥️ Demo Tests
- **`test_gui_demo.py`** - GUI component testing and demonstration
- **`test_terminal_demo.py`** - Terminal interface testing and live event display

## 🚀 Running Tests

### Prerequisites
```bash
# Install with development dependencies
pip install -e .[dev]

# For network tests, ensure Mininet is available
sudo mn --test pingall
```

### Run All Tests
```bash
# Run all tests with pytest
pytest tests/

# Run with coverage
pytest --cov=ryu tests/

# Run with verbose output
pytest -v tests/
```

### Run Individual Tests
```bash
# Test middleware functionality
python tests/test_middleware.py

# Test multi-controller features
python tests/test_multi_controller.py

# Test P4Runtime integration
python tests/test_p4runtime_integration.py

# Demo GUI components
python tests/test_gui_demo.py

# Demo terminal interface
python tests/test_terminal_demo.py
```

### Test Categories

#### Unit Tests
Located in `ryu/tests/unit/` - Test individual components and functions.

#### Integration Tests
Located in this directory - Test complete workflows and system integration.

#### Demo Tests
Interactive tests that demonstrate functionality while testing.

## 🔧 Test Configuration

### Environment Variables
```bash
# Set test configuration
export RYU_TEST_MODE=true
export RYU_LOG_LEVEL=DEBUG
export RYU_API_PORT=8081  # Use different port for testing
```

### Test Data
Some tests may require:
- Running Mininet topology
- Mock network devices
- Sample P4 programs
- Test configuration files

## 📊 Test Coverage

To generate coverage reports:
```bash
# Generate HTML coverage report
pytest --cov=ryu --cov-report=html tests/

# View coverage in browser
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

## 🐛 Debugging Tests

### Verbose Logging
```bash
# Run tests with debug logging
RYU_LOG_LEVEL=DEBUG pytest tests/test_middleware.py -v -s
```

### Interactive Debugging
```bash
# Run with Python debugger
python -m pdb tests/test_middleware.py

# Or use pytest with pdb
pytest --pdb tests/test_middleware.py
```

## 🧪 Writing New Tests

### Test Structure
```python
import pytest
from ryu.app.middleware.core import MiddlewareApp

class TestNewFeature:
    def setup_method(self):
        """Setup before each test method"""
        self.app = MiddlewareApp()
    
    def teardown_method(self):
        """Cleanup after each test method"""
        pass
    
    def test_feature_functionality(self):
        """Test specific functionality"""
        # Arrange
        # Act
        # Assert
        pass
```

### Test Guidelines
1. **Descriptive names** - Use clear, descriptive test names
2. **Arrange-Act-Assert** - Follow the AAA pattern
3. **Independent tests** - Each test should be independent
4. **Mock external dependencies** - Use mocks for network calls
5. **Test edge cases** - Include error conditions and edge cases

## 📚 Related Documentation

- [Testing Guide](@documentations/examples/) - Comprehensive testing documentation
- [Development Setup](@documentations/installation/) - Development environment setup
- [API Reference](@documentations/api-reference/) - API testing reference
- [Architecture](@documentations/architecture/) - System architecture for testing

## 🤝 Contributing Tests

To contribute new tests:
1. Follow the existing test structure
2. Include both positive and negative test cases
3. Add appropriate documentation
4. Ensure tests pass in CI/CD
5. Update this README if needed

---

**Found a bug?** Please [create an issue](https://github.com/nqmn/ryu/issues) with test reproduction steps.
