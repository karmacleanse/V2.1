import { useState } from 'react';
import { motion } from 'framer-motion';
import useRitualStore from '../store/ritualStore';

const IdentityStep = () => {
  const [input, setInput] = useState('');
  const setName = useRitualStore((state) => state.setName);
  const setAnonymous = useRitualStore((state) => state.setAnonymous);
  const setStep = useRitualStore((state) => state.setStep);

  const handleSubmit = () => {
    if (input.trim()) {
      setName(input.trim());
    }
    setStep('confession');
  };

  const handleAnonymous = () => {
    setAnonymous();
    setStep('confession');
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-md w-full p-8 border-2"
      style={{
        background: '#FFFFFF',
        borderColor: '#0A0A0A',
      }}
      data-testid="identity-step"
    >
      <h2
        className="text-2xl sm:text-3xl font-bold uppercase mb-2"
        style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
      >
        Identity Registry
      </h2>
      <p
        className="text-sm mb-8"
        style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
      >
        How should the registry identify you?
      </p>

      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Enter designation..."
        className="w-full border-2 px-4 py-3 text-base mb-4 font-mono focus:outline-none"
        style={{
          background: '#F4F4F0',
          borderColor: '#0A0A0A',
          color: '#0A0A0A',
        }}
        onKeyDown={(e) => e.key === 'Enter' && input.trim() && handleSubmit()}
        data-testid="identity-input"
      />

      <button
        onClick={handleSubmit}
        disabled={!input.trim()}
        className="w-full py-3 font-bold uppercase text-sm mb-3 border-2 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        style={{
          background: input.trim() ? '#0A0A0A' : '#E5E5DF',
          color: input.trim() ? '#F4F4F0' : '#737373',
          borderColor: '#0A0A0A',
          fontFamily: 'Chivo, sans-serif',
        }}
        data-testid="register-identity-btn"
      >
        Register Identity
      </button>

      <button
        onClick={handleAnonymous}
        className="w-full border-2 py-3 text-sm uppercase font-bold transition-colors"
        style={{
          background: 'transparent',
          color: '#525252',
          borderColor: '#0A0A0A',
          fontFamily: 'Chivo, sans-serif',
        }}
        onMouseEnter={(e) => {
          e.target.style.background = '#F4F4F0';
          e.target.style.color = '#0A0A0A';
        }}
        onMouseLeave={(e) => {
          e.target.style.background = 'transparent';
          e.target.style.color = '#525252';
        }}
        data-testid="remain-anonymous-btn"
      >
        Remain Anonymous
      </button>
    </motion.div>
  );
};

export default IdentityStep;