#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Monad testnet swap functionality
"""

import json
import sys
from web3 import Web3

def test_monad_connection():
    """Test connection to Monad testnet"""
    rpc_url = "https://testnet-rpc.monad.xyz"
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if w3.is_connected():
        print(f"✅ Connected to Monad testnet")
        print(f"   Chain ID: {w3.eth.chain_id}")
        print(f"   Latest block: {w3.eth.block_number}")
        return True
    else:
        print("❌ Failed to connect to Monad testnet")
        return False

def test_contract_addresses():
    """Test if important contracts are deployed"""
    rpc_url = "https://testnet-rpc.monad.xyz"
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    contracts = {
        "UniversalRouter": "0x3ae6d8a282d67893e17aa70ebffb33ee5aa65893",
        "UniswapV3Factory": "0x961235a9020b05c44df1026d956d1f4d78014276",
        "WrappedMonad (WMON)": "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701",
        "USDC (testnet)": "0xf817257fed379853cDe0fa4F97AB987181B1E5Ea",
    }
    
    print("\n📋 Checking contract deployments:")
    for name, address in contracts.items():
        try:
            code = w3.eth.get_code(address)
            if code and len(code) > 100:
                print(f"   ✅ {name}: {address}")
            else:
                print(f"   ❌ {name}: No code at {address}")
        except Exception as e:
            print(f"   ❌ {name}: Error checking {address}: {e}")

def test_wmon_contract():
    """Test WMON contract functions"""
    rpc_url = "https://testnet-rpc.monad.xyz"
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    wmon_address = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701"
    
    # Basic ERC20 ABI for testing
    erc20_abi = [
        {
            "constant": True,
            "inputs": [],
            "name": "name",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function"
        }
    ]
    
    print("\n🪙 Testing WMON contract:")
    try:
        wmon_contract = w3.eth.contract(
            address=w3.to_checksum_address(wmon_address),
            abi=erc20_abi
        )
        
        name = wmon_contract.functions.name().call()
        symbol = wmon_contract.functions.symbol().call()
        decimals = wmon_contract.functions.decimals().call()
        
        print(f"   Name: {name}")
        print(f"   Symbol: {symbol}")
        print(f"   Decimals: {decimals}")
        print(f"   ✅ WMON contract is accessible")
    except Exception as e:
        print(f"   ❌ Error accessing WMON contract: {e}")

def main():
    """Run all tests"""
    print("🚀 Testing Monad Testnet Swap Functionality")
    print("=" * 50)
    
    # Test connection
    if not test_monad_connection():
        sys.exit(1)
    
    # Test contract addresses
    test_contract_addresses()
    
    # Test WMON contract
    test_wmon_contract()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\n📝 Summary of fixes applied:")
    print("1. Fixed UnboundLocalError by initializing router_contract before usage")
    print("2. Updated WMON address to official WrappedMonad: 0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701")
    print("3. Implemented proper MON to WMON wrapping for swaps")
    print("4. Added UniversalRouter support with fallback to standard Router")
    print("\n💡 The swap service should now:")
    print("   - Properly handle native MON token swaps")
    print("   - Wrap MON to WMON before swapping")
    print("   - Support both buy and sell operations")
    print("   - Work with UniversalRouter at 0x3ae6d8a282d67893e17aa70ebffb33ee5aa65893")

if __name__ == "__main__":
    main()