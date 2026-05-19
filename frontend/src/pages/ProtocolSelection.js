import { useState } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import useRitualStore from '../store/ritualStore';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const tiers = [
  {
    id: 'free',
    name: 'Temporary Absolution',
    price: 'Free',
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
  const certificateUuid = useRitualStore((state) => state.certificateUuid);
  const setStep = useRitualStore((state) => state.setStep);

  const handleSelect = async (tier) => {
    if (tier.id === 'free') {
      // Go directly to certificate view
      setStep('certificate');
      return;
    }

    // Initiate payment
    setLoading(true);
    try {
      const originUrl = window.location.origin;
      const response = await axios.post(`${API}/checkout/session`, {
        tier: tier.tier_key,
        certificate_uuid: certificateUuid,
        origin_url: originUrl,
      });

      // Redirect to Stripe
      window.location.href = response.data.url;
    } catch (error) {
      console.error('Payment initiation failed:', error);
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-4xl w-full p-6"
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
            style={{
              background: '#FFFFFF',
              borderColor: '#0A0A0A',
            }}
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

            {/* Button */}
            <button
              onClick={() => handleSelect(tier)}
              disabled={loading}
              className="w-full py-3 font-bold uppercase text-xs border-2 transition-colors disabled:opacity-50"
              style={{
                background: tier.id === 'free' ? 'transparent' : '#0A0A0A',
                color: tier.id === 'free' ? '#0A0A0A' : '#F4F4F0',
                borderColor: '#0A0A0A',
                fontFamily: 'Chivo, sans-serif',
              }}
              data-testid={`select-${tier.id}-btn`}
            >
              {loading ? 'Processing...' : tier.buttonText}
            </button>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};

export default ProtocolSelection;