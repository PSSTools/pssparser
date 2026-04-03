"""
pytest configuration and shared fixtures for PSS frontend tests
"""
import pytest
from pssparser import Parser
from pssparser.core import Factory


@pytest.fixture(scope="session")
def factory():
    """Global factory instance (session scope for efficiency)"""
    f = Factory.inst()
    f.getDebugMgr().enable(False)
    return f


@pytest.fixture(autouse=True)
def _debug_off(factory):
    """Keep parser debug logging disabled unless a test opts in explicitly."""
    factory.getDebugMgr().enable(False)
    yield
    factory.getDebugMgr().enable(False)


@pytest.fixture
def parser():
    """Fresh parser for each test"""
    return Parser()


@pytest.fixture
def profiling_parser():
    """Parser with profiling enabled"""
    parser = Parser()
    parser.enable_profiling(True)
    return parser


@pytest.fixture
def debug_parser(factory):
    """Parser with debug enabled"""
    factory.getDebugMgr().enable(True)
    parser = Parser()
    yield parser
    # Clean up - disable debug after test
    factory.getDebugMgr().enable(False)


@pytest.fixture
def sample_component():
    """Sample component PSS code for testing"""
    return """
        component pss_top {
            action A {
                rand int x;
                constraint x > 0;
            }
        }
    """


@pytest.fixture
def multi_file_project():
    """Multi-file PSS project for import/linking tests"""
    return [
        ("types.pss", """
            struct Point {
                int x;
                int y;
            }
        """),
        ("actions.pss", """
            import types::*;
            component pss_top {
                action Move {
                    Point dest;
                }
            }
        """)
    ]


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", 
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", 
        "profiling: profiling and performance tests"
    )
    config.addinivalue_line(
        "markers", 
        "integration: integration tests"
    )
    config.addinivalue_line(
        "markers", 
        "performance: performance tests requiring benchmarking"
    )
    config.addinivalue_line(
        "markers",
        "source_ref: tests for source reference preservation"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location"""
    for item in items:
        # Mark tests in performance directory as slow
        if "performance/" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.performance)
        
        # Mark integration tests
        if "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Mark source reference tests
        if "source_references/" in str(item.fspath):
            item.add_marker(pytest.mark.source_ref)
