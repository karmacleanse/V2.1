"""
On-chain USDC payment verification for Polygon network.
Verifies that a tx hash represents a valid USDC transfer to our recipient address.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from typing import Optional

# Ensure env vars are loaded before reading
load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

POLYGON_RPC_URL = os.environ.get('POLYGON_RPC_URL', 'https://polygon-rpc.com')
USDC_CONTRACT_ADDRESS = os.environ.get('USDC_CONTRACT_ADDRESS', '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359')
CRYPTO_RECIPIENT_ADDRESS = os.environ.get('CRYPTO_RECIPIENT_ADDRESS')
POLYGON_CHAIN_ID = int(os.environ.get('POLYGON_CHAIN_ID', '137'))

# Standard ERC-20 Transfer event signature
TRANSFER_EVENT_SIGNATURE = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

# USDC has 6 decimals
USDC_DECIMALS = 6

# Pricing tiers in USDC (matching Stripe tiers)
CRYPTO_PRICING = {
    'standard': 1.0,
    'premium': 3.0,
    'enterprise': 7.0,
}


def get_web3() -> Web3:
    """Get Web3 instance connected to Polygon"""
    return Web3(Web3.HTTPProvider(POLYGON_RPC_URL))


def verify_usdc_payment(tx_hash: str, expected_tier: str) -> dict:
    """
    Verify that a tx hash represents a valid USDC transfer to our recipient.
    
    Returns:
        {
            'valid': bool,
            'amount_usdc': float,
            'sender': str (optional),
            'error': str (optional)
        }
    """
    if not CRYPTO_RECIPIENT_ADDRESS:
        return {'valid': False, 'error': 'Recipient address not configured'}
    
    if expected_tier not in CRYPTO_PRICING:
        return {'valid': False, 'error': 'Invalid tier'}
    
    expected_amount = CRYPTO_PRICING[expected_tier]
    expected_amount_raw = int(expected_amount * (10 ** USDC_DECIMALS))
    
    try:
        w3 = get_web3()
        
        if not w3.is_connected():
            return {'valid': False, 'error': 'RPC connection failed'}
        
        # Get transaction receipt
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        
        if not receipt:
            return {'valid': False, 'error': 'Transaction not found'}
        
        if receipt.status != 1:
            return {'valid': False, 'error': 'Transaction failed on-chain'}
        
        # Check that tx is to USDC contract
        tx = w3.eth.get_transaction(tx_hash)
        if tx['to'].lower() != USDC_CONTRACT_ADDRESS.lower():
            return {'valid': False, 'error': 'Transaction is not to USDC contract'}
        
        # Parse logs to find Transfer event
        recipient_lower = CRYPTO_RECIPIENT_ADDRESS.lower()
        
        for log in receipt.logs:
            # Verify log is from USDC contract
            if log['address'].lower() != USDC_CONTRACT_ADDRESS.lower():
                continue
            
            # Verify Transfer event signature
            if len(log['topics']) < 3:
                continue
            
            if log['topics'][0].hex() != TRANSFER_EVENT_SIGNATURE.replace('0x', ''):
                # Try with 0x prefix
                if log['topics'][0].hex() != TRANSFER_EVENT_SIGNATURE:
                    continue
            
            # topics[1] = from address (padded)
            # topics[2] = to address (padded)
            to_address = '0x' + log['topics'][2].hex()[-40:]
            from_address = '0x' + log['topics'][1].hex()[-40:]
            
            if to_address.lower() != recipient_lower:
                continue
            
            # Parse amount from data
            amount_raw = int(log['data'].hex(), 16)
            amount_usdc = amount_raw / (10 ** USDC_DECIMALS)
            
            # Allow small tolerance (network fees, slippage)
            if amount_raw < expected_amount_raw:
                return {
                    'valid': False,
                    'error': f'Insufficient amount: expected {expected_amount} USDC, got {amount_usdc} USDC',
                    'amount_usdc': amount_usdc,
                }
            
            return {
                'valid': True,
                'amount_usdc': amount_usdc,
                'sender': from_address,
                'tx_hash': tx_hash,
            }
        
        return {'valid': False, 'error': 'No matching USDC transfer found in transaction'}
        
    except Exception as e:
        logger.error(f"Crypto verification error: {str(e)}")
        return {'valid': False, 'error': f'Verification failed: {str(e)}'}


def find_recent_usdc_payment(expected_tier: str, since_block: int = None) -> dict:
    """
    Search recent USDC Transfer events to the recipient for the expected amount.
    Used for QR-code (no tx_hash) payment detection.
    
    Returns the most recent matching tx_hash, or None.
    """
    if not CRYPTO_RECIPIENT_ADDRESS:
        return {'found': False}
    
    if expected_tier not in CRYPTO_PRICING:
        return {'found': False, 'error': 'Invalid tier'}
    
    expected_amount = CRYPTO_PRICING[expected_tier]
    expected_amount_raw = int(expected_amount * (10 ** USDC_DECIMALS))
    
    try:
        w3 = get_web3()
        
        latest_block = w3.eth.block_number
        if since_block is None:
            # Default: last ~5 minutes (Polygon ~2s/block = 150 blocks)
            since_block = max(0, latest_block - 200)
        
        # Cap range to avoid timeout (max 500 blocks per query)
        from_block = max(since_block, latest_block - 500)
        
        # Build filter for Transfer events to our address
        recipient_padded = '0x' + CRYPTO_RECIPIENT_ADDRESS.lower().replace('0x', '').rjust(64, '0')
        
        logs = w3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': latest_block,
            'address': USDC_CONTRACT_ADDRESS,
            'topics': [
                TRANSFER_EVENT_SIGNATURE,
                None,  # from (any)
                recipient_padded,  # to (us)
            ]
        })
        
        # Iterate from newest to oldest
        for log in reversed(logs):
            amount_raw = int(log['data'].hex(), 16) if hasattr(log['data'], 'hex') else int(log['data'], 16)
            
            # Match amount (allow exact or slightly more)
            if amount_raw >= expected_amount_raw and amount_raw < expected_amount_raw * 2:
                tx_hash = log['transactionHash'].hex()
                if not tx_hash.startswith('0x'):
                    tx_hash = '0x' + tx_hash
                from_address = '0x' + log['topics'][1].hex().replace('0x', '')[-40:]
                
                return {
                    'found': True,
                    'tx_hash': tx_hash,
                    'amount_usdc': amount_raw / (10 ** USDC_DECIMALS),
                    'sender': from_address,
                    'block_number': log['blockNumber'],
                }
        
        return {'found': False, 'latest_block': latest_block}
        
    except Exception as e:
        logger.error(f"Find recent USDC error: {e}")
        return {'found': False, 'error': str(e)}
