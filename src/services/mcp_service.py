"""MCP (Model Context Protocol) Server Implementation.

Makes all agents portable and accessible via MCP for integration with Claude Desktop,
IDEs, and other MCP-compatible tools."""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
from src.core.config import Config, PROMPTS
from src.core import EventBus, AgentRegistry
from src.core.contracts import AgentEvent
from src.utils.learning import PerformanceTracker
from main import setup_services, setup_agents

logger = logging.getLogger(__name__)

@dataclass
class MCPAgentTool:
    """MCP Tool representation of an agent capability."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    agent_id: str
    capability: str

class BlogGenMCPServer:
    """MCP Server for Blog Generator agents."""

    def __init__(self):
        """Initialize MCP server."""
        self.server = Server("blog-generator")
        self.config = Config()
        self.event_bus = EventBus(self.config)
        self.registry = AgentRegistry()
        self.performance_tracker = PerformanceTracker()
        self.services = None
        self.agents = None
        self.tools: Dict[str, MCPAgentTool] = {}

        # Setup handlers
        self.server.list_tools()(self.handle_list_tools)
        self.server.call_tool()(self.handle_call_tool)
        self.server.list_resources()(self.handle_list_resources)
        self.server.read_resource()(self.handle_read_resource)
        self.server.list_prompts()(self.handle_list_prompts)
        self.server.get_prompt()(self.handle_get_prompt)

    async def initialize(self):
        """Initialize services and agents."""
        logger.info("Initializing MCP server...")

        # Setup services
        self.services = setup_services(self.config)

        # Setup agents
        self.agents = setup_agents(
            self.config,
            self.event_bus,
            self.registry,
            self.services,
            self.performance_tracker
        )

        # Register agent capabilities as MCP tools
        self._register_agent_tools()

        logger.info(f"MCP server initialized with {len(self.tools)} tools")

    def _register_agent_tools(self):
        """Register all agent capabilities as MCP tools."""
        for agent in self.agents:
            contract = agent.contract

            for capability in contract.capabilities:
                tool_name = f"blog_gen.{capability}"

                # Create tool
                mcp_tool = MCPAgentTool(
                    name=tool_name,
                    description=self._generate_tool_description(agent, capability),
                    input_schema=contract.input_schema,
                    agent_id=contract.agent_id,
                    capability=capability
                )

                self.tools[tool_name] = mcp_tool

    def _generate_tool_description(self, agent: Any, capability: str) -> str:
        """Generate description for an agent capability.

        Args:
            agent: Agent instance
            capability: Capability name

        Returns:
            Tool description"""
        descriptions = {
            "ingest_kb": "Ingest a Knowledge Base article for blog post generation",
            "ingest_blog": "Ingest existing blog posts for context and duplication checking",
            "ingest_api": "Ingest API documentation for code generation context",
            "identify_blog_topics": "Identify potential blog post topics from KB article",
            "check_duplication": "Check if a topic is a duplicate of existing content",
            "gather_rag_kb": "Search KB for relevant context",
            "gather_rag_blog": "Search blog posts for relevant context",
            "gather_rag_api": "Search API docs for code generation context",
            "create_outline": "Create a structured outline for a blog post",
            "write_introduction": "Write an engaging blog post introduction",
            "write_sections": "Write detailed blog post sections",
            "assemble_content": "Assemble final blog post content from parts",
            "generate_code": "Generate complete C# code examples",
            "validate_code": "Validate C# code for quality and API compliance",
            "inject_license": "Inject license header into code",
            "split_code": "Split code into segments for explanation",
            "generate_seo": "Generate SEO metadata for blog post",
            "inject_keywords": "Inject keywords naturally into content",
            "create_gist_readme": "Create README for GitHub Gist",
            "upload_gist": "Upload code and README to GitHub Gist",
            "add_frontmatter": "Add YAML frontmatter to blog post",
            "write_file": "Write final blog post to file",
            "plan": "Orchestrate agent workflow based on state analysis",
            "orchestrate": "Route capabilities to appropriate agents",
            "route": "Select and execute agents based on performance"
        }

        return descriptions.get(
            capability,
            f"Execute {capability} capability via {agent.agent_id}"
        )

    async def handle_list_tools(self) -> List[Tool]:
        """Handle MCP list_tools request.

        Returns:
            List of available tools"""
        tools = []

        for tool_name, mcp_tool in self.tools.items():
            tools.append(Tool(
                name=tool_name,
                description=mcp_tool.description,
                inputSchema=mcp_tool.input_schema
            ))

        logger.info(f"Listed {len(tools)} tools")
        return tools

    async def handle_call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle MCP call_tool request with retry logic.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution results"""
        logger.info(f"Calling tool: {name} with args: {arguments}")

        if name not in self.tools:
            return [TextContent(
                type="text",
                text=f"Error: Tool '{name}' not found"
            )]

        mcp_tool = self.tools[name]

        # Retry configuration
        max_retries = 3
        base_delay = 1.0
        max_delay = 30.0

        for attempt in range(max_retries):
            try:
                # Get the agent
                agent = self.registry.get_agent(mcp_tool.agent_id)

                if not agent:
                    return [TextContent(
                        type="text",
                        text=f"Error: Agent '{mcp_tool.agent_id}' not found"
                    )]

                # Create event
                event = AgentEvent(
                    event_type=f"execute_{mcp_tool.capability}",
                    data=arguments,
                    source_agent="MCP",
                    correlation_id=str(uuid.uuid4())
                )

                # Execute agent
                result = agent.execute(event)

                if result:
                    return [TextContent(
                        type="text",
                        text=json.dumps(result.data, indent=2)
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text="Agent executed successfully but returned no data"
                    )]

            except Exception as e:
                is_last_attempt = attempt == max_retries - 1

                # Check if this is a transient error (connection, timeout, etc.)
                is_transient = any(keyword in str(e).lower() for keyword in [
                    'timeout', 'connection', 'network', 'unavailable', 'busy'
                ])

                if is_transient and not is_last_attempt:
                    # Calculate exponential backoff with jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = delay * 0.1 * (2 * (hash(str(e)) % 100) / 100 - 1)
                    delay_with_jitter = delay + jitter

                    logger.warning(
                        f"MCP tool '{name}' failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {delay_with_jitter:.2f}s: {e}"
                    )

                    # Async sleep
                    await asyncio.sleep(delay_with_jitter)
                    continue
                else:
                    # Non-transient error or last attempt - fail
                    logger.error(f"MCP tool execution failed: {e}", exc_info=True)
                    return [TextContent(
                        type="text",
                        text=f"Error executing tool (attempt {attempt + 1}/{max_retries}): {str(e)}"
                    )]

        # Should not reach here, but just in case
        return [TextContent(
            type="text",
            text=f"Error: Maximum retries ({max_retries}) exceeded"
        )]

    async def handle_list_resources(self) -> List[EmbeddedResource]:
        """Handle MCP list_resources request.

        Returns:
            List of available resources"""
        resources = []

        # Add event log as resource
        if self.event_bus.event_log_path.exists():
            resources.append(EmbeddedResource(
                uri=f"file://{self.event_bus.event_log_path}",
                name="Event Log",
                description="Complete event trace for all agent executions",
                mimeType="application/jsonl"
            ))

        # Add health reports as resources
        resources.append(EmbeddedResource(
            uri="health://agents",
            name="Agent Health Report",
            description="Health status of all registered agents",
            mimeType="application/json"
        ))

        return resources

    async def handle_read_resource(self, uri: str) -> str:
        """Handle MCP read_resource request.

        Args:
            uri: Resource URI

        Returns:
            Resource content"""
        if uri.startswith("file://"):
            # Read file resource
            filepath = Path(uri[7:])
            if filepath.exists():
                with open(filepath, 'r') as f:
                    return f.read()
            else:
                return json.dumps({"error": "File not found"})

        elif uri == "health://agents":
            # Generate health report
            health_report = self.registry.get_health_report()
            return json.dumps(health_report, indent=2)

        else:
            return json.dumps({"error": "Unknown resource URI"})

    async def handle_list_prompts(self) -> List[Dict[str, Any]]:
        """Handle MCP list_prompts request.

        Returns:
            List of available prompts"""
        prompts = []
        for prompt_name, prompt_data in PROMPTS.items():
            prompts.append({
                "name": prompt_name.lower(),
                "description": f"Prompt template for {prompt_name.replace('_', ' ').title()}",
                "arguments": []
            })

        return prompts

    async def handle_get_prompt(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP get_prompt request.

        Args:
            name: Prompt name
            arguments: Prompt arguments

        Returns:
            Prompt content"""
        prompt_name = name.upper()
        if prompt_name not in PROMPTS:
            return {
                "error": f"Prompt '{name}' not found"
            }

        prompt_data = PROMPTS[prompt_name]

        return {
            "system": prompt_data.get("system", ""),
            "user": prompt_data.get("user", "")
        }

async def main():
    """Main entry point for MCP server."""
    server = BlogGenMCPServer()
    await server.initialize()

    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
# DOCGEN:LLM-FIRST@v4