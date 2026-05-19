import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ethers } from 'ethers';
import axios from 'axios';
import useRitualStore from '../store/ritualStore';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// USDC ERC-20 ABI (only the transfer function we need)
const USDC_ABI = [
  'function transfer(address to, uint256 amount) returns (bool)',
  'function balanceOf(address owner) view returns (uint256)',
  'function decimals() view returns (uint8)',
];

const POLYGON_CHAIN_ID_HEX = '0x89'; // 137 in hex

const POLYGON_NETWORK_PARAMS = {
  chainId: POLYGON_CHAIN_ID_HEX,
  chainName: 'Polygon Mainnet',
  nativeCurrency: { name: 'MATIC', symbol: 'MATIC', decimals: 18 },
  rpcUrls: ['https://polygon-rpc.com'],
  blockExplorerUrls: ['https://polygonscan.com'],
};

const CryptoPayment = ({ tier, tierKey, amount, onSuccess, onCancel }) => {
  const [stage, setStage] = useState('idle'); // idle, connecting, switching, confirming, verifying, success, error
  const [walletAddress, setWalletAddress] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [txHash, setTxHash] = useState(null);
  const [config, setConfig] = useState(null);
  const certificateUuid = useRitualStore((state) => state.certificateUuid);

  useEffect(() => {
    // Load crypto config from backend
    axios.get(`${API}/crypto/config`).then((res) => setConfig(res.data));
  }, []);

  const isMetaMaskInstalled = () => {
    return typeof window !== 'undefined' && typeof window.ethereum !== 'undefined';
  };

  const ensurePolygon = async (provider) => {
    const network = await provider.getNetwork();
    if (Number(network.chainId) !== 137) {
      setStage('switching');
      try {
        await window.ethereum.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: POLYGON_CHAIN_ID_HEX }],
        });
      } catch (switchError) {
        // Chain not added, try to add it
        if (switchError.code === 4902) {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [POLYGON_NETWORK_PARAMS],
          });
        } else {
          throw switchError;
        }
      }
    }
  };

  const handlePay = async () => {
    if (!isMetaMaskInstalled()) {
      setErrorMsg('MetaMask not detected. Please install MetaMask extension.');
      setStage('error');
      return;
    }

    if (!config) {
      setErrorMsg('Configuration not loaded. Please try again.');
      setStage('error');
      return;
    }

    try {
      setStage('connecting');
      setErrorMsg(null);

      // Request accounts
      const accounts = await window.ethereum.request({
        method: 'eth_requestAccounts',
      });
      const userAddress = accounts[0];
      setWalletAddress(userAddress);

      // Create provider
      const provider = new ethers.BrowserProvider(window.ethereum);

      // Ensure on Polygon
      await ensurePolygon(provider);

      // Re-create provider after network switch
      const freshProvider = new ethers.BrowserProvider(window.ethereum);
      const signer = await freshProvider.getSigner();

      // Create USDC contract instance
      const usdc = new ethers.Contract(config.usdc_contract, USDC_ABI, signer);

      // Check balance
      const balance = await usdc.balanceOf(userAddress);
      const requiredAmount = ethers.parseUnits(amount.toString(), config.decimals);

      if (balance < requiredAmount) {
        const balanceFormatted = ethers.formatUnits(balance, config.decimals);
        setErrorMsg(`Insufficient USDC balance. You have ${balanceFormatted} USDC, need ${amount} USDC.`);
        setStage('error');
        return;
      }

      // Prepare transaction
      setStage('confirming');

      // Send USDC transfer
      const tx = await usdc.transfer(config.recipient_address, requiredAmount);
      setTxHash(tx.hash);

      // Wait for confirmation
      setStage('verifying');
      const receipt = await tx.wait();

      if (receipt.status !== 1) {
        setErrorMsg('Transaction failed on-chain.');
        setStage('error');
        return;
      }

      // Verify with backend
      const verifyRes = await axios.post(`${API}/crypto/verify`, {
        tier: tierKey,
        certificate_uuid: certificateUuid,
        tx_hash: tx.hash,
        sender_address: userAddress,
      });

      if (verifyRes.data.verified) {
        setStage('success');
        setTimeout(() => {
          onSuccess();
        }, 2000);
      } else {
        setErrorMsg('Backend verification failed.');
        setStage('error');
      }
    } catch (err) {
      console.error('Crypto payment error:', err);
      if (err.code === 4001 || err.code === 'ACTION_REJECTED') {
        setErrorMsg('Transaction rejected in MetaMask.');
      } else if (err.response?.data?.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg(err.message || 'Transaction failed.');
      }
      setStage('error');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: 'rgba(10, 10, 10, 0.85)' }}
      data-testid="crypto-payment-modal"
    >
      <div
        className="max-w-md w-full p-8 border-2 relative"
        style={{ background: '#FFFFFF', borderColor: '#0A0A0A' }}
      >
        {/* Close button */}
        {stage !== 'confirming' && stage !== 'verifying' && stage !== 'success' && (
          <button
            onClick={onCancel}
            className="absolute top-4 right-4 text-2xl font-black hover:opacity-50"
            style={{ color: '#0A0A0A' }}
            data-testid="close-crypto-modal-btn"
          >
            ×
          </button>
        )}

        {/* Header */}
        <div className="mb-6">
          <div
            className="text-xs uppercase font-bold tracking-widest mb-2"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Crypto Payment Protocol
          </div>
          <h3
            className="text-2xl font-bold uppercase"
            style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
          >
            {tier}
          </h3>
          <div className="mt-4 flex items-baseline gap-2">
            <span
              className="text-4xl font-black"
              style={{ color: '#D92D20', fontFamily: 'Chivo, sans-serif' }}
            >
              {amount}
            </span>
            <span
              className="text-sm font-mono"
              style={{ color: '#525252' }}
            >
              USDC on Polygon
            </span>
          </div>
        </div>

        {/* Status content */}
        <AnimatePresence mode="wait">
          {stage === 'idle' && (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div
                className="border-2 p-4 mb-4"
                style={{ borderColor: '#E5E5DF', background: '#F4F4F0' }}
              >
                <div
                  className="text-xs uppercase font-bold tracking-widest mb-2"
                  style={{ color: '#737373' }}
                >
                  Transaction Details
                </div>
                <div className="space-y-1 text-xs font-mono" style={{ color: '#525252' }}>
                  <div>Network: <span style={{ color: '#0A0A0A' }}>Polygon Mainnet</span></div>
                  <div>Token: <span style={{ color: '#0A0A0A' }}>USDC</span></div>
                  <div>Amount: <span style={{ color: '#0A0A0A' }}>{amount} USDC</span></div>
                  <div className="break-all">
                    To: <span style={{ color: '#0A0A0A' }}>{config?.recipient_address}</span>
                  </div>
                </div>
              </div>

              <button
                onClick={handlePay}
                className="w-full py-3 font-bold uppercase text-sm border-2 transition-colors"
                style={{
                  background: '#0A0A0A',
                  color: '#F4F4F0',
                  borderColor: '#0A0A0A',
                  fontFamily: 'Chivo, sans-serif',
                }}
                data-testid="pay-with-metamask-btn"
              >
                Pay with MetaMask
              </button>

              <p
                className="text-xs text-center mt-4 font-mono"
                style={{ color: '#737373' }}
              >
                Direct wallet-to-wallet transfer. No intermediaries.
              </p>
            </motion.div>
          )}

          {stage === 'connecting' && (
            <StatusMessage
              title="Connecting Wallet"
              text="Approve connection in MetaMask..."
              showSpinner
            />
          )}

          {stage === 'switching' && (
            <StatusMessage
              title="Switching Network"
              text="Switch to Polygon network in MetaMask..."
              showSpinner
            />
          )}

          {stage === 'confirming' && (
            <StatusMessage
              title="Awaiting Confirmation"
              text="Confirm the transaction in MetaMask..."
              showSpinner
            />
          )}

          {stage === 'verifying' && (
            <StatusMessage
              title="Verifying On-Chain"
              text="Waiting for block confirmation (10-30 seconds)..."
              showSpinner
              txHash={txHash}
            />
          )}

          {stage === 'success' && (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center py-4"
            >
              <div
                className="inline-block px-6 py-3 border-2 transform -rotate-3 mb-4"
                style={{ borderColor: '#15803D', color: '#15803D' }}
              >
                <span
                  className="text-lg font-black uppercase tracking-widest"
                  style={{ fontFamily: 'Chivo, sans-serif' }}
                >
                  PAYMENT VERIFIED
                </span>
              </div>
              <p
                className="text-sm font-mono"
                style={{ color: '#525252' }}
              >
                Certificate upgraded to certified tier.
              </p>
              {txHash && (
                <a
                  href={`https://polygonscan.com/tx/${txHash}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-mono mt-2 inline-block underline"
                  style={{ color: '#525252' }}
                >
                  View on Polygonscan ↗
                </a>
              )}
            </motion.div>
          )}

          {stage === 'error' && (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="py-2"
            >
              <div
                className="border-2 p-4 mb-4"
                style={{ borderColor: '#D92D20', background: '#FFFFFF' }}
              >
                <div
                  className="text-xs uppercase font-bold tracking-widest mb-2"
                  style={{ color: '#D92D20' }}
                >
                  Error
                </div>
                <p className="text-sm font-mono" style={{ color: '#0A0A0A' }}>
                  {errorMsg}
                </p>
              </div>
              <button
                onClick={() => setStage('idle')}
                className="w-full py-3 font-bold uppercase text-sm border-2"
                style={{
                  background: 'transparent',
                  color: '#0A0A0A',
                  borderColor: '#0A0A0A',
                  fontFamily: 'Chivo, sans-serif',
                }}
                data-testid="retry-crypto-btn"
              >
                Retry
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

const StatusMessage = ({ title, text, showSpinner, txHash }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    className="text-center py-4"
  >
    {showSpinner && (
      <div
        className="w-12 h-12 border-2 rounded-full animate-spin mx-auto mb-4"
        style={{ borderColor: '#E5E5DF', borderTopColor: '#0A0A0A' }}
      />
    )}
    <div
      className="text-xs uppercase font-bold tracking-widest mb-2"
      style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
    >
      {title}
    </div>
    <p className="text-sm font-mono" style={{ color: '#0A0A0A' }}>
      {text}
    </p>
    {txHash && (
      <a
        href={`https://polygonscan.com/tx/${txHash}`}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs font-mono mt-3 inline-block underline break-all"
        style={{ color: '#525252' }}
      >
        {txHash.slice(0, 10)}...{txHash.slice(-8)} ↗
      </a>
    )}
  </motion.div>
);

export default CryptoPayment;
