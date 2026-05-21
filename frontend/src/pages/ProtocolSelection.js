import { useState } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import useRitualStore from '../store/ritualStore';
import BackButton from '../components/BackButton';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Severity-based compensation tiers (NOT functionality tiers).
// All paid amounts produce the SAME Premium certificate — they differ only
// in self-assessed karmic damage level.
const SEVERITY_OPTIONS = [
  {
    id: 'enterprise',
    amount: 7,
    label: 'Severe Karmic Catastrophe',
    tagline: '$7 \u2014 yeah... this one was bad',
    examples: [
      'catastrophic interpersonal decisions',
      'weaponized chaos',
      'emotionally devastating behavior',
    ],
    accent: '#D92D20',
    weight: 'heavy',
  },
  {
    id: 'premium',
    amount: 3,
    label: 'Significant Moral Confusion',
    tagline: '$3 \u2014 regrettable but recoverable',
    examples: [
      'regrettable decisions',
      'emotional collateral damage',
      'questionable late-night behavior',
    ],
    accent: '#B45309',
    weight: 'medium',
  },
  {
    id: 'standard',
    amount: 1,
    label: 'Minor Incident',
    tagline: '$1 \u2014 a small slip',
    examples: [
      'drank too much beer',
      'awkward behavior',
      'mild dishonesty',
      'avoidable stupidity',
    ],
    accent: '#525252',
    weight: 'light',
  },
];

const ProtocolSelection = () => {
  const [loading, setLoading] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState(null); // 'card' | 'crypto'
  const [selectedSeverity, setSelectedSeverity] = useState(null);
  const [customAmount, setCustomAmount] = useState('');
  const [customMode, setCustomMode] = useState(false);
  const [error, setError] = useState(null);
  const certificateUuid = useRitualStore((state) => state.certificateUuid);
  const setStep = useRitualStore((state) => state.setStep);

  const handleSelectFree = () => {
    setStep('certificate');
  };

  const proceedWithPayment = async (severity, method, overrideAmount = null) => {
    setLoading(true);
    setError(null);
    try {
      const originUrl = window.location.origin;
      const amount = overrideAmount !== null ? overrideAmount : severity.amount;

      if (method === 'card') {
        // Polar only supports preset products. Custom amount must use crypto.
        if (overrideAmount !== null && !severity) {
          setError('Custom amounts are only available via crypto payment.');
          setLoading(false);
          return;
        }
        const response = await axios.post(`${API}/polar/checkout`, {
          tier: severity.id,
          certificate_uuid: certificateUuid,
          origin_url: originUrl,
        });
        if (response.data?.url) {
          window.location.href = response.data.url;
        } else {
          throw new Error('No checkout URL');
        }
      } else if (method === 'crypto') {
        const payload = {
          certificate_uuid: certificateUuid,
          origin_url: originUrl,
        };
        if (overrideAmount !== null) {
          payload.custom_amount = parseFloat(amount);
        } else {
          payload.tier = severity.id;
        }
        const response = await axios.post(`${API}/plisio/invoice`, payload);
        if (response.data?.url) {
          window.location.href = response.data.url;
        } else {
          throw new Error('No invoice URL');
        }
      }
    } catch (e) {
      console.error('Payment error:', e);
      setError(e.response?.data?.detail || 'Payment initialization failed. Please try again.');
      setLoading(false);
    }
  };

  const handleSeverityClick = (severity) => {
    setSelectedSeverity(severity);
    setCustomMode(false);
    setPaymentMethod(null);
  };

  const handleCustomClick = () => {
    setCustomMode(true);
    setSelectedSeverity(null);
    setPaymentMethod(null);
  };

  const handleConfirmPayment = (method) => {
    if (customMode) {
      const val = parseFloat(customAmount);
      if (isNaN(val) || val < 0.5 || val > 1000) {
        setError('Amount must be between $0.50 and $1000.');
        return;
      }
      if (method === 'card') {
        setError('Custom amounts are only available via crypto. Please choose crypto or select a preset.');
        return;
      }
      proceedWithPayment(null, method, val);
    } else if (selectedSeverity) {
      proceedWithPayment(selectedSeverity, method);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="max-w-3xl w-full"
      data-testid="protocol-selection"
    >
      <div className="mb-4">
        <BackButton to="severity" />
      </div>

      <div className="text-center mb-6">
        <h2
          className="text-3xl sm:text-4xl font-black uppercase tracking-tight mb-2"
          style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
        >
          Karmic Compensation
        </h2>
        <p
          className="text-sm font-mono"
          style={{ color: '#525252' }}
        >
          Select severity level. All paid options issue the same Premium certificate.
        </p>
        <p
          className="text-xs font-mono mt-2"
          style={{ color: '#737373' }}
        >
          This is self-assessed karmic compensation, not a feature tier.
        </p>
      </div>

      {/* SEVERITY OPTIONS — $7 first, then $3, $1 */}
      <div className="space-y-3 mb-4">
        {SEVERITY_OPTIONS.map((opt) => {
          const isSelected = selectedSeverity?.id === opt.id;
          return (
            <button
              key={opt.id}
              onClick={() => handleSeverityClick(opt)}
              disabled={loading}
              className="w-full text-left border-2 p-5 transition-all disabled:opacity-50 hover:translate-x-1"
              style={{
                background: isSelected ? opt.accent : '#FFFFFF',
                borderColor: opt.accent,
                color: isSelected ? '#FFFFFF' : '#0A0A0A',
              }}
              data-testid={`severity-${opt.id}-btn`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div
                    className="text-xl sm:text-2xl font-black uppercase tracking-tight mb-1"
                    style={{ fontFamily: 'Chivo, sans-serif' }}
                  >
                    {opt.label}
                  </div>
                  <div
                    className="text-xs font-mono uppercase tracking-widest mb-3"
                    style={{ opacity: 0.85 }}
                  >
                    {opt.tagline}
                  </div>
                  <ul
                    className="text-xs font-mono space-y-0.5 pl-4"
                    style={{ opacity: 0.85, listStyleType: 'square' }}
                  >
                    {opt.examples.map((ex, i) => (
                      <li key={i}>{ex}</li>
                    ))}
                  </ul>
                </div>
                <div
                  className="text-3xl sm:text-4xl font-black"
                  style={{ fontFamily: 'Chivo, sans-serif' }}
                >
                  ${opt.amount}
                </div>
              </div>
            </button>
          );
        })}

        {/* OTHER AMOUNT */}
        <button
          onClick={handleCustomClick}
          disabled={loading}
          className="w-full text-left border-2 p-5 transition-all disabled:opacity-50 hover:translate-x-1"
          style={{
            background: customMode ? '#0A0A0A' : '#FFFFFF',
            borderColor: '#0A0A0A',
            color: customMode ? '#FFFFFF' : '#0A0A0A',
          }}
          data-testid="severity-custom-btn"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div
                className="text-xl sm:text-2xl font-black uppercase tracking-tight mb-1"
                style={{ fontFamily: 'Chivo, sans-serif' }}
              >
                Other Amount
              </div>
              <div
                className="text-xs font-mono uppercase tracking-widest"
                style={{ opacity: 0.85 }}
              >
                Self-assessed \u2014 you decide
              </div>
            </div>
            <div
              className="text-3xl sm:text-4xl font-black"
              style={{ fontFamily: 'Chivo, sans-serif' }}
            >
              $?
            </div>
          </div>
          {customMode && (
            <div className="mt-4 pt-4" style={{ borderTop: '1px solid rgba(255,255,255,0.3)' }}>
              <label
                className="text-xs uppercase font-bold tracking-widest mb-2 block"
                style={{ opacity: 0.85 }}
              >
                Compensation Amount (USD)
              </label>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-black">$</span>
                <input
                  type="number"
                  min="0.5"
                  max="1000"
                  step="0.50"
                  value={customAmount}
                  onChange={(e) => {
                    setCustomAmount(e.target.value);
                    setError(null);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  placeholder="5.00"
                  className="flex-1 border-2 px-3 py-2 text-lg font-mono font-bold"
                  style={{
                    background: '#FFFFFF',
                    borderColor: '#FFFFFF',
                    color: '#0A0A0A',
                  }}
                  data-testid="custom-amount-input"
                />
              </div>
              <p
                className="text-xs font-mono mt-2"
                style={{ opacity: 0.7 }}
              >
                Min $0.50 \u00b7 Max $1000 \u00b7 Crypto payment only
              </p>
            </div>
          )}
        </button>
      </div>

      {/* PAYMENT METHOD selection (appears after severity chosen) */}
      {(selectedSeverity || (customMode && customAmount)) && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="border-2 p-4 mb-4"
          style={{ background: '#FFFFFF', borderColor: '#0A0A0A' }}
          data-testid="payment-method-panel"
        >
          <div
            className="text-xs uppercase font-bold tracking-widest mb-3"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Choose Payment Method
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              onClick={() => handleConfirmPayment('card')}
              disabled={loading || customMode}
              className="py-3 px-4 font-bold uppercase text-sm border-2 transition-colors disabled:opacity-30"
              style={{
                background: '#0A0A0A',
                color: '#F4F4F0',
                borderColor: '#0A0A0A',
                fontFamily: 'Chivo, sans-serif',
              }}
              data-testid="pay-card-btn"
            >
              {loading ? 'Processing...' : 'Card (Polar.sh)'}
              {customMode && (
                <div className="text-xs font-mono mt-1 opacity-70">
                  Not available for custom
                </div>
              )}
            </button>
            <button
              onClick={() => handleConfirmPayment('crypto')}
              disabled={loading}
              className="py-3 px-4 font-bold uppercase text-sm border-2 transition-colors disabled:opacity-30"
              style={{
                background: 'transparent',
                color: '#0A0A0A',
                borderColor: '#0A0A0A',
                fontFamily: 'Chivo, sans-serif',
              }}
              data-testid="pay-crypto-btn"
            >
              {loading ? 'Processing...' : 'Crypto (Plisio)'}
            </button>
          </div>
          {error && (
            <div
              className="text-xs font-mono mt-3"
              style={{ color: '#D92D20' }}
              data-testid="payment-error"
            >
              {error}
            </div>
          )}
        </motion.div>
      )}

      {/* FREE OPTION — visually secondary, last */}
      <div
        className="border pt-4 mt-6"
        style={{ borderTop: '1px dashed #737373' }}
      >
        <button
          onClick={handleSelectFree}
          disabled={loading}
          className="w-full text-left p-4 transition-opacity disabled:opacity-50 hover:opacity-70"
          style={{
            background: 'transparent',
            color: '#525252',
          }}
          data-testid="severity-free-btn"
        >
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div
                className="text-sm font-mono uppercase tracking-widest mb-1"
                style={{ color: '#525252' }}
              >
                Or: Temporary Absolution Receipt
              </div>
              <div
                className="text-xs font-mono"
                style={{ color: '#737373' }}
              >
                No archive \u00b7 no AI illustration \u00b7 no scheduled delivery \u00b7 limited verification
              </div>
            </div>
            <div
              className="text-sm font-mono uppercase tracking-widest"
              style={{ color: '#525252' }}
            >
              Free \u2192
            </div>
          </div>
        </button>
      </div>

      <p
        className="text-xs text-center mt-8 font-mono"
        style={{ color: '#737373' }}
      >
        Card payments via Polar.sh \u00b7 Crypto via Plisio (BTC, LTC, USDT TRC/BEP, TRX, TON, DOGE)
      </p>
      <p
        className="text-xs text-center mt-2 font-mono"
        style={{ color: '#737373' }}
      >
        By proceeding, you acknowledge our{' '}
        <a
          href="/terms"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:no-underline"
          style={{ color: '#525252' }}
          data-testid="protocol-terms-link"
        >
          Terms & Voluntary Contribution Policy
        </a>
        .
      </p>
    </motion.div>
  );
};

export default ProtocolSelection;
