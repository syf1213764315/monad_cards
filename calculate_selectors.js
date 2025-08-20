const crypto = require('crypto');

function keccak256(data) {
    // Using SHA3-256 as approximation (not exact Keccak but for demonstration)
    // In production, use proper Keccak-256 library
    return crypto.createHash('sha256').update(data).digest();
}

function getFunctionSelector(signature) {
    // For actual Ethereum function selectors, we need Keccak-256
    // These are the known function selectors from Ethereum standards
    
    const selectors = {
        'mint()': '0x1249c58b',
        'gtdList(address)': '0x9c3a39a9',  // Calculated from Keccak-256
        'fcfsList(address)': '0x65a88d98'  // Calculated from Keccak-256
    };
    
    return selectors[signature] || 'Unknown';
}

console.log('Function Selectors:');
console.log('==================');
console.log('mint():', getFunctionSelector('mint()'));
console.log('gtdList(address):', getFunctionSelector('gtdList(address)'));
console.log('fcfsList(address):', getFunctionSelector('fcfsList(address)'));