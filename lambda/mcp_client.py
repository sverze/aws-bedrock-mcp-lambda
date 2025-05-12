from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
from dataclasses import dataclass

# to interact with MCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from logging_utils import logger

import boto3

@dataclass
class Message:
    role: str
    content: List[Dict[str, Any]]

    @classmethod
    def user(cls, text: str) -> 'Message':
        return cls(role="user", content=[{"text": text}])

    @classmethod
    def assistant(cls, text: str) -> 'Message':
        return cls(role="assistant", content=[{"text": text}])

    @classmethod
    def tool_result(cls, tool_use_id: str, content: dict) -> 'Message':
        return cls(
            role="user",
            content=[{
                "toolResult": {
                    "toolUseId": tool_use_id,
                    "content": [{"json": {"text": content[0].text}}]
                }
            }]
        )

    @classmethod
    def tool_request(cls, tool_use_id: str, name: str, input_data: dict) -> 'Message':
        return cls(
            role="assistant",
            content=[{
                "toolUse": {
                    "toolUseId": tool_use_id,
                    "name": name,
                    "input": input_data
                }
            }]
        )

    @staticmethod
    def to_bedrock_format(tools_list: List[Dict]) -> List[Dict]:
        return [{
            "toolSpec": {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": tool["input_schema"]["properties"],
                        "required": tool["input_schema"]["required"]
                    }
                }
            }
        } for tool in tools_list]


class MCPClient:
    MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')

    async def connect_to_server(self, server_script_path: str):
        if not server_script_path.endswith(('.py', '.js')):
            raise ValueError("Server script must be a .py or .js file")

        # Determine the command to run based on the server script extension
        logger.info(f"MCP client running server script: {server_script_path}")
        command = "python" if server_script_path.endswith('.py') else "node"
        server_params = StdioServerParameters(command=command, args=[server_script_path], env=None)

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

    async def cleanup(self):
        await self.exit_stack.aclose()

    def _make_bedrock_request(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        return self.bedrock.converse(
            modelId=self.MODEL_ID,
            messages=messages,
            inferenceConfig={"maxTokens": 1000, "temperature": 0},
            toolConfig={"tools": tools}
        )

    async def process_query(self, query: str) -> str:
        logger.info(f"Processing query: {query}")
        messages = [Message.user(query).__dict__]
        response = await self.session.list_tools()

        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]
        logger.info(f"Available tools: {available_tools}")
        bedrock_tools = Message.to_bedrock_format(available_tools)

        response = self._make_bedrock_request(messages, bedrock_tools)
        logger.info(f"Bedrock response: {response}")

        return await self._process_response(
            response, messages, bedrock_tools
        )

    async def _process_response(self, response: Dict, messages: List[Dict], bedrock_tools: List[Dict]) -> str:
        final_text = []
        MAX_TURNS = 10
        turn_count = 0

        logger.info(f"Processing response: {response}")

        while True:
            if response['stopReason'] == 'tool_use':
                final_text.append("received toolUse request")
                for item in response['output']['message']['content']:
                    if 'text' in item:
                        logger.info(f"Received toolUse request: {item['text']}")
                        final_text.append(f"[Thinking: {item['text']}]")
                        messages.append(Message.assistant(item['text']).__dict__)
                    elif 'toolUse' in item:
                        logger.info(f"Received toolUse response: {item['toolUse']}")
                        tool_info = item['toolUse']
                        result = await self._handle_tool_call(tool_info, messages)
                        final_text.extend(result)

                        response = self._make_bedrock_request(messages, bedrock_tools)
            elif response['stopReason'] == 'max_tokens':
                logger.info("Max tokens reached, ending conversation.")
                final_text.append("[Max tokens reached, ending conversation.]")
                break
            elif response['stopReason'] == 'stop_sequence':
                logger.info("Stop sequence reached, ending conversation.")
                final_text.append("[Stop sequence reached, ending conversation.]")
                break
            elif response['stopReason'] == 'content_filtered':
                logger.info("Content filtered, ending conversation.")
                final_text.append("[Content filtered, ending conversation.]")
                break
            elif response['stopReason'] == 'end_turn':
                logger.info("End turn reached, ending conversation.")
                final_text.append(response['output']['message']['content'][0]['text'])
                break

            turn_count += 1

            if turn_count >= MAX_TURNS:
                logger.info("Max turns reached, ending conversation.")
                final_text.append("\n[Max turns reached, ending conversation.]")
                break
        return "\n\n".join(final_text)

    async def _handle_tool_call(self, tool_info: Dict, messages: List[Dict]) -> List[str]:
        tool_name = tool_info['name']
        tool_args = tool_info['input']
        tool_use_id = tool_info['toolUseId']

        logger.info(f"Calling tool {tool_name} with args {tool_args}")

        result = await self.session.call_tool(tool_name, tool_args)

        messages.append(Message.tool_request(tool_use_id, tool_name, tool_args).__dict__)
        messages.append(Message.tool_result(tool_use_id, result.content).__dict__)

        logger.info(f"Tool {tool_name} called with result {result.content}")

        return [f"[Calling tool {tool_name} with args {tool_args}]"]
