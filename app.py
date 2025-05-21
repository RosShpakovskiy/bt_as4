import streamlit as st
import requests
import ollama
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configurations
CRYPTO_PANIC_API = "https://cryptopanic.com/api/v1/posts/"
BINANCE_API = "https://api.binance.com/api/v3"
COINGECKO_API = "https://api.coingecko.com/api/v3"

# Initialize APIs
CRYPTO_PANIC_TOKEN = os.getenv("CRYPTO_PANIC_TOKEN")

# Comprehensive crypto mapping
CRYPTO_MAP = {
    'bitcoin': {'symbols': ['btc'], 'binance': 'BTCUSDT', 'coingecko': 'bitcoin'},
    'ethereum': {'symbols': ['eth'], 'binance': 'ETHUSDT', 'coingecko': 'ethereum'},
    'solana': {'symbols': ['sol'], 'binance': 'SOLUSDT', 'coingecko': 'solana'},
    'bnb': {'symbols': ['bnb'], 'binance': 'BNBUSDT', 'coingecko': 'binancecoin'},
    'xrp': {'symbols': ['xrp'], 'binance': 'XRPUSDT', 'coingecko': 'ripple'},
    'cardano': {'symbols': ['ada'], 'binance': 'ADAUSDT', 'coingecko': 'cardano'}
}

st.title("🔗 Blockchain Market AI")

# -----------------------------------------
# API Helper Functions
# -----------------------------------------
def get_crypto_news(crypto_key):
    """
    Fetches the latest news for a given cryptocurrency key using CryptoPanic API.
    """
    try:
        with st.spinner("Fetching latest news..."):
            symbol = CRYPTO_MAP.get(crypto_key, {}).get('symbols', [crypto_key])[0].upper()
            params = {
                'auth_token': CRYPTO_PANIC_TOKEN,
                'currencies': symbol,
                'kind': 'news',
                'public': 'true'
            }
            response = requests.get(CRYPTO_PANIC_API, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            results = data.get('results', [])

            news_list = []
            for item in results[:3]:
                created = item.get('created_at', '')
                date = created.split('T')[0]
                formatted_date = datetime.fromisoformat(date).strftime('%b %d, %Y')
                news_list.append({
                    'title': item.get('title', 'No title'),
                    'url': item.get('url', ''),
                    'date': formatted_date
                })
            return news_list
    except requests.RequestException as e:
        st.error(f"Error fetching news: {e}")
        return []


def get_crypto_price_data(crypto_ids):
    try:
        results = {}
        for crypto in crypto_ids:
            # Get Binance data
            binance_symbol = CRYPTO_MAP[crypto]['binance']
            binance_resp = requests.get(f"{BINANCE_API}/ticker/24hr", params={'symbol': binance_symbol})
            binance_data = binance_resp.json()

            # Get CoinGecko data
            gecko_id = CRYPTO_MAP[crypto]['coingecko']
            gecko_resp = requests.get(f"{COINGECKO_API}/coins/{gecko_id}")
            gecko_data = gecko_resp.json()

            results[crypto] = {
                'price': float(binance_data['lastPrice']),
                'market_cap': float(gecko_data['market_data']['market_cap']['usd']),
                'rank': int(gecko_data.get('market_cap_rank', 0)),
                'change_24h': float(gecko_data['market_data']['price_change_percentage_24h']),
                'volume_24h': float(gecko_data['market_data']['total_volume']['usd'])
            }
        return results
    except Exception as e:
        st.error(f"Error fetching market data: {e}")
        return {}


def extract_crypto_info(query):
    query = query.lower()
    mentioned = []

    for crypto, data in CRYPTO_MAP.items():
        name = crypto.lower()
        symbols = [s.lower() for s in data['symbols']]
        gecko_name = data['coingecko'].lower()

        if name in query or gecko_name in query or any(sym in query for sym in symbols):
            mentioned.append(crypto)

    return list(set(mentioned)), (
        'news' if 'news' in query else
        'metrics' if any(term in query for term in ['price', 'market', 'data', 'volume', 'cap']) else
        'general'
    )

# -----------------------------------------
# Chat Interface
# -----------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

if prompt := st.chat_input("Ask about crypto (e.g. 'ETH news' or 'BTC price')"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    cryptos, qtype = extract_crypto_info(prompt)
    answer = ""

    if qtype == 'news':
        if not cryptos:
            answer = "Please specify a cryptocurrency for news updates."
        else:
            news = get_crypto_news(cryptos[0])
            if news:
                answer = f"**Latest {cryptos[0].title()} News:**\n\n"
                for item in news:
                    answer += f"• [{item['title']}]({item['url']}) ({item['date']})\n\n"
            else:
                answer = f"No recent news found for {cryptos[0].title()}"

    elif qtype == 'metrics':
        if not cryptos:
            answer = "Please specify a cryptocurrency for market data."
        else:
            data = get_crypto_price_data(cryptos)
            if data:
                answer = "**Current Market Data:**\n\n"
                for crypto in cryptos:
                    stats = data.get(crypto)
                    if stats:
                        answer += (
                            f"**{crypto.title()} ({CRYPTO_MAP[crypto]['symbols'][0].upper()})**\n"
                            f"• Price: ${stats['price']:,.2f}\n"
                            f"• Market Cap: ${stats['market_cap']:,.0f}\n"
                            f"• Market Cap Rank: #{stats['rank']}\n"
                            f"• 24h Change: {stats['change_24h']:.1f}%\n"
                            f"• 24h Volume: ${stats['volume_24h']:,.0f}\n\n"
                        )
            else:
                answer = "Could not retrieve market data at this time."

    else:
        response = ollama.chat(
            model="llama2",
            messages=[
                {"role": "system", "content": "You are a cryptocurrency expert..."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response['message']['content']

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer, unsafe_allow_html=True)
