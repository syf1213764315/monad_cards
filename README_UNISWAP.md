# Uniswap V3 交易服务 - Monad测试网

## 概述
这是一个为Monad测试网设计的Uniswap V3交易服务，支持通过REST API进行代币交换。

## 主要改进

### 1. 合约地址配置
- 自动检测并配置Monad网络上的Uniswap合约地址
- 支持多个Router地址的自动发现
- 使用正确的SwapRouter02而不是UniversalRouter

### 2. 原生代币处理
- 特殊处理Monad网络的原生MON代币
- 支持原生代币占位符地址
- 自动处理WETH/原生代币转换

### 3. 错误处理改进
- 详细的交易失败原因分析
- 完整的交易日志记录
- 交易回执的深度解析

### 4. 交易参数优化
- 支持multicall批量操作
- 自动处理代币授权
- 智能Gas估算和回退机制

## 安装

```bash
# 安装依赖
pip3 install --break-system-packages flask flask-cors web3 eth-account python-dotenv

# 启动服务
python3 uniswap_service.py
```

## API端点

### 1. 执行交易
**POST** `/api/swap/execute`

请求体：
```json
{
    "private_key": "0x...",
    "token_address": "0x...",
    "amount_in": 0.009,
    "trade_type": "buy",  // "buy" 或 "sell"
    "slippage": 5
}
```

### 2. 获取代币信息
**POST** `/api/token/info`

请求体：
```json
{
    "token_address": "0x..."
}
```

### 3. 获取代币余额
**POST** `/api/token/balance`

请求体：
```json
{
    "token_address": "0x...",
    "wallet_address": "0x..."
}
```

## 测试

使用提供的测试脚本：
```bash
python3 test_swap.py
```

## 注意事项

1. **Monad网络特性**：
   - Monad使用原生MON代币，可能没有标准的WETH合约
   - 某些Uniswap功能可能需要特殊处理

2. **交易失败处理**：
   - 如果交易失败，检查日志中的详细错误信息
   - 常见问题：Gas不足、滑点过低、流动性不足

3. **安全性**：
   - 不要在生产环境中硬编码私钥
   - 使用环境变量或安全的密钥管理系统

## 故障排除

### 问题1：Gas估算失败
**解决方案**：服务会自动使用默认Gas值（500000）

### 问题2：交易执行失败但已确认
**可能原因**：
- Router地址不正确
- 代币对没有流动性池
- 滑点设置过低

### 问题3：原生代币交易失败
**解决方案**：
- 服务会尝试多种方法处理原生代币
- 如果都失败，可能需要先将MON包装为WMON

## 配置说明

服务启动时会自动：
1. 检测可用的Router合约
2. 检测可用的Factory合约
3. 配置正确的WETH/原生代币处理方式

当前配置（Monad测试网）：
- Chain ID: 10143
- RPC URL: https://testnet-rpc.monad.xyz
- Router: 自动检测（默认：0x3ae6d8a282d67893e17aa70ebffb33ee5aa65893）
- Factory: 自动检测（默认：0x961235a9020b05c44df1026d956d1f4d78014276）

## 联系支持

如遇到问题，请检查：
1. 服务日志输出
2. 交易哈希和区块浏览器
3. Monad网络状态