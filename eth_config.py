import os

####################################################
# Basic settings
####################################################

# Master account address for Ethereum transactions
ETH_MASTER_ACCOUNT_ADDRESS = os.environ.get("ETH_MASTER_ACCOUNT_ADDRESS")
# Hex encoded private key of the master account
ETH_MASTER_PRIVATE_KEY = os.environ.get("ETH_MASTER_PRIVATE_KEY")

# Ethereum configuration settings for a blockchain application
ETH_CHAIN_ID = int(os.environ.get("ETH_CHAIN_ID")) or 2025
ETH_WEB3_HTTP_PROVIDER = (
    os.environ.get("ETH_WEB3_HTTP_PROVIDER") or "http://localhost:8546"
)
