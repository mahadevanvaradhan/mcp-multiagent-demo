import os
import platform
import requests
import re
import json
import datetime
import tiktoken 
import random
import newsapi
from newsapi import NewsApiClient
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP


# Load environment variables
load_dotenv()
COUNTRY_BASE_URL = os.getenv("COUNTRY_BASE_URL")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_BASE_URL = os.getenv("NEWS_BASE_URL", "https://newsapi.org/v2/top-headlines")


# Common utility functions

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


def get_news_by_region(country: str = "us") -> List[Dict[str, Any]]:
    """
    Fetch the latest news headlines for a specified country using NewsAPI.
       
    Returns:
    - list: List of dictionaries containing article details.
    """
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "country": country,
        "apiKey": NEWS_API_KEY
    }
    
    try:
        # Make the GET request
        response = requests.get(url, params=params)
        
        # Raise an exception if the request failed
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        
        # Return the articles
        return data.get("articles", [])
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
        return f"Error fetching news: {e}"
  
    
if __name__ == "__main__":
    news = get_news_by_region("India")
    print(news)