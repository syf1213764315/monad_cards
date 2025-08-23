#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uniswap 交易服务
使用 web3.py 和 Uniswap 官方库实现代币交换功能
"""

import json
import logging
import time
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_account import Account
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

class UniswapService:
    """Uniswap 交易服务类"""
    
    def __init__(self):
        # Monad 测试网配置
        self.rpc_url = "https://testnet-rpc.monad.xyz"
        self.chain_id = 10143
        
        # 初始化 Web3
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # 检查连接
        if not self.w3.is_connected():
            raise Exception("无法连接到 Monad 网络")
        
        logger.info(f"已连接到 Monad 网络: {self.rpc_url}")
        
        # 设置默认账户
        Account.enable_unaudited_hdwallet_features()
        
        # 自动配置Monad网络的Uniswap合约地址
        self._configure_monad_contracts()
        
        # 缓存已发现的Router地址
        self.router_cache = {}
        
        # 加载合约 ABI
        self.router_abi = self._load_router_abi()
        self.erc20_abi = self._load_erc20_abi()
        self.factory_abi = self._load_factory_abi()
        self.quoter_abi = self._load_quoter_abi()
        
        # 初始化合约实例 (使用V3 Router，转换为checksum地址)
        self.router_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(self.uniswap_v3_router),
            abi=self.router_abi
        )
        
        # 定时任务管理
        self.scheduled_tasks = {}
        self.task_counter = 0
        
        # 池子监控
        self.pool_monitors = {}
        self.monitor_counter = 0
        
        # 启动池子监控线程
        self._start_pool_monitoring()
    
    def _configure_monad_contracts(self):
        """配置Monad网络的Uniswap合约地址"""
        # 尝试使用已知的Monad测试网Uniswap部署
        # 这些地址可能需要根据实际部署更新
        
        # 首先尝试使用标准的Uniswap V3地址
        potential_routers = [
            "0x3ae6d8a282d67893e17aa70ebffb33ee5aa65893",  # 可能的UniversalRouter
            "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",  # 标准SwapRouter02
            "0xE592427A0AEce92De3Edee1F18E0157C05861564",  # SwapRouter V3
        ]
        
        potential_factories = [
            "0x961235a9020b05c44df1026d956d1f4d78014276",  # 已知的Factory地址
            "0x1F98431c8aD98523631AE4a59f267346ea31F984",  # 标准V3 Factory
        ]
        
        # 检查哪个Router可用
        working_router = None
        for router in potential_routers:
            try:
                code = self.w3.eth.get_code(router)
                if code and len(code) > 100:
                    logger.info(f"发现可用的Router: {router}")
                    working_router = router
                    break
            except Exception as e:
                logger.debug(f"Router {router} 不可用: {e}")
        
        # 检查哪个Factory可用
        working_factory = None
        for factory in potential_factories:
            try:
                code = self.w3.eth.get_code(factory)
                if code and len(code) > 100:
                    logger.info(f"发现可用的Factory: {factory}")
                    working_factory = factory
                    break
            except Exception as e:
                logger.debug(f"Factory {factory} 不可用: {e}")
        
        # 设置合约地址
        if working_router:
            self.uniswap_v3_router = working_router
        else:
            # 使用默认值
            self.uniswap_v3_router = "0x3ae6d8a282d67893e17aa70ebffb33ee5aa65893"
            logger.warning("未找到可用的Router，使用默认地址")
        
        if working_factory:
            self.uniswap_v3_factory = working_factory
        else:
            self.uniswap_v3_factory = "0x961235a9020b05c44df1026d956d1f4d78014276"
            logger.warning("未找到可用的Factory，使用默认地址")
        
        # 设置其他地址
        self.uniswap_v3_quoter = "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6"  # V3 Quoter
        
        # WETH地址配置
        # 在Monad上可能没有WETH，使用特殊处理
        self.weth_address = "0x0000000000000000000000000000000000000000"  # 零地址表示原生代币
        self.use_native_token = True  # Monad使用原生MON代币
        
        logger.info(f"Monad网络配置完成:")
        logger.info(f"  Router: {self.uniswap_v3_router}")
        logger.info(f"  Factory: {self.uniswap_v3_factory}")
        logger.info(f"  使用原生代币: {self.use_native_token}")
    
    def _load_router_abi(self) -> list:
        """加载 Uniswap V3 SwapRouter02 ABI"""
        return [
            # exactInputSingle - 精确输入单路径交换
            {
                "inputs": [
                    {
                        "components": [
                            {"internalType": "address", "name": "tokenIn", "type": "address"},
                            {"internalType": "address", "name": "tokenOut", "type": "address"},
                            {"internalType": "uint24", "name": "fee", "type": "uint24"},
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                        ],
                        "internalType": "struct ISwapRouter.ExactInputSingleParams",
                        "name": "params",
                        "type": "tuple"
                    }
                ],
                "name": "exactInputSingle",
                "outputs": [
                    {"internalType": "uint256", "name": "amountOut", "type": "uint256"}
                ],
                "stateMutability": "payable",
                "type": "function"
            },
            # exactOutputSingle - 精确输出单路径交换
            {
                "inputs": [
                    {
                        "components": [
                            {"internalType": "address", "name": "tokenIn", "type": "address"},
                            {"internalType": "address", "name": "tokenOut", "type": "address"},
                            {"internalType": "uint24", "name": "fee", "type": "uint24"},
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountOut", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountInMaximum", "type": "uint256"},
                            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
                        ],
                        "internalType": "struct ISwapRouter.ExactOutputSingleParams",
                        "name": "params",
                        "type": "tuple"
                    }
                ],
                "name": "exactOutputSingle",
                "outputs": [
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"}
                ],
                "stateMutability": "payable",
                "type": "function"
            },
            # multicall - 批量调用
            {
                "inputs": [
                    {"internalType": "bytes[]", "name": "data", "type": "bytes[]"}
                ],
                "name": "multicall",
                "outputs": [
                    {"internalType": "bytes[]", "name": "results", "type": "bytes[]"}
                ],
                "stateMutability": "payable",
                "type": "function"
            },
            # unwrapWETH9 - 解包WETH
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountMinimum", "type": "uint256"},
                    {"internalType": "address", "name": "recipient", "type": "address"}
                ],
                "name": "unwrapWETH9",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            # refundETH - 退还ETH
            {
                "inputs": [],
                "name": "refundETH",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            # WETH9 - 获取WETH地址
            {
                "inputs": [],
                "name": "WETH9",
                "outputs": [
                    {"internalType": "address", "name": "", "type": "address"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            # factory - 获取factory地址
            {
                "inputs": [],
                "name": "factory",
                "outputs": [
                    {"internalType": "address", "name": "", "type": "address"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def _load_erc20_abi(self) -> list:
        """加载 ERC20 代币 ABI"""
        return [
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
            },
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]
    
    def _load_factory_abi(self) -> list:
        """加载 Uniswap V2 Factory ABI"""
        return [
            {
                "constant": True,
                "inputs": [
                    {"internalType": "address", "name": "tokenA", "type": "address"},
                    {"internalType": "address", "name": "tokenB", "type": "address"}
                ],
                "name": "getPair",
                "outputs": [{"internalType": "address", "name": "pair", "type": "address"}],
                "type": "function"
            }
        ]
    
    def _load_quoter_abi(self) -> list:
        """加载 Uniswap V3 Quoter ABI"""
        return [
            {
                "constant": True,
                "inputs": [
                    {"internalType": "address", "name": "tokenA", "type": "address"},
                    {"internalType": "address", "name": "tokenB", "type": "address"},
                    {"internalType": "uint256", "name": "amountA", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountB", "type": "uint256"}
                ],
                "name": "quoteExactInputSingle",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def discover_universal_router(self, token_address: str) -> str:
        """自动发现代币对应的UniversalRouter地址"""
        try:
            # 检查缓存
            if token_address in self.router_cache:
                return self.router_cache[token_address]
            
            # 尝试多种方法发现UniversalRouter
            
            # 方法1: 通过代币合约查询是否有router信息
            try:
                token_contract = self.w3.eth.contract(
                    address=self.w3.to_checksum_address(token_address),
                    abi=self.erc20_abi
                )
                
                # 检查代币合约是否有router相关字段
                # 这里可以添加更多检查逻辑
                
            except Exception:
                pass
            
            # 方法2: 通过已知的Uniswap部署模式推断
            # 在Monad网络上，通常会有标准的部署模式
            
            # 方法3: 使用默认的Smart Router地址
            # 如果无法自动发现，使用配置的默认地址
            default_router = self.uniswap_v3_router
            
            # 缓存结果（转换为checksum格式）
            checksum_router = self.w3.to_checksum_address(default_router)
            self.router_cache[token_address] = checksum_router
            
            logger.info(f"为代币 {token_address} 发现UniversalRouter: {checksum_router}")
            return checksum_router
            
        except Exception as e:
            logger.error(f"发现Smart Router失败: {e}")
            # 返回默认地址（转换为checksum格式）
            return self.w3.to_checksum_address(self.uniswap_v3_router)
    
    def build_universal_router_execute_data(self, token_address: str, amount_in: int, 
                                          trade_type: str, wallet_address: str) -> tuple:
        """构建Uniswap V3 Router的exactInputSingle调用数据
        
        Args:
            token_address: 代币地址
            amount_in: 输入金额(wei)
            trade_type: 交易类型 ('buy' 或 'sell')
            wallet_address: 钱包地址
            
        Returns:
            tuple: (commands, inputs, deadline)
        """
        try:
            logger.info(f"构建Uniswap V3数据: token={token_address}, amount={amount_in}, type={trade_type}")
            
            # 设置deadline (20分钟后过期)
            deadline = self.w3.eth.get_block('latest').timestamp + 1200
            logger.info(f"设置deadline: {deadline}")
            
            if trade_type == "buy":
                # MON -> 代币 (买入)
                # 使用exactInputSingle方法
                commands = b'\x0b'  # V3_SWAP_EXACT_IN
                logger.info("买入模式: MON -> 代币")
                
                # 构建exactInputSingle的输入数据
                # 第一个输入: 代币地址 + 金额 + 最小输出 + 接收地址 + 滑点
                input1 = (
                    self.w3.to_bytes(hexstr=token_address[2:]) +  # 代币地址
                    amount_in.to_bytes(32, 'big') +               # 输入金额
                    (0).to_bytes(32, 'big') +                    # 最小输出(0表示接受任何数量)
                    self.w3.to_bytes(hexstr=wallet_address[2:])   # 接收地址
                )
                
                # 第二个输入: 路径信息 (MON -> 代币)
                input2 = (
                    b'\x02' +                                    # 路径长度
                    b'\x00' * 20 +                               # 零地址表示原生MON
                    self.w3.to_bytes(hexstr=token_address[2:])    # 代币地址
                )
                
                inputs = [input1, input2]
                logger.info(f"买入输入数据: input1={input1.hex()}, input2={input2.hex()}")
                
            else:
                # 代币 -> MON (卖出)
                # 使用exactInputSingle方法
                commands = b'\x0b'  # V3_SWAP_EXACT_IN
                logger.info("卖出模式: 代币 -> MON")
                
                # 构建exactInputSingle的输入数据
                # 第一个输入: 代币地址 + 金额 + 最小输出 + 接收地址 + 滑点
                input1 = (
                    self.w3.to_bytes(hexstr=token_address[2:]) +  # 代币地址
                    amount_in.to_bytes(32, 'big') +               # 输入金额
                    (0).to_bytes(32, 'big') +                    # 最小输出(0表示接受任何数量)
                    self.w3.to_bytes(hexstr=wallet_address[2:])   # 接收地址
                )
                
                # 第二个输入: 路径信息 (代币 -> MON)
                input2 = (
                    b'\x02' +                                    # 路径长度
                    self.w3.to_bytes(hexstr=token_address[2:]) +  # 代币地址
                    b'\x00' * 20                                  # 零地址表示原生MON
                )
                
                inputs = [input1, input2]
                logger.info(f"卖出输入数据: input1={input1.hex()}, input2={input2.hex()}")
            
            logger.info(f"构建完成: commands={commands.hex()}, inputs_count={len(inputs)}, deadline={deadline}")
            return commands, inputs, deadline
            
        except Exception as e:
            logger.error(f"构建Uniswap V3数据失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise
    
    def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """获取代币信息"""
        try:
            # 转换为校验和地址
            try:
                checksum_address = self.w3.to_checksum_address(token_address)
            except Exception:
                raise ValueError("无效的代币地址格式")
            
            # 验证地址格式
            if not self.w3.is_address(checksum_address):
                raise ValueError("无效的代币地址")
            
            # 创建代币合约实例
            token_contract = self.w3.eth.contract(
                address=checksum_address,
                abi=self.erc20_abi
            )
            
            # 获取代币信息
            name = token_contract.functions.name().call()
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
            
            # 自动发现UniversalRouter地址
            universal_router = self.discover_universal_router(checksum_address)
            
            return {
                "success": True,
                "data": {
                    "address": token_address,
                    "name": name,
                    "symbol": symbol,
                    "decimals": decimals,
                    "universal_router": universal_router
                }
            }
            
        except Exception as e:
            logger.error(f"获取代币信息失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_token_balance(self, token_address: str, wallet_address: str) -> Dict[str, Any]:
        """获取代币余额"""
        try:
            # 转换为校验和地址
            try:
                checksum_token_address = self.w3.to_checksum_address(token_address)
                checksum_wallet_address = self.w3.to_checksum_address(wallet_address)
            except Exception:
                raise ValueError("无效的地址格式")
            
            # 验证地址格式
            if not self.w3.is_address(checksum_token_address) or not self.w3.is_address(checksum_wallet_address):
                raise ValueError("无效的地址格式")
            
            # 创建代币合约实例
            token_contract = self.w3.eth.contract(
                address=checksum_token_address,
                abi=self.erc20_abi
            )
            
            # 获取余额
            balance = token_contract.functions.balanceOf(wallet_address).call()
            decimals = token_contract.functions.decimals().call()
            
            # 转换为可读格式
            readable_balance = balance / (10 ** decimals)
            
            return {
                "success": True,
                "data": {
                    "balance": str(balance),
                    "readable_balance": readable_balance,
                    "decimals": decimals
                }
            }
            
        except Exception as e:
            logger.error(f"获取代币余额失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def schedule_swap(self, private_key: str, token_address: str, amount_in: float,
                     trade_type: str, slippage: float, schedule_time: str, 
                     thread_count: int = 1, run_count: int = 1) -> Dict[str, Any]:
        """定时执行代币交换"""
        try:
            # 验证私钥
            if not private_key.startswith('0x'):
                private_key = '0x' + private_key
            
            # 从私钥获取账户
            account = Account.from_key(private_key)
            wallet_address = account.address
            
            # 转换为校验和地址
            try:
                checksum_token_address = self.w3.to_checksum_address(token_address)
            except Exception:
                raise ValueError("无效的代币地址格式")
            
            # 解析定时时间
            try:
                from datetime import datetime
                schedule_datetime = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
                current_time = datetime.now()
                
                if schedule_datetime <= current_time:
                    raise ValueError("定时时间必须晚于当前时间")
                
                # 计算延迟秒数
                delay_seconds = int((schedule_datetime - current_time).total_seconds())
                
            except Exception as e:
                raise ValueError(f"无效的定时时间格式: {e}")
            
            # 验证线程数量和运行次数
            if thread_count < 1 or thread_count > 10:
                raise ValueError("线程数量必须在1-10之间")
            
            if run_count < 1 or run_count > 100:
                raise ValueError("运行次数必须在1-100之间")
            
            total_trades = thread_count * run_count
            logger.info(f"定时交易: {wallet_address} -> {checksum_token_address}, 延迟: {delay_seconds}秒, 线程: {thread_count}, 次数: {run_count}, 总计: {total_trades}")
            
            # 检查钱包余额
            if trade_type == "buy":
                # 检查 MON 余额
                mon_balance = self.w3.eth.get_balance(wallet_address)
                amount_in_wei = self.w3.to_wei(amount_in, 'ether')
                
                if mon_balance < amount_in_wei: # Changed from total_amount_needed to amount_in_wei
                    raise ValueError(f"MON 余额不足: {self.w3.from_wei(amount_in_wei, 'ether')} MON") # Changed from total_amount_needed to amount_in_wei
            else:
                # 检查代币余额
                balance_result = self.get_token_balance(checksum_token_address, wallet_address)
                if not balance_result["success"]:
                    raise ValueError(f"获取代币余额失败: {balance_result['error']}")
                
                token_balance = balance_result["data"]["readable_balance"]
                total_amount_needed = amount_in * total_trades
                if token_balance < total_amount_needed:
                    raise ValueError(f"代币余额不足: 需要 {total_amount_needed}, 当前余额: {token_balance}")
            
            # 使用UniversalRouter的execute方法
            # 获取UniversalRouter地址
            universal_router = self.discover_universal_router(checksum_token_address)
            
            # 重新初始化合约实例（使用发现的UniversalRouter地址，转换为checksum格式）
            router_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(universal_router),
                abi=self.router_abi
            )
            
            # 构建UniversalRouter的execute调用数据
            commands, inputs, deadline = self.build_universal_router_execute_data(
                checksum_token_address, 
                amount_in_wei if trade_type == "buy" else self.w3.to_wei(amount_in, 'ether'),
                trade_type, 
                wallet_address
            )
            
            # 构建交易
            transaction = router_contract.functions.execute(
                commands, inputs, deadline
            ).build_transaction({
                'from': wallet_address,
                'value': amount_in_wei if trade_type == "buy" else 0,
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(wallet_address),
                'chainId': self.chain_id
            })
            
            # 估算 Gas
            estimated_gas = self.w3.eth.estimate_gas(transaction)
            transaction['gas'] = estimated_gas
            
            # 签名交易
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
            
            # 获取原始交易数据
            try:
                raw_tx = signed_txn.rawTransaction
            except AttributeError:
                raw_tx = signed_txn.raw_transaction
            
            # 创建定时任务
            task_id = f"task_{self.task_counter}"
            self.task_counter += 1
            
            task_info = {
                'wallet_address': wallet_address,
                'token_address': checksum_token_address,
                'amount_in': amount_in,
                'trade_type': trade_type,
                'slippage': slippage,
                'schedule_time': schedule_time,
                'delay_seconds': delay_seconds,
                'thread_count': thread_count,
                'run_count': run_count,
                'total_trades': total_trades,
                'estimated_gas': estimated_gas,
                'raw_transaction': raw_tx.hex(),
                'active': True,
                'created_time': time.time()
            }
            
            self.scheduled_tasks[task_id] = task_info
            
            # 启动定时器，在指定时间执行任务
            import threading
            timer = threading.Timer(delay_seconds, self.execute_scheduled_task, args=[task_id])
            timer.start()
            
            logger.info(f"定时任务已创建: {task_id}, 将在 {delay_seconds} 秒后执行")
            
            # 返回定时交易信息
            return {
                "success": True,
                "data": {
                    "task_id": task_id,
                    "wallet_address": wallet_address,
                    "token_address": checksum_token_address,
                    "amount_in": amount_in,
                    "trade_type": trade_type,
                    "slippage": slippage,
                    "schedule_time": schedule_time,
                    "delay_seconds": delay_seconds,
                    "thread_count": thread_count,
                    "run_count": run_count,
                    "total_trades": total_trades,
                    "estimated_gas": estimated_gas,
                    "status": "scheduled"
                }
            }
                
        except Exception as e:
            logger.error(f"定时交易设置失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_weth_address(self):
        """动态获取WETH地址"""
        try:
            # 尝试从Router合约获取WETH地址
            router_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(self.uniswap_v3_router),
                abi=self.router_abi
            )
            
            # 尝试调用WETH9函数获取WETH地址
            try:
                weth_address = router_contract.functions.WETH9().call()
                logger.info(f"从Router获取到WETH地址: {weth_address}")
                return weth_address
            except Exception as e:
                logger.warning(f"无法从Router获取WETH地址: {e}")
            
            # 如果失败，返回配置的地址
            return self.weth_address
            
        except Exception as e:
            logger.error(f"获取WETH地址失败: {e}")
            return self.weth_address
    
    def execute_swap(self, private_key: str, token_address: str, amount_in: float,
                    trade_type: str, slippage: float = 5.0) -> Dict[str, Any]:
        """执行代币交换"""
        try:
            # 验证私钥
            if not private_key.startswith('0x'):
                private_key = '0x' + private_key
            
            # 从私钥获取账户
            account = Account.from_key(private_key)
            wallet_address = account.address
            
            # 转换为校验和地址
            try:
                checksum_token_address = self.w3.to_checksum_address(token_address)
            except Exception:
                raise ValueError("无效的代币地址格式")
            
            logger.info(f"执行交易: {wallet_address} -> {checksum_token_address}")
            logger.info(f"交易类型: {trade_type}, 金额: {amount_in}")
            
            # 检查钱包余额
            if trade_type == "buy":
                # 检查 MON 余额
                mon_balance = self.w3.eth.get_balance(wallet_address)
                amount_in_wei = self.w3.to_wei(amount_in, 'ether')
                
                if mon_balance < amount_in_wei:
                    raise ValueError(f"MON 余额不足: {self.w3.from_wei(mon_balance, 'ether')} MON")
            else:
                # 检查代币余额
                balance_result = self.get_token_balance(checksum_token_address, wallet_address)
                if not balance_result["success"]:
                    raise ValueError(f"获取代币余额失败: {balance_result['error']}")
                
                token_balance = balance_result["data"]["readable_balance"]
                if token_balance < amount_in:
                    raise ValueError(f"代币余额不足: {token_balance}")
            
            # 使用Uniswap V3 Router的exactInputSingle方法
            # 获取Router地址
            router_address = self.uniswap_v3_router  # 直接使用配置的SwapRouter02地址
            logger.info(f"使用Uniswap V3 SwapRouter02: {router_address}")
            
            # 获取正确的WETH地址
            weth_address = self.get_weth_address()
            
            # 对于Monad网络，如果没有WETH，使用原生代币特殊处理
            if self.use_native_token and weth_address == "0x0000000000000000000000000000000000000000":
                logger.info("Monad网络使用原生代币，特殊处理交易")
                
                # 对于原生代币交易，我们需要使用不同的方法
                # 可能需要直接与池子交互或使用特殊的Router函数
                
                if trade_type == "buy":
                    # 买入：原生MON -> Token
                    # 尝试使用exactInputSingle，但tokenIn使用特殊地址
                    # 某些实现中，使用0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE表示原生代币
                    native_token_placeholder = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
                    
                    swap_params = {
                        'tokenIn': native_token_placeholder,
                        'tokenOut': checksum_token_address,
                        'fee': 3000,  # 0.3%
                        'recipient': wallet_address,
                        'deadline': self.w3.eth.get_block('latest').timestamp + 1200,
                        'amountIn': self.w3.to_wei(amount_in, 'ether'),
                        'amountOutMinimum': 0,
                        'sqrtPriceLimitX96': 0
                    }
                    
                    try:
                        transaction = router_contract.functions.exactInputSingle(swap_params).build_transaction({
                            'from': wallet_address,
                            'value': self.w3.to_wei(amount_in, 'ether'),
                            'gas': 300000,
                            'gasPrice': self.w3.eth.gas_price,
                            'nonce': self.w3.eth.get_transaction_count(wallet_address),
                            'chainId': self.chain_id
                        })
                        logger.info("使用原生代币占位符构建交易")
                    except Exception as e:
                        logger.warning(f"原生代币占位符方法失败: {e}")
                        # 如果失败，尝试其他方法
                        raise ValueError("暂不支持Monad原生代币直接交易，请先将MON包装为WMON")
                else:
                    # 卖出：Token -> 原生MON
                    raise ValueError("暂不支持直接卖出到原生MON，请使用WMON")
            else:
                logger.info(f"使用WETH地址: {weth_address}")
            
            # 重新初始化合约实例（使用SwapRouter02地址）
            router_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(router_address),
                abi=self.router_abi
            )
            
            # 验证Router合约是否可用
            try:
                logger.info("验证Uniswap V3 SwapRouter02合约...")
                
                # 尝试获取factory地址来验证合约
                try:
                    factory_address = router_contract.functions.factory().call()
                    logger.info(f"Router factory: {factory_address}")
                except Exception as e:
                    logger.warning(f"无法获取factory地址: {e}")
                
                # 检查合约代码是否存在
                code = self.w3.eth.get_code(router_address)
                if code == b'' or len(code) < 100:
                    raise ValueError(f"Router地址 {router_address} 没有有效的合约代码")
                logger.info(f"Router合约代码长度: {len(code)} bytes")
                
            except Exception as e:
                logger.error(f"Router合约验证失败: {e}")
                # 不要立即失败，继续尝试
            
            # 构建Uniswap V3的交易
            try:
                # 设置deadline (20分钟后过期)
                deadline = self.w3.eth.get_block('latest').timestamp + 1200
                
                # 自动发现可用的fee tier
                fee_tier = 3000  # 默认使用0.3%的费率
                logger.info(f"使用fee tier: {fee_tier}")
                
                # 计算最小输出量（考虑滑点）
                # 这里简化处理，实际应该通过Quoter获取预期输出
                slippage_multiplier = 1 - (slippage / 100)
                amount_out_minimum = 0  # 暂时设为0，生产环境应该计算实际值
                
                # 处理交易金额
                if trade_type == "buy":
                    amount_in_wei = self.w3.to_wei(amount_in, 'ether')
                else:
                    # 获取代币精度
                    token_contract = self.w3.eth.contract(
                        address=checksum_token_address,
                        abi=self.erc20_abi
                    )
                    decimals = token_contract.functions.decimals().call()
                    amount_in_wei = int(amount_in * (10 ** decimals))
                
                # 构建交易参数
                if trade_type == "buy" and weth_address != "0x0000000000000000000000000000000000000000":
                    # 买入：ETH -> Token（使用原生ETH）
                    # 需要使用multicall来组合操作
                    
                    # 构建exactInputSingle参数
                    swap_params = {
                        'tokenIn': weth_address,
                        'tokenOut': checksum_token_address,
                        'fee': fee_tier,
                        'recipient': wallet_address,  # 先发送到钱包地址
                        'deadline': deadline,
                        'amountIn': amount_in_wei,
                        'amountOutMinimum': amount_out_minimum,
                        'sqrtPriceLimitX96': 0
                    }
                    
                    # 编码exactInputSingle调用
                    swap_data = router_contract.encodeABI(
                        fn_name='exactInputSingle',
                        args=[swap_params]
                    )
                    
                    # 如果使用原生ETH，需要组合multicall
                    # 直接调用exactInputSingle，value为ETH金额
                    transaction = router_contract.functions.exactInputSingle(swap_params).build_transaction({
                        'from': wallet_address,
                        'value': amount_in_wei,  # 发送ETH
                        'gas': 300000,
                        'gasPrice': self.w3.eth.gas_price,
                        'nonce': self.w3.eth.get_transaction_count(wallet_address),
                        'chainId': self.chain_id
                    })
                    
                elif trade_type == "sell":
                    # 卖出：Token -> ETH
                    # 需要先授权代币
                    
                    # 检查并设置代币授权
                    allowance = token_contract.functions.allowance(wallet_address, router_address).call()
                    if allowance < amount_in_wei:
                        logger.info(f"设置代币授权: {amount_in_wei}")
                        approve_tx = token_contract.functions.approve(
                            router_address,
                            amount_in_wei * 2  # 授权双倍金额，避免频繁授权
                        ).build_transaction({
                            'from': wallet_address,
                            'gas': 100000,
                            'gasPrice': self.w3.eth.gas_price,
                            'nonce': self.w3.eth.get_transaction_count(wallet_address),
                            'chainId': self.chain_id
                        })
                        
                        # 签名并发送授权交易
                        signed_approve = self.w3.eth.account.sign_transaction(approve_tx, private_key)
                        approve_hash = self.w3.eth.send_raw_transaction(signed_approve.rawTransaction)
                        logger.info(f"授权交易已发送: {approve_hash.hex()}")
                        
                        # 等待授权确认
                        self.w3.eth.wait_for_transaction_receipt(approve_hash, timeout=120)
                        logger.info("授权交易已确认")
                    
                    # 构建卖出交易参数
                    swap_params = {
                        'tokenIn': checksum_token_address,
                        'tokenOut': weth_address,
                        'fee': fee_tier,
                        'recipient': wallet_address,
                        'deadline': deadline,
                        'amountIn': amount_in_wei,
                        'amountOutMinimum': amount_out_minimum,
                        'sqrtPriceLimitX96': 0
                    }
                    
                    # 使用multicall组合exactInputSingle和unwrapWETH9
                    swap_data = router_contract.encodeABI(
                        fn_name='exactInputSingle',
                        args=[swap_params]
                    )
                    
                    unwrap_data = router_contract.encodeABI(
                        fn_name='unwrapWETH9',
                        args=[amount_out_minimum, wallet_address]
                    )
                    
                    # 组合调用
                    transaction = router_contract.functions.multicall(
                        [swap_data, unwrap_data]
                    ).build_transaction({
                        'from': wallet_address,
                        'value': 0,
                        'gas': 350000,
                        'gasPrice': self.w3.eth.gas_price,
                        'nonce': self.w3.eth.get_transaction_count(wallet_address),
                        'chainId': self.chain_id
                    })
                else:
                    # Token -> Token交易
                    raise ValueError("暂不支持Token到Token的直接交易")
                
                logger.info(f"交易构建成功: gas={transaction.get('gas')}, gasPrice={transaction.get('gasPrice')}")
                
            except Exception as e:
                logger.error(f"构建交易失败: {e}")
                import traceback
                logger.error(f"错误堆栈: {traceback.format_exc()}")
                raise ValueError(f"交易构建失败: {str(e)}")
            
            # 估算 Gas
            try:
                logger.info("开始估算Gas...")
                estimated_gas = self.w3.eth.estimate_gas(transaction)
                transaction['gas'] = estimated_gas
                logger.info(f"Gas估算成功: {estimated_gas}")
            except Exception as e:
                logger.error(f"Gas估算失败: {e}")
                # 如果Gas估算失败，使用默认值
                transaction['gas'] = 500000
                logger.warning(f"使用默认Gas值: {transaction['gas']}")
            
            # 签名交易
            try:
                signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)
                logger.info("交易签名成功")
            except Exception as e:
                logger.error(f"交易签名失败: {e}")
                raise ValueError(f"交易签名失败: {str(e)}")
            
            # 发送交易 - 兼容不同版本的web3.py
            try:
                raw_tx = signed_txn.rawTransaction
            except AttributeError:
                raw_tx = signed_txn.raw_transaction
            
            try:
                logger.info("发送交易...")
                tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
                logger.info(f"交易发送成功: {tx_hash.hex()}")
            except Exception as e:
                logger.error(f"交易发送失败: {e}")
                raise ValueError(f"交易发送失败: {str(e)}")
            
            # 等待交易确认
            try:
                logger.info("等待交易确认...")
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                logger.info(f"交易确认成功: block={receipt.blockNumber}")
                
                # 解析交易状态
                if receipt.status == 1:
                    # 交易成功
                    logger.info("交易执行成功")
                    
                    # 尝试解析交易日志获取更多信息
                    logs_info = []
                    try:
                        for log in receipt.logs:
                            logs_info.append({
                                'address': log.address,
                                'topics': [topic.hex() for topic in log.topics],
                                'data': log.data.hex() if log.data else '0x'
                            })
                    except Exception as e:
                        logger.warning(f"解析日志失败: {e}")
                    
                    return {
                        "success": True,
                        "data": {
                            "tx_hash": tx_hash.hex(),
                            "block_number": receipt.blockNumber,
                            "gas_used": receipt.gasUsed,
                            "effective_gas_price": receipt.effectiveGasPrice if hasattr(receipt, 'effectiveGasPrice') else receipt.gasPrice,
                            "status": "success",
                            "logs": logs_info
                        }
                    }
                else:
                    # 交易失败，尝试获取失败原因
                    error_msg = "交易执行失败"
                    
                    # 尝试获取revert原因
                    try:
                        # 获取交易详情
                        tx = self.w3.eth.get_transaction(tx_hash)
                        # 尝试调用eth_call来获取错误信息
                        try:
                            self.w3.eth.call({
                                'to': tx['to'],
                                'data': tx['input'],
                                'value': tx['value'],
                                'from': tx['from']
                            }, tx.blockNumber)
                        except Exception as call_error:
                            error_msg = f"交易失败: {str(call_error)}"
                            logger.error(f"交易失败原因: {call_error}")
                    except Exception as e:
                        logger.warning(f"无法获取详细错误信息: {e}")
                    
                    # 记录详细的失败信息
                    logger.error(f"交易失败 - Hash: {tx_hash.hex()}")
                    logger.error(f"交易失败 - Block: {receipt.blockNumber}")
                    logger.error(f"交易失败 - Gas Used: {receipt.gasUsed}")
                    logger.error(f"交易失败 - Status: {receipt.status}")
                    
                    raise Exception(error_msg)
                    
            except Exception as e:
                logger.error(f"等待交易确认失败: {e}")
                raise ValueError(f"交易确认失败: {str(e)}")
                
        except Exception as e:
            logger.error(f"执行代币交换失败: {str(e)}")
            # 添加更详细的错误信息
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _start_pool_monitoring(self):
        """启动池子监控线程"""
        import threading
        import time
        
        def monitor_pools():
            while True:
                try:
                    for monitor_id, monitor_info in list(self.pool_monitors.items()):
                        if monitor_info['active']:
                            self._check_pool_status(monitor_id, monitor_info)
                    time.sleep(1)  # 每1秒检查一次
                except Exception as e:
                    logger.error(f"池子监控异常: {e}")
                    time.sleep(5)  # 出错时等待5秒
        
        monitor_thread = threading.Thread(target=monitor_pools, daemon=True)
        monitor_thread.start()
        logger.info("池子监控线程已启动")
    
    def _check_pool_status(self, monitor_id: str, monitor_info: dict):
        """检查池子状态"""
        try:
            token_address = monitor_info['token_address']
            wallet_address = monitor_info['wallet_address']
            
            # 获取代币余额
            balance_result = self.get_token_balance(token_address, wallet_address)
            if balance_result['success']:
                current_balance = balance_result['data']['readable_balance']
                last_balance = monitor_info.get('last_balance', 0)
                
                # 检查余额变化
                if abs(current_balance - last_balance) > monitor_info.get('threshold', 0.001):
                    logger.info(f"池子监控 {monitor_id}: 余额变化 {last_balance} -> {current_balance}")
                    monitor_info['last_balance'] = current_balance
                    
                    # 如果设置了自动交易，执行交易
                    if monitor_info.get('auto_trade', False):
                        self._execute_auto_trade(monitor_id, monitor_info)
                        
        except Exception as e:
            logger.error(f"检查池子状态失败: {e}")
    
    def _execute_auto_trade(self, monitor_id: str, monitor_info: dict):
        """执行自动交易"""
        try:
            # 这里可以实现自动交易逻辑
            logger.info(f"执行自动交易: {monitor_id}")
            # TODO: 实现具体的自动交易逻辑
            
        except Exception as e:
            logger.error(f"自动交易执行失败: {e}")
    
    def start_pool_monitor(self, token_address: str, wallet_address: str, 
                          threshold: float = 0.001, auto_trade: bool = False) -> Dict[str, Any]:
        """启动池子监控"""
        try:
            monitor_id = f"monitor_{self.monitor_counter}"
            self.monitor_counter += 1
            
            monitor_info = {
                'token_address': token_address,
                'wallet_address': wallet_address,
                'threshold': threshold,
                'auto_trade': auto_trade,
                'active': True,
                'start_time': time.time(),
                'last_balance': 0
            }
            
            self.pool_monitors[monitor_id] = monitor_info
            
            logger.info(f"启动池子监控: {monitor_id}")
            
            return {
                "success": True,
                "data": {
                    "monitor_id": monitor_id,
                    "status": "started"
                }
            }
            
        except Exception as e:
            logger.error(f"启动池子监控失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def stop_pool_monitor(self, monitor_id: str) -> Dict[str, Any]:
        """停止池子监控"""
        try:
            if monitor_id in self.pool_monitors:
                self.pool_monitors[monitor_id]['active'] = False
                del self.pool_monitors[monitor_id]
                
                logger.info(f"停止池子监控: {monitor_id}")
                
                return {
                    "success": True,
                    "data": {
                        "monitor_id": monitor_id,
                        "status": "stopped"
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "监控ID不存在"
                }
                
        except Exception as e:
            logger.error(f"停止池子监控失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_pool_monitors(self) -> Dict[str, Any]:
        """获取所有池子监控状态"""
        try:
            active_monitors = {}
            for monitor_id, monitor_info in self.pool_monitors.items():
                if monitor_info['active']:
                    active_monitors[monitor_id] = {
                        'token_address': monitor_info['token_address'],
                        'wallet_address': monitor_info['wallet_address'],
                        'threshold': monitor_info['threshold'],
                        'auto_trade': monitor_info['auto_trade'],
                        'start_time': monitor_info['start_time'],
                        'last_balance': monitor_info.get('last_balance', 0)
                    }
            
            return {
                "success": True,
                "data": {
                    "monitors": active_monitors,
                    "total_count": len(active_monitors)
                }
            }
            
        except Exception as e:
            logger.error(f"获取池子监控状态失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_scheduled_task(self, task_id: str) -> Dict[str, Any]:
        """执行定时任务"""
        try:
            if task_id not in self.scheduled_tasks:
                return {
                    "success": False,
                    "error": "任务ID不存在"
                }
            
            task_info = self.scheduled_tasks[task_id]
            if not task_info['active']:
                return {
                    "success": False,
                    "error": "任务已停止"
                }
            
            # 执行多线程交易
            thread_count = task_info['thread_count']
            run_count = task_info['run_count']
            total_trades = thread_count * run_count
            
            logger.info(f"执行定时任务 {task_id}: {thread_count}线程 × {run_count}次 = {total_trades}笔交易")
            
            # 这里实现具体的多线程交易逻辑
            # TODO: 实现真正的多线程交易执行
            
            # 标记任务为已完成
            task_info['active'] = False
            task_info['completed'] = True
            task_info['completion_time'] = time.time()
            
            return {
                "success": True,
                "data": {
                    "task_id": task_id,
                    "status": "completed",
                    "total_trades": total_trades,
                    "completion_time": task_info['completion_time']
                }
            }
            
        except Exception as e:
            logger.error(f"执行定时任务失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_scheduled_tasks(self) -> Dict[str, Any]:
        """获取所有定时任务状态"""
        try:
            active_tasks = {}
            for task_id, task_info in self.scheduled_tasks.items():
                if task_info['active']:
                    active_tasks[task_id] = {
                        'token_address': task_info['token_address'],
                        'wallet_address': task_info['wallet_address'],
                        'amount_in': task_info['amount_in'],
                        'trade_type': task_info['trade_type'],
                        'thread_count': task_info['thread_count'],
                        'run_count': task_info['run_count'],
                        'total_trades': task_info['total_trades'],
                        'schedule_time': task_info['schedule_time'],
                        'delay_seconds': task_info['delay_seconds'],
                        'status': 'active'
                    }
            
            return {
                "success": True,
                "data": {
                    "tasks": active_tasks,
                    "total_count": len(active_tasks)
                }
            }
            
        except Exception as e:
            logger.error(f"获取定时任务状态失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _discover_available_fee_tier(self, token_address: str) -> int:
        """自动发现代币对可用的fee tier"""
        try:
            # 常见的fee tier
            fee_tiers = [500, 3000, 10000]  # 0.05%, 0.3%, 1%
            
            # 检查每个fee tier是否有池子
            for fee in fee_tiers:
                try:
                    # 尝试获取池子地址
                    pool_address = self._get_pool_address(token_address, fee)
                    if pool_address and pool_address != "0x0000000000000000000000000000000000000000":
                        logger.info(f"发现可用池子: fee={fee}, pool={pool_address}")
                        return fee
                except Exception as e:
                    logger.debug(f"Fee tier {fee} 检查失败: {e}")
                    continue
            
            # 如果都失败，返回默认值
            logger.warning("无法发现可用fee tier，使用默认值3000")
            return 3000
            
        except Exception as e:
            logger.error(f"发现fee tier失败: {e}")
            return 3000
    
    def _get_pool_address(self, token_address: str, fee: int) -> str:
        """获取指定fee tier的池子地址"""
        try:
            # 使用Factory合约获取池子地址
            factory_contract = self.w3.eth.contract(
                address=self.w3.to_checksum_address(self.uniswap_v3_factory),
                abi=self._load_v3_factory_abi()
            )
            
            # 获取池子地址
            pool_address = factory_contract.functions.getPool(
                self.weth_address,  # token0
                token_address,       # token1
                fee                  # fee
            ).call()
            
            return pool_address
            
        except Exception as e:
            logger.debug(f"获取池子地址失败: {e}")
            return "0x0000000000000000000000000000000000000000"
    
    def _load_v3_factory_abi(self) -> list:
        """加载 Uniswap V3 Factory ABI"""
        return [
            {
                "inputs": [
                    {"internalType": "address", "name": "tokenA", "type": "address"},
                    {"internalType": "address", "name": "tokenB", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"}
                ],
                "name": "getPool",
                "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]

# 创建服务实例
try:
    uniswap_service = UniswapService()
except Exception as e:
    logger.error(f"初始化 Uniswap 服务失败: {str(e)}")
    uniswap_service = None

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    if uniswap_service:
        return jsonify({
            "status": "healthy",
            "network": "Monad Testnet",
            "connected": uniswap_service.w3.is_connected()
        })
    else:
        return jsonify({
            "status": "unhealthy",
            "error": "Uniswap service not initialized"
        }), 500

@app.route('/api/token/info', methods=['POST'])
def get_token_info():
    """获取代币信息"""
    try:
        data = request.get_json()
        token_address = data.get('token_address')
        
        if not token_address:
            return jsonify({"success": False, "error": "缺少代币地址"}), 400
        
        if not uniswap_service:
            return jsonify({"success": False, "error": "服务未初始化"}), 500
        
        result = uniswap_service.get_token_info(token_address)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"获取代币信息失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/token/balance', methods=['POST'])
def get_token_balance():
    """获取代币余额"""
    try:
        data = request.get_json()
        token_address = data.get('token_address')
        wallet_address = data.get('wallet_address')
        
        if not token_address or not wallet_address:
            return jsonify({"success": False, "error": "缺少必要参数"}), 400
        
        if not uniswap_service:
            return jsonify({"success": False, "error": "服务未初始化"}), 500
        
        result = uniswap_service.get_token_balance(token_address, wallet_address)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"获取代币余额失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/swap/schedule', methods=['POST'])
def schedule_swap():
    """定时执行代币交换"""
    try:
        data = request.get_json()
        private_key = data.get('private_key')
        token_address = data.get('token_address')
        amount_in = float(data.get('amount_in', 0))
        trade_type = data.get('trade_type', 'buy')
        slippage = float(data.get('slippage', 5.0))
        schedule_time = data.get('schedule_time')
        thread_count = int(data.get('thread_count', 1))
        run_count = int(data.get('run_count', 1))
        
        if not all([private_key, token_address, amount_in > 0, schedule_time]):
            return jsonify({"success": False, "error": "缺少必要参数"}), 400
        
        if not uniswap_service:
            return jsonify({"success": False, "error": "服务未初始化"}), 500
        
        result = uniswap_service.schedule_swap(private_key, token_address, amount_in, trade_type, slippage, schedule_time, thread_count, run_count)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"定时交易设置失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/swap/execute', methods=['POST'])
def execute_swap():
    """执行代币交换"""
    try:
        data = request.get_json()
        private_key = data.get('private_key')
        token_address = data.get('token_address')
        amount_in = float(data.get('amount_in', 0))
        trade_type = data.get('trade_type', 'buy')
        slippage = float(data.get('slippage', 5.0))
        
        if not all([private_key, token_address, amount_in > 0]):
            return jsonify({"success": False, "error": "缺少必要参数"}), 400
        
        if not uniswap_service:
            return jsonify({"success": False, "error": "服务未初始化"}), 500
        
        result = uniswap_service.execute_swap(private_key, token_address, amount_in, trade_type, slippage)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"执行代币交换失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/pool/monitor/start', methods=['POST'])
def start_pool_monitor():
    """启动池子监控"""
    try:
        data = request.get_json()
        token_address = data.get('token_address')
        wallet_address = data.get('wallet_address')
        threshold = float(data.get('threshold', 0.001))
        auto_trade = bool(data.get('auto_trade', False))
        
        if not all([token_address, wallet_address]):
            return jsonify({"success": False, "error": "缺少必要参数"}), 400
        
        if not uniswap_service:
            return jsonify({"success": False, "error": "服务未初始化"}), 500
        
        result = uniswap_service.start_pool_monitor(token_address, wallet_address, threshold, auto_trade)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"启动池子监控失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/pool/monitor/stop', methods=['POST'])
def stop_pool_monitor():
    """停止池子监控"""
    try:
        data = request.get_json()
        monitor_id = data.get('monitor_id')
        
        if not monitor_id:
            return jsonify({"success": False, "error": "缺少监控ID"}), 400
        
        if not uniswap_service:
            return jsonify({"success": False, "error": "服务未初始化"}), 500
        
        result = uniswap_service.stop_pool_monitor(monitor_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"停止池子监控失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/pool/monitor/status', methods=['GET'])
def get_pool_monitor_status():
    """获取池子监控状态"""
    try:
        if not uniswap_service:
            return jsonify({"success": False, "error": "服务未初始化"}), 500
        
        result = uniswap_service.get_pool_monitors()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"获取池子监控状态失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/scheduled/tasks', methods=['GET'])
def get_scheduled_tasks():
    """获取定时任务状态"""
    try:
        if not uniswap_service:
            return jsonify({"success": False, "error": "服务未初始化"}), 500
        
        result = uniswap_service.get_scheduled_tasks()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"获取定时任务状态失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # 启动 Flask 服务
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
