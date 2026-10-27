#!/usr/bin/env python3
"""
Demonstration of Supermemory integration with OmniState.
Shows the configuration and tool usage without requiring full MCP server setup.
"""

import os
import sys

# Add server directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from config import Config, SupermemoryConfig, load_config
def demonstrate_configuration():
    """Demonstrate Supermemory configuration capabilities"""
    print("=" * 70)
    print("Supermemory Configuration Demonstration")
    print("=" * 70)
    
    # 1. Show default configuration
    print("\n1. DEFAULT SUPERMEMORY CONFIGURATION:")
    print("-" * 50)
    default_config = SupermemoryConfig()
    print(f"   Enabled: {default_config.enabled}")
    print(f"   API Key: {'[SET]' if default_config.api_key else '[NOT SET]'}")
    print(f"   Base URL: {default_config.base_url}")
    print(f"   API Version: {default_config.api_version}")
    print(f"   Default Space: {default_config.default_space}")
    
    # 2. Show Config integration
    print("\n2. CONFIG CLASS INTEGRATION:")
    print("-" * 50)
    cfg = Config(data_dir="/tmp/test-omnistate")
    print(f"   OmniState Config has Supermemory field: {hasattr(cfg, 'supermemory')}")
    print(f"   Supermemory enabled: {cfg.supermemory.enabled}")
    print(f"   Type: {type(cfg.supermemory).__name__}")
    
    # 3. Show environment variable support
    print("\n3. ENVIRONMENT VARIABLE SUPPORT:")
    print("-" * 50)
    
    # Simulate environment variables
    test_env = {
        "SUPERMEMORY_API_KEY": "sm_prod_api_key_12345",
        "SUPERMEMORY_BASE_URL": "https://supermemory.company.com",
        "SUPERMEMORY_ENABLED": "true",
        "SUPERMEMORY_API_VERSION": "v6",
        "SUPERMEMORY_DEFAULT_SPACE": "production_workspace"
    }
    
    # Create config with environment variables
    cfg_with_env = load_config(env=test_env)
    
    print(f"   API Key: {cfg_with_env.supermemory.api_key[:20]}...")
    print(f"   Base URL: {cfg_with_env.supermemory.base_url}")
    print(f"   Enabled: {cfg_with_env.supermemory.enabled}")
    print(f"   API Version: {cfg_with_env.supermemory.api_version}")
    print(f"   Default Space: {cfg_with_env.supermemory.default_space}")
    
    # 4. Show configuration merging
    print("\n4. CONFIGURATION MERGING:")
    print("-" * 50)
    print("   Order of precedence:")
    print("   - Environment variables (highest)")
    print("   - Config file")
    print("   - Default values (lowest)")
    
    return True
def demonstrate_bridge_tools():
    """Demonstrate the Supermemory bridge tools"""
    print("\n" + "=" * 70)
    print("SUPERMEMORY BRIDGE TOOLS DEMONSTRATION")
    print("=" * 70)
    
    print("\n1. AVAILABLE BRIDGE TOOLS:")
    print("-" * 50)
    
    tools = [
        ("supermemory_search", "Search Supermemory memories", [
            "query (required)", 
            "namespace (optional, defaults to config)",
            "limit (optional, default=10)",
            "scope (optional, default='shared')"
        ]),
        ("supermemory_profile", "Get Supermemory user profile", [
            "namespace (optional, defaults to config)"
        ]),
        ("supermemory_add", "Add memory to Supermemory", [
            "content (required)",
            "namespace (optional, defaults to config)",
            "title (optional)",
            "tags (optional, comma-separated string)",
            "source (optional)"
        ]),
        ("supermemory_sync", "Sync OmniState with Supermemory", [
            "project (optional, OmniState project name)",
            "namespace (optional, defaults to config)",
            "limit (optional, default=50)"
        ]),
        ("supermemory_status", "Get Supermemory integration status", [])
    ]
    
    for tool_name, description, params in tools:
        print(f"   - {tool_name}:")
        print(f"     Description: {description}")
        print(f"     Parameters: {', '.join(params)}")
        print()
    
    print("2. TOOL CHARACTERISTICS:")
    print("-" * 50)
    print("   - Async tools (except supermemory_status): supermemory_search, supermemory_profile, supermemory_add, supermemory_sync")
    print("   - supermemory_status: synchronous")
    print("   - Error handling: Graceful failure with informative messages")
    print("   - API dependency: Requires node-fetch (Node.js runtime)")
    print("   - Fallback mode: Simulates responses in non-Node environments")
    
    print("\n3. INTEGRATION SCENARIOS:")
    print("-" * 50)
    
    scenarios = [
        ("Search & Add", "Find existing memories, add new ones"),
        ("Profile Retrieval", "Get user profile and context"),
        ("Project Sync", "Sync project-specific memories"),
        ("Status Check", "Verify integration health"),
        ("Conditional Usage", "Use Supermemory when available, fallback to OmniState")
    ]
    
    for scenario, description in scenarios:
        print(f"   - {scenario}: {description}")
    
    return True
def demonstrate_usage_examples():
    """Show practical usage examples"""
    print("\n" + "=" * 70)
    print("PRACTICAL USAGE EXAMPLES")
    print("=" * 70)
    
    examples = [
        ("Example 1: Search Memory", '''
# Search for user preferences
{
  "tool": "supermemory_search",
  "arguments": {
    "query": "preferred programming languages",
    "namespace": "sm_project_default",
    "limit": 5
  }
}
'''),
        ("Example 2: Get Profile", '''
# Retrieve user profile
{
  "tool": "supermemory_profile",
  "arguments": {
    "namespace": "sm_project_default"
  }
}
'''),
        ("Example 3: Add Memory", '''
# Store new information
{
  "tool": "supermemory_add",
  "arguments": {
    "content": "User prefers TypeScript with React",
    "title": "User Technology Preferences",
    "namespace": "sm_project_default",
    "tags": "preference,technology,typeScript,react",
    "source": "omnistate-bridge"
  }
}
'''),
        ("Example 4: Sync Project", '''
# Sync current project with Supermemory
{
  "tool": "supermemory_sync",
  "arguments": {
    "project": "my-typescript-project",
    "namespace": "sm_project_default",
    "limit": 100
  }
}
'''),
        ("Example 5: Check Status", '''
# Verify Supermemory integration
{
  "tool": "supermemory_status"
}
''')
    ]
    
    for example_name, example_code in examples:
        print(f"\n{example_name}:")
        print("-" * len(example_name) + "-")
        print(example_code.rstrip())
    
    print("\n4. ERROR HANDLING EXAMPLES:")
    print("-" * 50)
    
    error_examples = [
        "Supermemory integration disabled",
        "API key not configured",
        "Node-fetch not available",
        "API call fails (network, auth, etc.)"
    ]
    
    for error in error_examples:
        print(f"   - {error}: Tool returns informative error message")
    
    return True
def main():
    """Run the complete demonstration"""
    print("\n" + "🔧 Supermemory Integration for OmniState" + "\n")
    print("This demonstration shows how OmniState integrates with Supermemory")
    print("to provide enhanced memory management capabilities.")
    
    # Run demonstrations
    demonstrate_configuration()
    demonstrate_bridge_tools()
    demonstrate_usage_examples()
    
    print("\n" + "=" * 70)
    print("INTEGRATION SUMMARY")
    print("=" * 70)
    
    summary_points = [
        "✅ Supermemory configuration added to OmniState config.py",
        "✅ 5 bridge tools implemented for Supermemory API interaction",
        "✅ Environment variables support for flexible configuration",
        "✅ Proper async/await patterns for non-blocking operations",
        "✅ Comprehensive error handling and status reporting",
        "✅ Backward compatible - existing OmniState tools unchanged",
        "✅ Optional integration - can be disabled by setting enabled=false",
        "✅ Bidirectional synchronization between OmniState and Supermemory"
    ]
    
    for point in summary_points:
        print(f"   {point}")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("""
1. Configure Supermemory integration:
   - Set SUPERMEMORY_API_KEY in environment or config
   - Enable integration with SUPERMEMORY_ENABLED=true

2. Test integration:
   - Use supermemory_status to verify configuration
   - Try bridge tools with sample data
   - Check logs for any integration issues

3. Deploy and use:
   - OmniState and Supermemory work together seamlessly
   - Leverage both systems for enhanced memory management
   - Gradually migrate data as needed

For more details, see:
- SUPERMEMORY_INTEGRATION.md (comprehensive documentation)
- test_supermemory_integration.py (test suite)
""")
    
    print("✅ Integration demonstration complete!")
    print("\nThe Supermemory integration for OmniState is ready for use.")
if __name__ == "__main__":
    main()