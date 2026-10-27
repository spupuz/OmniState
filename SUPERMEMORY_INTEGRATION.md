# Supermemory Integration for OmniState

## Overview

This integration adds Supermemory MCP bridge tools to the OmniState MCP server, enabling seamless communication between OmniState's memory management capabilities and Supermemory's advanced memory API.

## Integration Approach (Option 3: Bridge tools in OmniState)

### What Was Added

1. **Supermemory Configuration** (`server/config.py`)
   - Added `SupermemoryConfig` dataclass with API key, base URL, API version, default space, and enabled flag
   - Updated `Config` class to include Supermemory configuration
   - Added environment variables support (`SUPERMEMORY_API_KEY`, `SUPERMEMORY_BASE_URL`, etc.)

2. **Supermemory Bridge Tools** (`server/mcp_server.py`)
   - `supermemory_search`: Search Supermemory memories
   - `supermemory_profile`: Get user profile from Supermemory  
   - `supermemory_add`: Add a memory to Supermemory
   - `supermemory_sync`: Sync OmniState memories with Supermemory
   - `supermemory_status`: Get Supermemory integration status

### Key Features

1. **Bidirectional Integration**: OmniState can both read from and write to Supermemory
2. **Smart Namespace Handling**: Uses configured default space or allows project-specific namespaces
3. **Status Checking**: Verify Supermemory integration is properly configured
4. **Error Handling**: Graceful handling of API failures and missing configurations
5. **Asynchronous Operations**: All Supermemory API calls are async and non-blocking

### Configuration

#### Environment Variables

```bash
# Required for Supermemory integration
SUPERMEMORY_API_KEY=your_supermemory_api_key
SUPERMEMORY_BASE_URL=https://api.supermemory.ai  # or your self-hosted instance
SUPERMEMORY_ENABLED=true

# Optional
SUPERMEMORY_API_VERSION=v5
SUPERMEMORY_DEFAULT_SPACE=sm_project_default
```

#### Configuration File (`/data/config.json`)

```json
{
  "supermemory": {
    "api_key": "your_api_key",
    "base_url": "https://api.supermemory.ai",
    "api_version": "v5",
    "default_space": "sm_project_default",
    "enabled": true
  }
}
```

### Tool Usage

#### 1. Check Supermemory Status

```
# Check if Supermemory integration is working
{
  "tool": "supermemory_status",
  "name": "Get Supermemory integration status"
}
```

**Response:**
```json
{
  "enabled": true,
  "api_key_configured": true,
  "base_url": "https://api.supermemory.ai",
  "api_version": "v5",
  "default_space": "sm_project_default",
  "status": "configured"
}
```

#### 2. Search Supermemory Memories

```
# Search memories in Supermemory
{
  "tool": "supermemory_search",
  "name": "Search Supermemory memories",
  "arguments": {
    "query": "user preferences about React",
    "namespace": "sm_project_default",
    "limit": 10,
    "scope": "shared"
  }
}
```

#### 3. Get Supermemory Profile

```
# Get user profile from Supermemory
{
  "tool": "supermemory_profile", 
  "name": "Get Supermemory profile",
  "arguments": {
    "namespace": "sm_project_default"
  }
}
```

#### 4. Add Memory to Supermemory

```
# Save a memory to Supermemory
{
  "tool": "supermemory_add",
  "name": "Add memory to Supermemory", 
  "arguments": {
    "content": "User prefers TypeScript and functional programming patterns",
    "namespace": "sm_project_default",
    "title": "User Preferences",
    "tags": "preference,typeScript,functional",
    "source": "omnistate-bridge"
  }
}
```

#### 5. Sync OmniState with Supermemory

```
# Sync memories from OmniState to Supermemory
{
  "tool": "supermemory_sync",
  "name": "Sync OmniState with Supermemory",
  "arguments": {
    "project": "my-react-project",
    "namespace": "sm_project_default",
    "limit": 50
  }
}
```

### Benefits

1. **Unified Memory Strategy**: Leverage both OmniState's project-structured memory and Supermemory's advanced memory features
2. **No Code Changes Required**: Existing OmniState functionality remains intact
3. **Flexible Configuration**: Enable/disable Supermemory integration as needed
4. **Backward Compatible**: Existing tools and workflows continue to work unchanged
5. **Performance Optimized**: Asynchronous operations prevent blocking

### Limitations

1. **Runtime Dependency**: Requires Node.js runtime with `node-fetch` for HTTP API calls
2. **Configuration Required**: Must set up Supermemory API credentials
3. **Simulated Mode**: In non-Node environments, tools simulate API responses with notes

### Testing

The integration includes comprehensive error handling and status reporting:

1. **Status Check**: Verify configuration before API calls
2. **Graceful Degradation**: Tools provide informative messages when dependencies are missing
3. **Async Operations**: Proper async/await patterns for non-blocking operations

### Migration Considerations

- **Zero Breaking Changes**: Existing OmniState tools and workflows unchanged
- **Optional Feature**: Supermemory integration can be disabled by setting `enabled: false`
- **No Data Migration**: Integration is read/write, not a migration path

### Security Notes

1. **API Key Protection**: Never log or expose API keys in plain text
2. **Environment Variables**: Use environment variables for sensitive configuration
3. **Token Management**: API keys are stored in configuration files with proper security

## Usage Examples

### Example 1: Complete Workflow

```python
# 1. Check Supermemory integration status
status = call_tool("supermemory_status")
if status["enabled"]:
    print("Supermemory integration available")
    
    # 2. Search for existing memories
    search_result = call_tool("supermemory_search", 
                           query="previous project setup",
                           namespace="sm_project_default")
    
    # 3. Add new memory
    add_result = call_tool("supermemory_add",
                         content="Project uses React with TypeScript",
                         title="Project Configuration",
                         namespace="sm_project_default")
    
    # 4. Sync with current project
    sync_result = call_tool("supermemory_sync",
                          project="current-project",
                          namespace="sm_project_default")
```

### Example 2: Conditional Integration

```python
# Check if Supermemory is properly configured
status = call_tool("supermemory_status")

if status["status"] == "configured":
    # Use Supermemory for advanced memory operations
    profile = call_tool("supermemory_profile")
    memories = call_tool("supermemory_search", query="user preferences")
    
    # Store results back to OmniState if needed
    sync_result = call_tool("supermemory_sync", project="active-project")
else:
    # Fall back to OmniState-only operations
    print("Supermemory not configured, using OmniState only")
```

## Conclusion

The Supermemory integration for OmniState provides a powerful bridge between two memory management systems, enabling users to:

- Leverage Supermemory's advanced memory features while maintaining OmniState's project structure
- Synchronize memories between systems for redundancy and accessibility
- Use both systems' strengths for different use cases

This integration follows the recommended Option 3 approach, providing the best of both worlds with minimal configuration overhead.