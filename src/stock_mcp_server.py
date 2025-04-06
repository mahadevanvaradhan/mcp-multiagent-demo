import os
import platform
import requests
import re
import json
import datetime
import random
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP


# Load environment variables
load_dotenv()


PHONE_VERIFY_BASE_URL = os.getenv("PHONE_VERIFY_BASE_URL")
PHONE_VERIFY_KEY = os.getenv("PHONE_VERIFY_KEY")
COUNTRY_BASE_URL = os.getenv("COUNTRY_BASE_URL")
ALPHAVANTAGE_BASE_URL = os.getenv("ALPHAVANTAGE_BASE_URL")
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
MCP_SERVER_PORT = os.getenv("STOCK_MCP_SERVER_PORT", "8001")
MCP_SERVER_URL = f"http://localhost:{MCP_SERVER_PORT}"


mcp = FastMCP(
    "Share Stock Details",
    instructions="Validate Phone number and provide Stock Details",
    debug=False,
    log_level="INFO",
    host="0.0.0.0",
    port=int(MCP_SERVER_PORT) 
)


def get_country_info_custom(country_name):
    url = COUNTRY_BASE_URL + country_name
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        data = response.json()
        # Extract first result
        country = data[0]
        
        # Get currency info (handling multiple currencies if present)
        currencies = country.get("currencies", {})
        currency_code = list(currencies.keys())[0] if currencies else "N/A"
        currency_name = currencies[currency_code]["name"] if currencies else "N/A"
        currency_symbol = currencies[currency_code]["symbol"] if currencies else "N/A"
        
        return {
            "name": country["name"]["common"],
            "capital": country["capital"][0] if country.get("capital") else "N/A",
            "region": country.get("region", "N/A"),
            "country_code": country.get("cca2", "N/A"),
            "tld": country["tld"][0] if country.get("tld") else "N/A",
            "currency": currency_name,
            "currency_symbol": currency_symbol,
            "population": country.get("population", "N/A")
        }
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"
    except (IndexError, KeyError, TypeError):
        return "Error: Country data not found or malformed response"


# Custom Function 1
@mcp.tool()
def validate_phone_number(phone: str, country: str):

    country_info = get_country_info_custom(country)
    if isinstance(country_info, str):  # Check if an error message was returned
       return
    country_code = country_info["country_code"]
    # API endpoint and parameters
    url = PHONE_VERIFY_BASE_URL
    params = {
        "api_key": PHONE_VERIFY_KEY,
        "phone": phone,
        "country": country_code
    }
    
    try:
        # Make the GET request
        response = requests.get(url, params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Print the response text
            print("API Response:", response.text)
            return response.json()
        else:
            print(f"Error: Received status code {response.status_code}")
            
    except requests.RequestException as e:
        print(f"Error making request: {e}")

# Custom Function 2
@mcp.tool()
def get_stock_data(symbol, interval="5min", function="TIME_SERIES_INTRADAY"):
   
    url = ALPHAVANTAGE_BASE_URL
    params = {
        "apikey": ALPHAVANTAGE_API_KEY,
        "symbol": symbol,
        "interval": interval,
        "function": function
    }
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()  
        data = res.json()
        if "Error Message" in data:
            return {"error": data["Error Message"]}
        elif "Information" in data:
            return {"info": data["Information"]}  
        else:
            return data
            
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}       
  
    
if __name__ == "__main__":
    mcp.run(transport="sse")