#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Uniswap交易服务
"""

import requests
import json
import sys

def test_swap():
    """测试交易功能"""
    # API端点
    url = "http://localhost:5001/api/swap/execute"
    
    # 测试数据（使用用户提供的数据）
    payload = {
        "private_key": "0x96419aae7748b95182bb982ac084e1cd6e725e6e6f9d4a45fda00a50ce7b76f9",
        "token_address": "0x0F0BDEbF0F83cD1EE3974779Bcb7315f9808c714",
        "amount_in": 0.009,
        "trade_type": "buy",
        "slippage": 5
    }
    
    print("发送交易请求...")
    print(f"请求数据: {json.dumps(payload, indent=2)}")
    
    try:
        # 发送POST请求
        response = requests.post(url, json=payload)
        
        # 解析响应
        result = response.json()
        
        if result.get("success"):
            print("\n✅ 交易成功!")
            print(f"交易哈希: {result['data']['tx_hash']}")
            print(f"区块号: {result['data']['block_number']}")
            print(f"Gas使用: {result['data']['gas_used']}")
        else:
            print("\n❌ 交易失败!")
            print(f"错误信息: {result.get('error', '未知错误')}")
            
        return result
        
    except Exception as e:
        print(f"\n❌ 请求失败: {str(e)}")
        return None

def test_token_info():
    """测试获取代币信息"""
    url = "http://localhost:5001/api/token/info"
    
    payload = {
        "token_address": "0x0F0BDEbF0F83cD1EE3974779Bcb7315f9808c714"
    }
    
    print("\n获取代币信息...")
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        if result.get("success"):
            data = result['data']
            print(f"代币名称: {data.get('name', 'N/A')}")
            print(f"代币符号: {data.get('symbol', 'N/A')}")
            print(f"小数位数: {data.get('decimals', 'N/A')}")
        else:
            print(f"获取失败: {result.get('error', '未知错误')}")
            
        return result
        
    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None

if __name__ == "__main__":
    print("=" * 50)
    print("Uniswap交易服务测试")
    print("=" * 50)
    
    # 先测试获取代币信息
    token_info = test_token_info()
    
    # 然后测试交易
    print("\n" + "=" * 50)
    swap_result = test_swap()
    
    print("\n测试完成!")