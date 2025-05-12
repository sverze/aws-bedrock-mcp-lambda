import json
import asyncio
import os
import sys
from typing import Dict, Any

# Add the Lambda directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Add the Lambda layer's Python directory to the Python path (for dependencies)
sys.path.append("/opt/python")

from mcp_client import MCPClient
from logging_utils import logger

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda function that processes a query using the MCP client.
    
    Parameters:
    event (dict): Event data containing the query
    context (object): Runtime information
    
    Returns:
    dict: Response with statusCode and body
    """
    logger.info(f"Handling MCP event: {event}")
    # Extract query from event - handle both query and queryStringParameters
    query_params = event.get('queryStringParameters', {}) or {}
    query = query_params.get('query', '')

    if not query:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Missing query parameter',
                'usage': 'Add a query parameter to your request'
            })
        }
    
    try:
        # Run the MCP client with the query
        result = asyncio.run(process_query(query))
        logger.info(f"MCP event completed")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'query': query,
                'result': result
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error processing query',
                'error': str(e)
            })
        }

async def process_query(query: str) -> str:
    """Process a query using the MCP client."""
    logger.info(f"Process query: {query}")

    client = MCPClient()
    try:
        # Connect to the MCP server
        server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mcp_server.py')
        await client.connect_to_server(server_path)
        
        # Process the query
        result = await client.process_query(query)
        logger.info(f"Query completed")

        return result
    finally:
        # Clean up resources
        await client.cleanup()
