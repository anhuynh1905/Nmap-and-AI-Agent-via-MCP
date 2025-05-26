import asyncio
from typing import Optional
from openai import OpenAI
from fastmcp import Client
from contextlib import AsyncExitStack
import json # Added import

from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv('DEEPSEEK_API_KEY')
http_url = "http://127.0.0.1:8000/nmap_mcp_server"

class MCPClient:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.chat = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
        self.messages = []  # Persistent conversation history

    async def connect_to_server(self):
        self.client = await self.exit_stack.enter_async_context(Client(http_url))
        tools = await self.client.list_tools()

        print("\nConnected to server with tools: ", [tool.name for tool in tools])
        
        # Initialize system message once when connecting
        tool_descriptions = []
        for tool in tools:
            tool_descriptions.append(f"- {tool.name}: {tool.description}")
        
        system_message_content = "You are a helpful assistant. You have access to the following tools. Please use them when appropriate to answer the user's query. Format your response to use a tool if necessary.\nAvailable tools:\n" + "\n".join(tool_descriptions)
        
        self.messages = [{"role": "system", "content": system_message_content}]

    async def process_query(self, query: str) -> str:
        """Process a query using Deepseek and available tools"""

        tools_list = await self.client.list_tools()
        
        # Add user message to persistent conversation history
        self.messages.append({"role": "user", "content": query})

        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in tools_list]

        # Initial API call
        response = self.chat.chat.completions.create( # Synchronous call
            model="deepseek-chat",
            tools=available_tools,
            messages=self.messages
        )

        final_text = []
        assistant_message = response.choices[0].message

        # Append assistant's response to messages history
        self.messages.append(assistant_message)

        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_arguments_str = tool_call.function.arguments
                try:
                    tool_args = json.loads(tool_arguments_str)
                except json.JSONDecodeError as e:
                    print(f"Error decoding arguments for tool {tool_name}: {tool_arguments_str}. Error: {e}")
                    final_text.append(f"[Error: Could not decode arguments for tool {tool_name}]")
                    continue

                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                tool_result_from_call = await self.call_tool(tool_name, tool_args)
                
                actual_tool_result_object = None
                if isinstance(tool_result_from_call, list):
                    if tool_result_from_call: # Check if the list is not empty
                        actual_tool_result_object = tool_result_from_call[0] # Assume the first element is the ToolResult
                        if len(tool_result_from_call) > 1:
                            print(f"DEBUG: call_tool for {tool_name} returned a list with {len(tool_result_from_call)} items. Using the first one.")
                    else:
                        print(f"Error: call_tool for {tool_name} returned an empty list.")
                        final_text.append(f"[Error: Tool {tool_name} returned no result]")
                        continue # Skip processing for this tool_call
                else: # Not a list, assume it's the ToolResult object itself
                    actual_tool_result_object = tool_result_from_call
                
                tool_output_content = None
                if hasattr(actual_tool_result_object, 'content'):
                    tool_output_content = actual_tool_result_object.content
                elif hasattr(actual_tool_result_object, 'text'): # Check for .text if .content is not found
                    tool_output_content = actual_tool_result_object.text
                else:
                    print(f"Error: Result object for tool {tool_name} (type: {type(actual_tool_result_object)}, value: {actual_tool_result_object}) has neither 'content' nor 'text' attribute.")
                    final_text.append(f"[Error: Malformed result from tool {tool_name}]")
                    continue # Skip processing for this tool_call

                # Ensure tool_output_content is a string for the API
                if not isinstance(tool_output_content, str):
                    try:
                        tool_output_content = json.dumps(tool_output_content)
                    except TypeError as e:
                        print(f"Error serializing tool output for {tool_name}: {tool_output_content}. Error: {e}")
                        tool_output_content = f"Error: Could not serialize output for tool {tool_name}"
                
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": tool_output_content,
                })
            
            # Make a follow-up call to the model with the tool response(s)
            follow_up_response = self.chat.chat.completions.create( # Synchronous call
                model="deepseek-chat",
                # tools=available_tools, # You might not want to allow tools in the follow-up, or you might.
                messages=self.messages
            )
            follow_up_message = follow_up_response.choices[0].message
            
            # Append the assistant's final response to messages history
            self.messages.append(follow_up_message)

            if follow_up_message.content:
                final_text.append(follow_up_message.content)
            else:
                final_text.append("[Assistant did not provide a text response after tool use]")

        elif assistant_message.content:
            final_text.append(assistant_message.content)
        else:
            final_text.append("[Assistant did not provide text or tool calls]")

        return "\\n".join(final_text)
    
    async def call_tool(self, tool_name: str, tool_args: dict): # Added definition from previous context
        """Call a tool from the MCP server"""
        # Assuming self.client is the MCP client instance
        return await self.client.call_tool(tool_name, tool_args)

    def reset_conversation(self):
        """Reset the conversation history, keeping only the system message"""
        if self.messages and self.messages[0]["role"] == "system":
            self.messages = [self.messages[0]]  # Keep only system message
        else:
            self.messages = []

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client started!")
        print("\nType your queries, 'reset' to clear conversation history, or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break
                elif query.lower() == 'reset':
                    self.reset_conversation()
                    print("Conversation history cleared.")
                    continue

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()

    try:
        await client.connect_to_server()
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())