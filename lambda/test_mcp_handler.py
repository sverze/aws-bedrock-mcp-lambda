import json
from mcp_handler import handler


if __name__ == "__main__":
    # Simulate an API Gateway event
    event = {
        'queryStringParameters': {
        'query': 'What\'s the weather in New York?'
        }
    }

    # Call the handler function
    response = handler(event, None)

    # Print the response
    print(json.dumps(response, indent=2))
