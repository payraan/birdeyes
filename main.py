from fastapi import FastAPI, HTTPException, Query, Header
import requests
import os
import uvicorn
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging
from fastapi.middleware.cors import CORSMiddleware
import time

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Birdeye API",
    description="API for retrieving Solana DeFi data from Birdeye (Standard tier)",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Environment variables
API_KEY = os.getenv("BIRDEYE_API_KEY", "63171bd11b984f239e042b0b169463a4")
BASE_URL = "https://public-api.birdeye.so"

# Rate limiting setup - Standard tier: 10 requests per second
RATE_LIMIT = 10  # requests per second
last_request_time = 0
request_count = 0

@app.get("/")
def home():
    return {"message": "✅ Birdeye API is running!", "version": "1.0.0"}

# Helper function to handle rate limiting
def check_rate_limit():
    global last_request_time, request_count
    current_time = time.time()
    
    # Reset counter if more than 1 second has passed
    if current_time - last_request_time > 1:
        last_request_time = current_time
        request_count = 1
        return True
    
    # Increment counter
    request_count += 1
    
    # Check if we've exceeded rate limit
    if request_count > RATE_LIMIT:
        return False
    
    return True

# Helper function to send requests to Birdeye
async def fetch_from_birdeye(endpoint: str, params: Optional[Dict[str, Any]] = None):
    # Check rate limit
    if not check_rate_limit():
        logger.warning("⚠️ Rate limit exceeded, delaying request")
        time.sleep(1)  # Sleep for 1 second if rate limit exceeded
    
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "X-API-KEY": API_KEY,
        "Accept": "application/json"
    }
    
    logger.info(f"🔍 Sending request to: {url}")
    logger.info(f"🔍 With params: {params}")
    
    try:
        response = requests.get(url, params=params, headers=headers)
        
        logger.info(f"✅ Response status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            logger.error(f"❌ Unauthorized: API key is invalid or missing")
            return {
                "error": "unauthorized",
                "message": "API key is invalid or missing, or you don't have access to this endpoint with your subscription plan.",
                "status_code": 401
            }
        elif response.status_code == 429:
            logger.error(f"❌ Too Many Requests: {response.text}")
            return {
                "error": "rate_limited",
                "message": "Rate limit exceeded. Please try again later.",
                "status_code": 429
            }
        else:
            logger.error(f"⚠ Unexpected Error: {response.text}")
            return {
                "error": "unexpected_error",
                "message": f"Unexpected error with status code {response.status_code}",
                "status_code": response.status_code
            }
    except requests.RequestException as e:
        logger.error(f"❌ Request error: {str(e)}")
        return {
            "error": "connection_error",
            "message": str(e),
            "status_code": 500
        }

# --- VERIFIED WORKING ENDPOINTS ---

# 1️⃣ Token Price (Confirmed working)
@app.get("/public/token/price/{address}")
async def get_token_price_public(
    address: str,
    chain_id: Optional[str] = Query("solana", description="Blockchain ID")
):
    """
    Get current price information for a token (Confirmed working)
    """
    params = {"chain_id": chain_id}
    return await fetch_from_birdeye(f"/defi/price?address={address}", params)

# 2️⃣ Token Historical Price
@app.get("/public/token/history/{address}")
async def get_token_price_history_public(
    address: str,
    type: Optional[str] = Query("1D", description="Time interval (1H, 1D, 1W, 1M, 1Y)"),
    chain_id: Optional[str] = Query("solana", description="Blockchain ID")
):
    """
    Get historical price data for a token
    """
    params = {
        "type": type,
        "chain_id": chain_id
    }
    return await fetch_from_birdeye(f"/defi/price_history?address={address}", params)

# 3️⃣ Token List
@app.get("/public/token/list")
async def get_token_list_public(
    sort_by: Optional[str] = Query("mc", description="Field to sort by (mc, volume, etc.)"),
    sort_type: Optional[str] = Query("d", description="Sort direction (a=ascending, d=descending)"),
    offset: Optional[int] = Query(0, description="Pagination offset"),
    limit: Optional[int] = Query(10, description="Number of results (max 100)"),
    chain_id: Optional[str] = Query("solana", description="Blockchain ID")
):
    """
    Get a list of tokens with sorting and pagination
    """
    params = {
        "sort_by": sort_by,
        "sort_type": sort_type,
        "offset": offset,
        "limit": min(limit, 100),
        "chain_id": chain_id
    }
    return await fetch_from_birdeye("/defi/tokenlist", params)

# 4️⃣ New Token Listings
@app.get("/public/tokens/new")
async def get_new_token_listings_public(
    count: Optional[int] = Query(10, description="Number of results (max 100)"),
    offset: Optional[int] = Query(0, description="Pagination offset"),
    chain_id: Optional[str] = Query("solana", description="Blockchain ID")
):
    """
    Get recently listed tokens
    """
    params = {
        "count": min(count, 100),
        "offset": offset,
        "chain_id": chain_id
    }
    return await fetch_from_birdeye("/defi/v2/tokens/new_listing", params)

# 5️⃣ Token Creation Info 
@app.get("/public/token/creation/{address}")
async def get_token_creation_info_public(address: str):
    """
    Get information about token creation
    """
    return await fetch_from_birdeye(f"/defi/token_creation_info?address={address}")

# 6️⃣ Markets
@app.get("/public/markets")
async def get_markets_public(
    count: Optional[int] = Query(10, description="Number of results (max 100)"),
    offset: Optional[int] = Query(0, description="Pagination offset"),
    sort_by: Optional[str] = Query("v24hUSD", description="Field to sort by"),
    sort_type: Optional[str] = Query("d", description="Sort direction (a=ascending, d=descending)"),
    chain_id: Optional[str] = Query("solana", description="Blockchain ID")
):
    """
    Get market data for token pairs
    """
    params = {
        "count": min(count, 100),
        "offset": offset,
        "sort_by": sort_by,
        "sort_type": sort_type,
        "chain_id": chain_id
    }
    return await fetch_from_birdeye("/defi/v2/markets", params)

# 7️⃣ Token Trending (From docs)
@app.get("/public/tokens/trending")
async def get_trending_tokens_public(
    sort_by: Optional[str] = Query("mc", description="Field to sort by"),
    sort_type: Optional[str] = Query("d", description="Sort direction (a=ascending, d=descending)"),
    offset: Optional[int] = Query(0, description="Pagination offset"),
    limit: Optional[int] = Query(10, description="Number of results (max 100)"),
    chain_id: Optional[str] = Query("solana", description="Blockchain ID")
):
    """
    Get trending tokens
    """
    params = {
        "sort_by": sort_by,
        "sort_type": sort_type,
        "offset": offset,
        "limit": min(limit, 100),
        "chain_id": chain_id
    }
    return await fetch_from_birdeye("/defi/token_trending", params)

# 8️⃣ Search (From docs)
@app.get("/public/search")
async def search_public(
    query: str = Query(..., description="Search query"),
    chain_id: Optional[str] = Query("solana", description="Blockchain ID"),
    limit: Optional[int] = Query(10, description="Number of results (max 100)")
):
    """
    Search for tokens and markets
    """
    params = {
        "q": query,
        "chain_id": chain_id,
        "limit": min(limit, 100)
    }
    return await fetch_from_birdeye("/defi/v3/search", params)

# 9️⃣ OHLCV (From docs)
@app.get("/public/ohlcv/{address}")
async def get_ohlcv_public(
    address: str,
    type: Optional[str] = Query("1D", description="Time interval (1H, 1D, 1W, 1M, 1Y)"),
    count: Optional[int] = Query(100, description="Number of candles"),
    chain_id: Optional[str] = Query("solana", description="Blockchain ID")
):
    """
    Get OHLCV data for a token
    """
    params = {
        "type": type,
        "count": min(count, 1000),
        "chain_id": chain_id
    }
    return await fetch_from_birdeye(f"/defi/ohlcv?address={address}", params)

# Run the server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8087))  # Using port 8087 to avoid conflicts with other APIs
    logger.info(f"🚀 Starting Birdeye API server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
