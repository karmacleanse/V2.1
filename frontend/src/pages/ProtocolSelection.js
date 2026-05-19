import { useState } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import useRitualStore from '../store/ritualStore';
import CryptoPayment from '../components/CryptoPayment';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const tiers = [
  {
    id: 'free',
    name: 'Temporary Absolution',
    price: 'Free',
    amount: 0,
    features: [
      'Valid for 24 hours',
      'Basic certificate',
      'No archival',
      'Limited verification',
    ],
    buttonText: 'Issue Free Certificate',
  },
  {
    id: 'standard',
    name: 'Certified Absolution',
    price: '$1',
    amount: 1,
    tier_key: 'standard',
    features: [
      'Permanent record',
      'Full verification',
      'Registry archived',
      'Shareable QR code',
    ],
    buttonText: 'Upgrade for $1',
  },
  {
    id: 'premium',
    name: 'Premium Certification',
    price: '$3',
    amount: 3,
    tier_key: 'premium',
    features: [
      'All Standard features',
      'Priority processing',
      'Enhanced verification',
      'Expedited delivery',
    ],
    buttonText: 'Upgrade for $3',
  },
  {
    id: 'enterprise',
    name: 'Enterprise Protocol',
    price: '$7',
    amount: 7,
    tier_key: 'enterprise',
    features: [
      'All Premium features',
      'VIP status',
      'Multiple certificates',
      'Custom branding',
    ],
    buttonText: 'Upgrade for $7',
  },
];

const ProtocolSelection = () => {
  const [loading, setLoading] = useState(false);
  const [cryptoModal, setCryptoModal] = useState(null); // tier object when active
  const certificateUuid = useRitualStore((state) => state.certificateUuid);
  const setStep = useRitualStore((state) => state.setStep);
  const setTier = useRitualStore((state) => state.setTier);

  const handleSelectFree = () => {
    setStep('certificate');
  };

  const handleStripePayment = async (tier) => {
    setLoading(true);
    try {
      const originUrl = window.location.origin;
      const response = await axios.post(`${API}/checkout/session`, {
        tier: tier.tier_key,
        certificate_uuid: certificateUuid,
        origin_url: originUrl,
      });

      if (response.data?.url) {
        window.location.href = response.data.url;
      } else {
        throw new Error('No checkout URL received');
      }
    } catch (error) {
      console.error('Payment initiation failed:', error);
      alert('Payment initiation failed. Please try again or use crypto.');
      setLoading(false);
    }
  };

  const handleCryptoPayment = (tier) => {
    setCryptoModal(tier);
  };

  const handleCryptoSuccess = () => {
    setTier('paid');
    setCryptoModal(null);
    setStep('certificate');
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-5xl w-full p-6"
        data-testid="protocol-selection"
      >
        <h2
          className="text-3xl sm:text-4xl font-bold uppercase mb-2 text-center"
          style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
        >
          Select Protocol
        </h2>
        <p
          className="text-sm mb-8 text-center"
          style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
        >
          Choose your certification level
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {tiers.map((tier) => (
            <motion.div
              key={tier.id}
              whileHover={{ scale: 1.02 }}
              className="border-2 p-6 flex flex-col"
              style={{ background: '#FFFFFF', borderColor: '#0A0A0A' }}
              data-testid={`tier-${tier.id}`}
            >
              {/* Header */}
              <div className="mb-4">
                <h3
                  className="text-lg font-bold uppercase mb-2"
                  style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
                >
                  {tier.name}
                </h3>
                <div
                  className="text-3xl font-black"
                  style={{
                    fontFamily: 'Chivo, sans-serif',
                    color: tier.id === 'free' ? '#15803D' : '#D92D20',
                  }}
                >
                  {tier.price}
                </div>
              </div>

              {/* Features */}
              <ul className="space-y-2 mb-6 flex-1">
                {tier.features.map((feature, idx) => (
                  <li
                    key={idx}
                    className="text-xs font-mono"
                    style={{ color: '#525252' }}
                  >
                    • {feature}
                  </li>
                ))}
              </ul>

              {/* Buttons */}
              {tier.id === 'free' ? (
                <button
                  onClick={handleSelectFree}
                  disabled={loading}
                  className="w-full py-3 font-bold uppercase text-xs border-2 transition-colors disabled:opacity-50"
                  style={{
                    background: 'transparent',
                    color: '#0A0A0A',
                    borderColor: '#0A0A0A',
                    fontFamily: 'Chivo, sans-serif',
                  }}
                  data-testid={`select-${tier.id}-btn`}
                >
                  {tier.buttonText}
                </button>
              ) : (
                <div className="space-y-2">
                  <button
                    onClick={() => handleStripePayment(tier)}
                    disabled={loading}
                    className="w-full py-3 font-bold uppercase text-xs border-2 transition-colors disabled:opacity-50"
                    style={{
                      background: '#0A0A0A',
                      color: '#F4F4F0',
                      borderColor: '#0A0A0A',
                      fontFamily: 'Chivo, sans-serif',
                    }}
                    data-testid={`select-${tier.id}-btn`}
                  >
                    {loading ? 'Processing...' : `Pay Card`}
                  </button>
                  <button
                    onClick={() => handleCryptoPayment(tier)}
                    disabled={loading}
                    className="w-full py-2.5 font-bold uppercase text-xs border-2 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                    style={{
                      background: 'transparent',
                      color: '#0A0A0A',
                      borderColor: '#0A0A0A',
                      fontFamily: 'Chivo, sans-serif',
                    }}
                    data-testid={`crypto-${tier.id}-btn`}
                  >
                    <span>🦊</span>
                    <span>Pay {tier.amount} USDC</span>
                  </button>
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Footer info */}
        <p
          className="text-xs text-center mt-8 font-mono"
          style={{ color: '#737373' }}
        >
          Crypto payments via MetaMask on Polygon network. No intermediaries.
        </p>
      </motion.div>

      {/* Crypto Payment Modal */}
      {cryptoModal && (
        <CryptoPayment
          tier={cryptoModal.name}
          tierKey={cryptoModal.tier_key}
          amount={cryptoModal.amount}
          onSuccess={handleCryptoSuccess}
          onCancel={() => setCryptoModal(null)}
        />
      )}
    </>
  );
};

export default ProtocolSelection;
