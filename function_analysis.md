# Smart Contract Function Analysis

## Mint Function
从代码中可以看到，mint函数的调用：
```javascript
let e = (0, w.p)({
    abi: b,
    functionName: "mint",
    args: []
})
```

## 相关的检查函数

### 1. gtdList 函数
```javascript
{
    inputs: [{
        internalType: "address",
        name: "",
        type: "address"
    }],
    name: "gtdList",
    outputs: [{
        internalType: "bool",
        name: "",
        type: "bool"
    }],
    stateMutability: "view",
    type: "function"
}
```

### 2. fcfsList 函数
```javascript
{
    inputs: [{
        internalType: "address",
        name: "",
        type: "address"
    }],
    name: "fcfsList",
    outputs: [{
        internalType: "bool",
        name: "",
        type: "bool"
    }],
    stateMutability: "view",
    type: "function"
}
```

### 3. mint 函数
```javascript
{
    inputs: [],
    name: "mint",
    outputs: [],
    stateMutability: "payable",
    type: "function"
}
```

## Function Selectors (函数选择器)

函数选择器是函数签名的Keccak-256哈希的前4个字节。

- **mint()**: `0x1249c58b`
- **gtdList(address)**: 需要计算
- **fcfsList(address)**: 需要计算
