import { motion } from 'framer-motion';
import axios from 'axios';
import useRitualStore from '../store/ritualStore';
import BackButton from '../components/BackButton';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SeverityResult = () => {
  const severity = useRitualStore((state) => state.severity);
  const confession = useRitualStore((state) => state.confession);
  const name = useRitualStore((state) => state.name);
  const setCertificate = useRitualStore((state) => state.setCertificate);
  const setStep = useRitualStore((state) => state.setStep);

  const handleContinue = async () => {
    // Create certificate
    try {
      const response = await axios.post(`${API}/certificate`, {
        name,
        confession,
        severity_class: severity.severity_class,
        stability: severity.stability,
        risk_score: severity.risk_score,
        protocol: severity.protocol,
        diagnostics: severity.diagnostics,
      });

      setCertificate(
        response.data.uuid,
        response.data.registry_id,
        response.data.tier,
        response.data.status
      );

      setStep('protocol');
    } catch (error) {
      console.error('Failed to create certificate:', error);
    }
  };

  if (!severity) return null;

  const getSeverityColor = () => {
    switch (severity.severity_class) {
      case 'Critical':
        return '#D92D20';
      case 'High':
        return '#B45309';
      case 'Moderate':
        return '#525252';
      default:
        return '#15803D';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl w-full p-8 border-2"
      style={{
        background: '#FFFFFF',
        borderColor: '#0A0A0A',
      }}
      data-testid="severity-result"
    >
      <div className="mb-4">
        <BackButton to="confession" />
      </div>
      {/* Header */}
      <div className="mb-8 text-center">
        <h2
          className="text-2xl sm:text-3xl font-bold uppercase mb-4"
          style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
        >
          Analysis Complete
        </h2>
        
        {/* Severity Stamp */}
        <div
          className="inline-block px-6 py-3 border-2 transform -rotate-3 mt-4"
          style={{
            borderColor: getSeverityColor(),
            color: getSeverityColor(),
          }}
        >
          <span
            className="text-xl font-black uppercase tracking-widest"
            style={{ fontFamily: 'Chivo, sans-serif' }}
          >
            CLASS {severity.severity_class.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Details Grid */}
      <div className="space-y-4 mb-8">
        <div className="border-t-2 pt-4" style={{ borderColor: '#E5E5DF' }}>
          <div
            className="text-xs uppercase font-bold tracking-widest mb-1"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Emotional Stability
          </div>
          <div
            className="text-base font-mono"
            style={{ color: '#0A0A0A' }}
          >
            {severity.stability}
          </div>
        </div>

        <div className="border-t-2 pt-4" style={{ borderColor: '#E5E5DF' }}>
          <div
            className="text-xs uppercase font-bold tracking-widest mb-1"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Risk Score
          </div>
          <div className="flex items-center gap-4">
            <div
              className="text-3xl font-black"
              style={{ color: getSeverityColor(), fontFamily: 'Chivo, sans-serif' }}
            >
              {severity.risk_score}
            </div>
            <div className="flex-1">
              <div
                className="h-2 rounded overflow-hidden"
                style={{ background: '#E5E5DF' }}
              >
                <div
                  className="h-full"
                  style={{
                    width: `${severity.risk_score}%`,
                    background: getSeverityColor(),
                  }}
                />
              </div>
            </div>
            <div
              className="text-sm font-mono"
              style={{ color: '#737373' }}
            >
              /100
            </div>
          </div>
        </div>

        <div className="border-t-2 pt-4" style={{ borderColor: '#E5E5DF' }}>
          <div
            className="text-xs uppercase font-bold tracking-widest mb-1"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Protocol Required
          </div>
          <div
            className="text-base font-mono"
            style={{ color: '#0A0A0A' }}
          >
            {severity.protocol}
          </div>
        </div>

        <div className="border-t-2 pt-4" style={{ borderColor: '#E5E5DF' }}>
          <div
            className="text-xs uppercase font-bold tracking-widest mb-2"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Diagnostics
          </div>
          <ul className="space-y-1">
            {severity.diagnostics.map((diag, idx) => (
              <li
                key={idx}
                className="text-sm font-mono"
                style={{ color: '#525252' }}
              >
                • {diag}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Continue Button */}
      <button
        onClick={handleContinue}
        className="w-full py-3 font-bold uppercase text-sm border-2 transition-colors"
        style={{
          background: '#0A0A0A',
          color: '#F4F4F0',
          borderColor: '#0A0A0A',
          fontFamily: 'Chivo, sans-serif',
        }}
        data-testid="continue-to-protocol-btn"
      >
        Proceed to Protocol Selection
      </button>
    </motion.div>
  );
};

export default SeverityResult;