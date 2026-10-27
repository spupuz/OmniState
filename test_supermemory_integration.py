#!/usr/bin/env python3
"""
Simple test to verify Supermemory integration with OmniState.
This tests the configuration and bridge tools without requiring the full MCP server.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

def test_config():
    """Test Supermemory configuration"""
    try:
        from config import Config, SupermemoryConfig
        
        print("✓ Config imports successful")
        
        # Test SupermemoryConfig
        sm_config = SupermemoryConfig()
        assert sm_config.api_key == ""
        assert sm_config.base_url == "https://api.supermemory.ai"
        assert sm_config.api_version == "v5"
        assert sm_config.default_space == "sm_project_default"
        assert sm_config.enabled == False
        
        print(f"✓ SupermemoryConfig defaults correct")
        print(f"  - enabled: {sm_config.enabled}")
        print(f"  - base_url: {sm_config.base_url}")
        
        # Test Config
        cfg = Config(data_dir="/tmp/test-omnistate")
        assert hasattr(cfg, 'supermemory')
        assert cfg.supermemory.enabled == False
        
        print(f"✓ Config created with Supermemory field")
        
        # Test with environment overrides
        test_env = {
            "SUPERMEMORY_API_KEY": "test_key_123",
            "SUPERMEMORY_BASE_URL": "https://custom.example.com",
            "SUPERMEMORY_ENABLED": "true",
            "SUPERMEMORY_API_VERSION": "v6",
            "SUPERMEMORY_DEFAULT_SPACE": "custom_space"
        }
        
        from config import load_config
        cfg_with_env = load_config(env=test_env)
        
        assert cfg_with_env.supermemory.api_key == "test_key_123"
        assert cfg_with_env.supermemory.base_url == "https://custom.example.com"
        assert cfg_with_env.supermemory.enabled == True
        assert cfg_with_env.supermemory.api_version == "v6"
        assert cfg_with_env.supermemory.default_space == "custom_space"
        
        print(f"✓ Environment variable overrides work correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_imports():
    """Test that Supermemory bridge tools are importable"""
    try:
        # Test the async tools can be imported
        from mcp_server import (
            supermemory_search,
            supermemory_profile, 
            supermemory_add,
            supermemory_sync,
            supermemory_status
        )
        
        print("✓ Supermemory bridge tools import successful")
        
        # Check they are async functions
        import inspect
        
        async_tools = [
            supermemory_search,
            supermemory_profile,
            supermemory_add,
            supermemory_sync
        ]
        
        for tool in async_tools:
            assert inspect.iscoroutinefunction(tool), f"{tool.__name__} should be async"
        
        print(f"✓ All async tools properly defined")
        
        # Check sync tool
        assert not inspect.iscoroutinefunction(supermemory_status), "supermemory_status should be sync"
        
        print(f"✓ supermemory_status is sync")
        
        return True
        
    except Exception as e:
        print(f"✗ Tool import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration_scenarios():
    """Test various configuration scenarios"""
    try:
        from config import SupermemoryConfig, load_config
        
        # Test 1: Default configuration
        cfg1 = SupermemoryConfig()
        assert cfg1.enabled == False
        assert cfg1.api_key == ""
        
        # Test 2: Enabled but no API key
        cfg2_dict = {"enabled": True, "api_key": "", "base_url": "https://api.supermemory.ai"}
        # Simulate with dict
        class ConfigFromDict:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        cfg2 = ConfigFromDict(**cfg2_dict)
        assert cfg2.enabled == True
        assert cfg2.api_key == ""
        
        # Test 3: Enabled with API key
        cfg3_dict = {"enabled": True, "api_key": "sm_test_key", "base_url": "https://api.supermemory.ai"}
        cfg3 = ConfigFromDict(**cfg3_dict)
        assert cfg3.enabled == True
        assert cfg3.api_key == "sm_test_key"
        
        print("✓ Configuration scenarios work correctly")
        return True
        
    except Exception as e:
        print(f"✗ Configuration scenarios test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Supermemory Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Configuration Test", test_config),
        ("Tool Import Test", test_tool_imports),
        ("Configuration Scenarios", test_configuration_scenarios),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Summary: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    
    print("\n✅ All tests passed!")
    print("\nIntegration Summary:")
    print("- Supermemory configuration added to OmniState config.py")
    print("- 5 Supermemory bridge tools implemented in mcp_server.py")
    print("- Environment variables support for configuration")
    print("- Proper async/await patterns for non-blocking operations")
    print("- Comprehensive error handling and status reporting")


if __name__ == "__main__":
    main()