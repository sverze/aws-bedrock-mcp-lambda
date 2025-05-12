from typing import Any
import sys

# Ensure we can find packages in the Lambda layer
sys.path.insert(0, '/opt/python')

import httpx
from mcp.server.fastmcp import FastMCP

import re
import requests
from markdownify import markdownify
from requests.exceptions import RequestException
from logging_utils import logger

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

async def make_nws_request(url: str) -> dict[str, Any] | None:
    logger.info(f"Making news request: {url}")
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            logger.info(f"Response status: {response.status_code}")
            return response.json()
        except Exception:
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    logger.info(f"Fetching alerts for state: {state}")
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    logger.info(f"Found {len(alerts)} alerts")
    return "\n---\n".join(alerts)

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    logger.info(f"Fetching forecast for latitude: {latitude}, longitude: {longitude}")
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    logger.info(f"Found {len(forecasts)} forecasts")
    return "\n---\n".join(forecasts)

@mcp.tool()
def visit_webpage(url: str) -> str:
    """Visits a webpage at the given URL and returns its content as a markdown string.

    Args:
        url: The URL of the webpage to visit.

    Returns:
        The content of the webpage converted to Markdown, or an error message if the request fails.
    """
    logger.info(f"Visiting webpage: {url}")
    try:
        # Send a GET request to the URL
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Convert the HTML content to Markdown
        markdown_content = markdownify(response.text).strip()

        # Remove multiple line breaks
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        logger.info(f"Converted {len(markdown_content.splitlines())} lines of markdown")
        return markdown_content

    except RequestException as e:
        return f"Error fetching the webpage: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

# @mcp.tool()
# def validate_links(urls: list[str]) -> list[str, bool]:
#     """Validates that the links are valid webpages.
#
#     Args:
#         urls: The URLs of the webpages to visit.
#
#     Returns:
#         A list of the url and boolean of whether or not the link is valid.
#     """
#     logger.info(f"Validating links: {urls}")
#     output = []
#     for url in urls:
#         try:
#             # Send a GET request to the URL
#             response = requests.get(url, timeout=30)
#             response.raise_for_status()  # Raise an exception for bad status codes
#             print('validateResponse', response)
#             # Check if the response content is not empty
#             if response.text.strip():
#                 output.append([url, True])
#             else:
#                 output.append([url, False])
#         except RequestException as e:
#             output.append([url, False])
#             print(f"Error fetching the webpage: {str(e)}")
#         except Exception as e:
#             output.append([url, False])
#             print(f"An unexpected error occurred: {str(e)}")
#     logger.info(f"Validated {len(output)} links")
#     return output

if __name__ == "__main__":
    # Initialize and run the server
    logger.info("Starting MCP server")
    mcp.run(transport='stdio')
