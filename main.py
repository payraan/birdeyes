from fastapi import FastAPI, HTTPException, Query, Depends, Header
import requests
import os
import uvicorn
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import logging
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Birdeye API",
    description="API for retrieving Solana DeFi data from Birdeye",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Environment variables
API_KEY = os.getenv("BIRDEYE_API_KEY", "63171bd11b984f239e042b0b169463a4")
BASE_URL = "https://public-api.birdeye.so"

@app.get("/")
def home():
    return {"message": "✅ Birdeye API is running!", "version": "1.0.0"}

# Helper function to send requests to Birdeye
async def fetch_from_birdeye(endpoint: str, params: Optional[Dict[str, Any]] = None):
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
        elif response.status_code == 400:
            logger.error(f"❌ Bad Request: {response.text}")
            raise HTTPException(status_code=400, detail=f"❌ Bad Request: {response.text}")
        elif response.status_code == 401:
            logger.error(f"❌ Unauthorized: API key is invalid or missing")
            raise HTTPException(status_code=401, detail="❌ Unauthorized: API key is invalid or missing")
        elif response.status_code == 429:
            logger.error(f"❌ Too Many Requests: {response.text}")
            raise HTTPException(status_code=429, detail="❌ Rate limit exceeded. Please try again later.")
        else:
            logger.error(f"⚠ Unexpected Error: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"⚠ Unexpected Error: {response.text[:200]}")
    except requests.RequestException as e:
        logger.error(f"❌ Request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"❌ Connection Error: {str(e)}")

# 1️⃣ Get token overview
@app.get("/token/overview/{address}")
async def get_token_overview(address: str):
    """
    Get detailed information about a token by its address
    """
    return await fetch_from_birdeye(f"/defi/token_overview?address={address}")

# 2️⃣ Get token list
@app.get("/token/list")
async def get_token_list(
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

# 3️⃣ Get token security
@app.get("/token/security/{address}")
async def get_token_security(address: str):
    """
    Get security metrics and risk assessment for a token
    """
    return await fetch_from_birdeye(f"/defi/token_security?address={address}")

# 4️⃣ Get token creation info
@app.get("/token/creation/{address}")
async def get_token_creation_info(address: str):
    """
    Get information about token creation, mint authority, and initial distribution
    """
    return await fetch_from_birdeye(f"/defi/token_creation_info?address={address}")

# 5️⃣ Get new token listings
@app.get("/tokens/new")
async def get_new_token_listings(
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

# 6️⃣ Get markets
@app.get("/markets")
async def get_markets(
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

# 7️⃣ Get token price
@app.get("/token/price/{address}")
async def get_token_price(
    address: str,
    chain_id: Optional[str] = Query("solana", description="Blockchain ID")
):
    """
    Get current price information for a token
    """
    params = {"chain_id": chain_id}
    return await fetch_from_birdeye(f"/defi/price?address={address}", params)

# 8️⃣ Get token historical price
@app.get("/token/history/{address}")
async def get_token_price_history(
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

# 9️⃣ Get token holders
@app.get("/token/holders/{address}")
async def get_token_holders(
    address: str,
    offset: Optional[int] = Query(0, description="Pagination offset"),
    limit: Optional[int] = Query(10, description="Number of results (max 100)"),
    chain_id: Optional[str] = Query("solana", description="Blockchain ID")
):
    """
    Get information about token holders
    """
    params = {
        "offset": offset,
        "limit": min(limit, 100),
        "chain_id": chain_id
    }
    return await fetch_from_birdeye(f"/defi/token_holders?address={address}", params)

# 🔟 Get trending tokens
@app.get("/tokens/trending")
async def get_trending_tokens(
    count: Optional[int] = Query(10, description="Number of results (max 100)"),
    chain_id: Optional[str] = Query("solana", description="Blockchain ID")
):
    """
    Get trending tokens based on recent activity
    """
    params = {
        "count": min(count, 100),
        "chain_id": chain_id
    }
    return await fetch_from_birdeye("/defi/trending_tokens", params)

# Run the server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8087))  # Using port 8087 to avoid conflicts with other APIs
    logger.info(f"🚀 Starting Birdeye API server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
