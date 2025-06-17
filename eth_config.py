import os

####################################################
# Basic settings
####################################################
ETH_MASTER_PRIVATE_KEY = os.environ.get("ETH_MASTER_PRIVATE_KEY")

ETH_CHAIN_ID = os.environ.get("ETH_CHAIN_ID") or 2025
ETH_TX_GAS_LIMIT = os.environ.get("ETH_TX_GAS_LIMIT") or 5000000

ETH_WEB3_HTTP_PROVIDER = (
    os.environ.get("ETH_WEB3_HTTP_PROVIDER") or "http://localhost:8546"
)
