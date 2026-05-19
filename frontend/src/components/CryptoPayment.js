import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ethers } from 'ethers';
import QRCode from 'react-qr-code';
import axios from 'axios';
import useRitualStore from '../store/ritualStore';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const USDC_ABI = [
  'function transfer(address to, uint256 amount) returns (bool)',
  'function balanceOf(address owner) view returns (uint256)',
];

const POLYGON_CHAIN_ID_HEX = '0x89';

const POLYGON_NETWORK_PARAMS = {
  chainId: POLYGON_CHAIN_ID_HEX,
  chainName: 'Polygon Mainnet',
  nativeCurrency: { name: 'MATIC', symbol: 'MATIC', decimals: 18 },
  rpcUrls: ['https://polygon-rpc.com'],
  blockExplorerUrls: ['https://polygonscan.com'],
};

// Build EIP-681 URI for ERC-20 transfer on Polygon
const buildEip681Uri = (usdcContract, recipient, amountRaw) => {
  return `ethereum:${usdcContract}@137/transfer?address=${recipient}&uint256=${amountRaw}`;
};

const CryptoPayment = ({ tier, tierKey, amount, onSuccess, onCancel }) => {
  const [config, setConfig] = useState(null);
  const [mode, setMode] = useState('chooser'); // chooser | browser | mobile
  const [stage, setStage] = useState('idle');
  const [errorMsg, setErrorMsg] = useState(null);
  const [txHash, setTxHash] = useState(null);
  const [walletAddress, setWalletAddress] = useState(null);

  const certificateUuid = useRitualStore((state) => state.certificateUuid);

  useEffect(() => {
    axios.get(`${API}/crypto/config`).then((res) => setConfig(res.data));
  }, []);

  // Polling backend for QR-based payment detection
  const startPolling = useCallback(async () => {
    let attempts = 0;
    const maxAttempts = 60; // ~10 minutes (every 10s)
    const sinceTimestamp = Math.floor(Date.now() / 1000);

    const poll = async () => {
      if (attempts >= maxAttempts) {
        setErrorMsg('Payment not detected. If sent, refresh in 5 minutes.');
        setStage('error');
        return;
      }
      attempts++;

      try {
        const res = await axios.post(`${API}/crypto/poll`, {
          tier: tierKey,
          certificate_uuid: certificateUuid,
          since_timestamp: sinceTimestamp,
        });

        if (res.data.detected) {
          setTxHash(res.data.tx_hash);
          setStage('success');
          setTimeout(() => onSuccess(), 2500);
          return;
        }

        setTimeout(poll, 10000);
      } catch (err) {
        console.error('Polling error:', err);
        setTimeout(poll, 10000);
      }
    };

    poll();
  }, [tierKey, certificateUuid, onSuccess]);

  const handleBrowserPay = async () => {
    if (!window.ethereum) {
      setErrorMsg('No browser wallet detected. Use mobile QR instead, or install MetaMask.');
      setStage('error');
      return;
    }

    if (!config) {
      setErrorMsg('Configuration not loaded.');
      setStage('error');
      return;
    }

    try {
      setStage('connecting');
      setErrorMsg(null);

      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
      const userAddress = accounts[0];
      setWalletAddress(userAddress);

      // Ensure Polygon
      const provider = new ethers.BrowserProvider(window.ethereum);
      const network = await provider.getNetwork();

      if (Number(network.chainId) !== 137) {
        setStage('switching');
        try {
          await window.ethereum.request({
            method: 'wallet_switchEthereumChain',
            params: [{ chainId: POLYGON_CHAIN_ID_HEX }],
          });
        } catch (switchErr) {
          if (switchErr.code === 4902) {
            await window.ethereum.request({
              method: 'wallet_addEthereumChain',
              params: [POLYGON_NETWORK_PARAMS],
            });
          } else {
            throw switchErr;
          }
        }
      }

      const freshProvider = new ethers.BrowserProvider(window.ethereum);
      const signer = await freshProvider.getSigner();
      const usdc = new ethers.Contract(config.usdc_contract, USDC_ABI, signer);

      // Check balance
      const balance = await usdc.balanceOf(userAddress);
      const required = ethers.parseUnits(amount.toString(), config.decimals);

      if (balance < required) {
        const have = ethers.formatUnits(balance, config.decimals);
        setErrorMsg(`Insufficient USDC. You have ${have}, need ${amount}.`);
        setStage('error');
        return;
      }

      setStage('confirming');
      const tx = await usdc.transfer(config.recipient_address, required);
      setTxHash(tx.hash);

      setStage('verifying');
      const receipt = await tx.wait();

      if (receipt.status !== 1) {
        setErrorMsg('Transaction failed on-chain.');
        setStage('error');
        return;
      }

      const verifyRes = await axios.post(`${API}/crypto/verify`, {
        tier: tierKey,
        certificate_uuid: certificateUuid,
        tx_hash: tx.hash,
        sender_address: userAddress,
      });

      if (verifyRes.data.verified) {
        setStage('success');
        setTimeout(() => onSuccess(), 2500);
      } else {
        setErrorMsg('Backend verification failed.');
        setStage('error');
      }
    } catch (err) {
      console.error('Browser pay error:', err);
      if (err.code === 4001 || err.code === 'ACTION_REJECTED') {
        setErrorMsg('Transaction rejected.');
      } else {
        setErrorMsg(err.shortMessage || err.message || 'Transaction failed.');
      }
      setStage('error');
    }
  };

  const handleMobilePay = () => {
    setMode('mobile');
    setStage('waiting-qr');
    startPolling();
  };

  // Build URI for QR
  const eip681Uri = config
    ? buildEip681Uri(
        config.usdc_contract,
        config.recipient_address,
        ethers.parseUnits(amount.toString(), config.decimals).toString()
      )
    : '';

  const handleCopyAddress = () => {
    if (config?.recipient_address) {
      navigator.clipboard.writeText(config.recipient_address);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="fixed inset-0 z-50 flex items-center justify-center px-4 py-8 overflow-y-auto"
      style={{ background: 'rgba(10, 10, 10, 0.85)' }}
      data-testid="crypto-payment-modal"
    >
      <div
        className="max-w-md w-full p-8 border-2 relative my-auto"
        style={{ background: '#FFFFFF', borderColor: '#0A0A0A' }}
      >
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
            <span className="text-sm font-mono" style={{ color: '#525252' }}>
              USDC on Polygon
            </span>
          </div>
        </div>

        <AnimatePresence mode="wait">
          {/* CHOOSER */}
          {mode === 'chooser' && stage === 'idle' && (
            <motion.div
              key="chooser"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              <button
                onClick={() => { setMode('browser'); handleBrowserPay(); }}
                className="w-full py-4 font-bold uppercase text-sm border-2 transition-colors flex items-center justify-center gap-3"
                style={{
                  background: '#0A0A0A',
                  color: '#F4F4F0',
                  borderColor: '#0A0A0A',
                  fontFamily: 'Chivo, sans-serif',
                }}
                data-testid="browser-wallet-btn"
              >
                <span style={{ fontSize: '1.2em' }}>🦊</span>
                Browser Wallet
              </button>

              <button
                onClick={handleMobilePay}
                className="w-full py-4 font-bold uppercase text-sm border-2 transition-colors flex items-center justify-center gap-3"
                style={{
                  background: 'transparent',
                  color: '#0A0A0A',
                  borderColor: '#0A0A0A',
                  fontFamily: 'Chivo, sans-serif',
                }}
                data-testid="mobile-wallet-btn"
              >
                <span style={{ fontSize: '1.2em' }}>📱</span>
                Mobile Wallet (QR)
              </button>

              <p className="text-xs text-center mt-4 font-mono" style={{ color: '#737373' }}>
                Browser: MetaMask, Coinbase, Trust, Phantom extensions
                <br />
                Mobile: scan QR with any wallet app
              </p>
            </motion.div>
          )}

          {/* MOBILE QR */}
          {mode === 'mobile' && stage === 'waiting-qr' && config && (
            <motion.div
              key="qr"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center"
            >
              <div
                className="border-2 p-4 mb-4 inline-block"
                style={{ borderColor: '#0A0A0A', background: '#FFFFFF' }}
              >
                <QRCode value={eip681Uri} size={220} />
              </div>

              <div
                className="text-xs uppercase font-bold tracking-widest mb-2"
                style={{ color: '#737373' }}
              >
                Scan with mobile wallet
              </div>
              <p className="text-xs font-mono mb-4" style={{ color: '#525252' }}>
                Trust · Rainbow · Coinbase · MetaMask Mobile · Phantom · Argent
              </p>

              <div
                className="border-2 p-3 mb-3"
                style={{ borderColor: '#E5E5DF', background: '#F4F4F0' }}
              >
                <div
                  className="text-xs uppercase font-bold tracking-widest mb-2"
                  style={{ color: '#737373' }}
                >
                  Or send manually
                </div>
                <div className="text-xs font-mono space-y-1" style={{ color: '#0A0A0A' }}>
                  <div>Network: <span style={{ fontWeight: 'bold' }}>Polygon</span></div>
                  <div>Token: <span style={{ fontWeight: 'bold' }}>USDC</span></div>
                  <div>Amount: <span style={{ fontWeight: 'bold' }}>{amount} USDC</span></div>
                </div>
                <div className="mt-2">
                  <div className="text-xs uppercase font-bold tracking-widest mb-1" style={{ color: '#737373' }}>
                    To
                  </div>
                  <div
                    className="text-xs font-mono break-all cursor-pointer"
                    style={{ color: '#0A0A0A' }}
                    onClick={handleCopyAddress}
                    title="Click to copy"
                  >
                    {config.recipient_address}
                  </div>
                  <button
                    onClick={handleCopyAddress}
                    className="text-xs uppercase font-bold underline mt-1"
                    style={{ color: '#525252' }}
                  >
                    Copy address
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-center gap-2 mt-4">
                <div
                  className="w-3 h-3 rounded-full animate-pulse"
                  style={{ background: '#D92D20' }}
                />
                <p className="text-xs uppercase font-bold tracking-widest" style={{ color: '#525252' }}>
                  Watching blockchain...
                </p>
              </div>
              <p className="text-xs font-mono mt-2" style={{ color: '#737373' }}>
                Page auto-updates when payment is detected
              </p>
            </motion.div>
          )}

          {/* Browser stages */}
          {(stage === 'connecting' || stage === 'switching') && mode === 'browser' && (
            <StatusMessage
              title={stage === 'switching' ? 'Switching Network' : 'Connecting Wallet'}
              text={stage === 'switching' ? 'Switch to Polygon in your wallet...' : 'Approve in your wallet extension...'}
              showSpinner
            />
          )}

          {stage === 'confirming' && (
            <StatusMessage
              title="Awaiting Confirmation"
              text="Confirm the transaction in your wallet..."
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
              <p className="text-sm font-mono" style={{ color: '#525252' }}>
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
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-2">
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
                onClick={() => {
                  setStage('idle');
                  setMode('chooser');
                  setErrorMsg(null);
                  setTxHash(null);
                }}
                className="w-full py-3 font-bold uppercase text-sm border-2"
                style={{
                  background: 'transparent',
                  color: '#0A0A0A',
                  borderColor: '#0A0A0A',
                  fontFamily: 'Chivo, sans-serif',
                }}
                data-testid="retry-crypto-btn"
              >
                Back
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
