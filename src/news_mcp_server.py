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
MCP_SERVER_PORT = os.getenv("NEWS_MCP_SERVER_PORT", "8002")
MCP_SERVER_URL = f"http://localhost:{MCP_SERVER_PORT}"


# Common utility functions

def get_full_path(path: str) -> str:
    """Convert a path to an absolute path."""
    return os.path.abspath(os.path.expanduser(path))

def format_error_response(error: str, details: Optional[str] = None) -> Dict[str, Any]:
    """Format a standardized error response."""
    response = {"error": error}
    if details:
        response["details"] = details
    return response

def _format_report_content(title: str, content: Dict[str, Any], format: str) -> str:
    """Helper function to format report content based on the specified format."""
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if format == "markdown":
        report_text = f"# {title}\n\n"
        report_text += f"*Generated on {current_time}*\n\n"
        
        for section, section_content in content.items():
            report_text += f"## {section}\n\n"
            if isinstance(section_content, (list, tuple)):
                for item in section_content:
                    report_text += f"- {item}\n"
            elif isinstance(section_content, dict):
                for key, value in section_content.items():
                    report_text += f"**{key}**: {value}\n"
            else:
                report_text += f"{section_content}\n"
            report_text += "\n"
    
    elif format == "html":
        report_text = f"<!DOCTYPE html>\n<html>\n<head>\n<title>{title}</title>\n"
        report_text += "<style>body{font-family:Arial,sans-serif;margin:40px;line-height:1.6}"
        report_text += "h1{color:#333}h2{color:#444;margin-top:30px}</style>\n</head>\n<body>\n"
        report_text += f"<h1>{title}</h1>\n"
        report_text += f"<p><em>Generated on {current_time}</em></p>\n"
        
        for section, section_content in content.items():
            report_text += f"<h2>{section}</h2>\n"
            if isinstance(section_content, (list, tuple)):
                report_text += "<ul>\n"
                for item in section_content:
                    report_text += f"<li>{item}</li>\n"
                report_text += "</ul>\n"
            elif isinstance(section_content, dict):
                report_text += "<dl>\n"
                for key, value in section_content.items():
                    report_text += f"<dt><strong>{key}</strong></dt>\n<dd>{value}</dd>\n"
                report_text += "</dl>\n"
            else:
                report_text += f"<p>{section_content}</p>\n"
                
        report_text += "</body>\n</html>"
    
    elif format == "txt":
        report_text = f"{title.upper()}\n"
        report_text += "=" * len(title) + "\n\n"
        report_text += f"Generated on {current_time}\n\n"
        
        for section, section_content in content.items():
            report_text += f"{section}\n"
            report_text += "-" * len(section) + "\n"
            if isinstance(section_content, (list, tuple)):
                for item in section_content:
                    report_text += f"* {item}\n"
            elif isinstance(section_content, dict):
                for key, value in section_content.items():
                    report_text += f"{key}: {value}\n"
            else:
                report_text += f"{section_content}\n"
            report_text += "\n"
    
    else:  # json
        # For JSON, we create a structured document
        report_data = {
            "title": title,
            "generated_at": current_time,
            "content": content
        }
        report_text = json.dumps(report_data, indent=2)
    
    return report_text



mcp = FastMCP(
    "NLP and News Analytics",
    instructions="NLP and News Analytics",
    debug=False,
    log_level="INFO",
    host="0.0.0.0",
    port=int(MCP_SERVER_PORT) 
)

# Custom Function 1
@mcp.tool()
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

# Custom Function 2
@mcp.tool()
def calculate_token_length(text, model="gpt-3.5-turbo", show_tokens=False):
    """
    Calculate the number of tokens in a given text for a specified LLM model.
    
    Parameters:
    - text (str): The input text to tokenize.
    - model (str): The LLM model to determine the encoding (default: "gpt-3.5-turbo").
    - show_tokens (bool): If True, print the token IDs (default: False).
    
    Returns:
    - int: The number of tokens in the text.
    """
    # Get the encoding for the specified model
    encoding = tiktoken.encoding_for_model(model)
    
    # Encode the text into tokens
    tokens = encoding.encode(text)
    
    # Calculate token count
    token_count = len(tokens)
    
    # Optionally display token IDs
    if show_tokens:
        print(f"Token IDs: {tokens}")
    
    return token_count

# Custom Function 3
@mcp.tool()
def analyze_text(text: str) -> Dict[str, Any]:
    """
    Analyze text to extract statistics and information.
    
    Args:
        text: The text to analyze
    
    Returns:
        Text statistics including word count, character count, etc.
    """
    try:
        # Remove excess whitespace
        cleaned_text = re.sub(r'\s+', ' ', text).strip()
        
        # Count words
        words = cleaned_text.split()
        word_count = len(words)
        
        # Count sentences (basic)
        sentences = re.split(r'[.!?]+', cleaned_text)
        sentence_count = sum(1 for s in sentences if s.strip())
        
        # Count paragraphs
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        
        # Find most common words
        word_freq = {}
        for word in words:
            word_lower = word.lower()
            word_freq[word_lower] = word_freq.get(word_lower, 0) + 1
            
        common_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "character_count": len(text),
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "average_word_length": sum(len(word) for word in words) / word_count if word_count else 0,
            "average_sentence_length": word_count / sentence_count if sentence_count else 0,
            "most_common_words": [{"word": word, "count": count} for word, count in common_words]
        }
    except Exception as e:
        return format_error_response(f"Failed to analyze text: {str(e)}")
    
# Custom Function 4
@mcp.tool()
def generate_report(title: str = "", content: dict = None, format: str = "markdown", filename: str = "") -> Dict[str, Any]:
    """
    Generate and save a formatted report. This tool can automatically generate content if not provided.
    
    Args:
        title: Report title (if empty, will generate a default title)
        content: Dictionary containing report content sections (if empty, will generate sample content)
        format: Output format (markdown, html, txt, json)
        filename: Optional filename (without extension), defaults to title_YYYYMMDD if empty
    
    Returns:
        Information about the saved report
    """
    try:
        # Generate default title if none provided
        if not title:
            topics = ["Status Report", "Project Overview", "Weekly Summary", "Monthly Analysis", 
                      "Performance Review", "System Health Check", "Progress Update"]
            title = f"Auto-generated {random.choice(topics)}"
            print(f"[Auto-generated title: {title}]")
        
        # Generate sample content if none provided
        if not content or not isinstance(content, dict):
            current_time = datetime.datetime.now()
            content = {
                "Summary": "This is an automatically generated report with sample content.",
                "Date Information": {
                    "Generation Date": current_time.strftime("%Y-%m-%d"),
                    "Generation Time": current_time.strftime("%H:%M:%S"),
                    "Day of Week": current_time.strftime("%A"),
                    "Month": current_time.strftime("%B")
                },
                "Sample Metrics": [
                    f"Metric A: {random.randint(75, 99)}%",
                    f"Metric B: {random.randint(50, 100)} units",
                    f"Metric C: {random.uniform(0.1, 0.9):.2f} ratio"
                ],
                "System Information": {
                    "OS": platform.system(),
                    "Python Version": platform.python_version(),
                    "Machine": platform.machine()
                },
                "Notes": "This content was automatically generated because no content was provided."
            }
            print("[Auto-generated sample content]")
            
        valid_formats = ["markdown", "html", "txt", "json"]
        if format.lower() not in valid_formats:
            format = "markdown"
            print(f"[Invalid format specified, defaulting to markdown]")
            
        # Generate default filename if none provided
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if not filename:
            # Create safe filename from title
            safe_title = "".join(c if c.isalnum() else "_" for c in title).lower()
            filename = f"{safe_title}_{timestamp}"
            
        # Ensure filename doesn't have extension
        filename = filename.split('.')[0]
        
        # Add appropriate extension based on format
        format = format.lower()
        ext_map = {
            "markdown": "md",
            "html": "html",
            "txt": "txt",
            "json": "json"
        }
        ext = ext_map.get(format, "md")
        full_filename = f"{filename}.{ext}"
        
        # Create report content based on format
        report_text = _format_report_content(title, content, format)
            
        # Save the report
        reports_dir = get_full_path("reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        file_path = os.path.join(reports_dir, full_filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
            
        # Return success info
        rel_path = os.path.join("reports", full_filename)
        return {
            "status": "success",
            "title": title,
            "format": format,
            "filename": full_filename,
            "path": rel_path,
            "absolute_path": file_path,
            "size_bytes": len(report_text),
            "sections": list(content.keys()),
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "auto_generated": not bool(title) or not bool(content)
        }
    except Exception as e:
        return format_error_response(
            f"Failed to generate report: {str(e)}",
            "Check your input content and try again"
        )

# Custom Function 5
@mcp.tool()
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
    mcp.run(transport="sse")