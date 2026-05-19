import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import useRitualStore from '../store/ritualStore';

const placeholders = [
  'I ghosted someone.',
  'I overreacted during a meeting.',
  'I became the problem.',
  'I lied for convenience.',
  'I sent the risky message.',
  'I took the last coffee without brewing a new pot.',
  'I read the message and never replied.',
  'I forgot their birthday intentionally.',
];

const ConfessionStep = () => {
  const [text, setText] = useState('');
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const setConfession = useRitualStore((state) => state.setConfession);
  const setStep = useRitualStore((state) => state.setStep);

  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderIdx((i) => (i + 1) % placeholders.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = () => {
    setConfession(text);
    setStep('processing');
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
      data-testid="confession-step"
    >
      <h2
        className="text-2xl sm:text-3xl font-bold uppercase mb-2"
        style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
      >
        Incident Declaration
      </h2>
      <p
        className="text-sm mb-8"
        style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
      >
        Describe the imbalance requiring correction.
      </p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholders[placeholderIdx]}
        rows={6}
        maxLength={500}
        className="w-full border-2 px-4 py-3 text-base mb-2 resize-none focus:outline-none font-mono"
        style={{
          background: '#F4F4F0',
          borderColor: '#0A0A0A',
          color: '#0A0A0A',
        }}
        data-testid="confession-textarea"
      />

      <p
        className="text-xs mb-4 text-right font-mono"
        style={{ color: '#737373' }}
      >
        {text.length}/500
      </p>

      <button
        onClick={handleSubmit}
        disabled={text.trim().length < 5}
        className="w-full py-3 font-bold uppercase text-sm border-2 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        style={{
          background: text.trim().length >= 5 ? '#0A0A0A' : '#E5E5DF',
          color: text.trim().length >= 5 ? '#F4F4F0' : '#737373',
          borderColor: '#0A0A0A',
          fontFamily: 'Chivo, sans-serif',
        }}
        data-testid="submit-incident-btn"
      >
        Submit Incident Report
      </button>
    </motion.div>
  );
};

export default ConfessionStep;