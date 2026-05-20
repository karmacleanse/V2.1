import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, useLocation, useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import useRitualStore from './store/ritualStore';

import Landing from './pages/Landing';
import IdentityStep from './pages/IdentityStep';
import ConfessionStep from './pages/ConfessionStep';
import ProcessingRitual from './pages/ProcessingRitual';
import SeverityResult from './pages/SeverityResult';
import ProtocolSelection from './pages/ProtocolSelection';
import CertificateView from './pages/CertificateView';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Main funnel controller
const Funnel = () => {
  const step = useRitualStore((state) => state.step);
  const setStep = useRitualStore((state) => state.setStep);
  const location = useLocation();
  const navigate = useNavigate();

  // Handle payment return
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const success = params.get('success');
    const polarSuccess = params.get('polar_success');
    const cryptomusSuccess = params.get('cryptomus_success');
    const sessionId = params.get('session_id');
    const checkoutId = params.get('checkout_id');
    const certUuid = params.get('cert_uuid');

    if (success === 'true' && sessionId) {
      pollPaymentStatus(sessionId);
    } else if (polarSuccess === 'true' && checkoutId) {
      pollPolarStatus(checkoutId);
    } else if (cryptomusSuccess === 'true' && certUuid) {
      pollCryptomusStatus(certUuid);
    }
  }, [location]);

  const pollCryptomusStatus = async (certUuid, attempts = 0) => {
    const maxAttempts = 60;
    if (attempts >= maxAttempts) {
      alert('Payment processing — check back in 10 minutes.');
      return;
    }
    try {
      const response = await axios.get(`${API}/cryptomus/status/${certUuid}`);
      if (response.data.is_paid) {
        setStep('certificate');
        navigate('/', { replace: true });
      } else {
        setTimeout(() => pollCryptomusStatus(certUuid, attempts + 1), 10000);
      }
    } catch (error) {
      console.error('Cryptomus poll error:', error);
      setTimeout(() => pollCryptomusStatus(certUuid, attempts + 1), 10000);
    }
  };

  const pollPolarStatus = async (checkoutId, attempts = 0) => {
    const maxAttempts = 15;
    if (attempts >= maxAttempts) {
      alert('Payment confirmation pending. Refresh page in a minute.');
      return;
    }

    try {
      const response = await axios.get(`${API}/polar/status/${checkoutId}`);

      if (response.data.payment_status === 'paid') {
        setStep('certificate');
        navigate('/', { replace: true });
      } else {
        setTimeout(() => pollPolarStatus(checkoutId, attempts + 1), 2000);
      }
    } catch (error) {
      console.error('Error checking Polar status:', error);
      setTimeout(() => pollPolarStatus(checkoutId, attempts + 1), 2000);
    }
  };

  const pollPaymentStatus = async (sessionId, attempts = 0) => {
    const maxAttempts = 10;
    if (attempts >= maxAttempts) {
      alert('Payment verification timeout. Please contact support.');
      return;
    }

    try {
      const response = await axios.get(`${API}/checkout/status/${sessionId}`);
      
      if (response.data.payment_status === 'paid') {
        // Payment successful, show certificate
        setStep('certificate');
        // Clean URL
        navigate('/', { replace: true });
      } else if (response.data.status === 'expired') {
        alert('Payment session expired.');
        setStep('protocol');
      } else {
        // Continue polling
        setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), 2000);
      }
    } catch (error) {
      console.error('Error checking payment status:', error);
      setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), 2000);
    }
  };

  const renderStep = () => {
    switch (step) {
      case 'landing':
        return <Landing />;
      case 'identity':
        return <IdentityStep />;
      case 'confession':
        return <ConfessionStep />;
      case 'processing':
        return <ProcessingRitual />;
      case 'severity':
        return <SeverityResult />;
      case 'protocol':
        return <ProtocolSelection />;
      case 'certificate':
        return <CertificateView />;
      default:
        return <Landing />;
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-8"
      style={{ background: '#F4F4F0' }}
    >
      {renderStep()}
    </div>
  );
};

// Verification page (public)
const VerificationPage = () => {
  const { registryId } = useParams();
  const [certificate, setCertificate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCert = async () => {
      try {
        const response = await axios.get(`${API}/verify/${registryId}`);
        setCertificate(response.data);
      } catch (err) {
        setError(err.response?.status === 404 ? 'Certificate not found' : 'Verification failed');
      } finally {
        setLoading(false);
      }
    };
    fetchCert();
  }, [registryId]);

  const getSeverityColor = (severityClass) => {
    switch (severityClass) {
      case 'Critical': return '#D92D20';
      case 'High': return '#B45309';
      case 'Moderate': return '#525252';
      default: return '#15803D';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#F4F4F0' }}>
        <div className="font-mono text-sm" style={{ color: '#525252' }}>
          Loading verification...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#F4F4F0' }}>
        <div className="max-w-md w-full border-2 p-8" style={{ background: '#FFFFFF', borderColor: '#0A0A0A' }}>
          <div className="text-center">
            <div className="inline-block px-6 py-3 border-2 transform -rotate-3 mb-4"
              style={{ borderColor: '#D92D20', color: '#D92D20' }}>
              <span className="text-lg font-black uppercase tracking-widest" style={{ fontFamily: 'Chivo, sans-serif' }}>
                INVALID
              </span>
            </div>
            <h2 className="text-2xl font-bold uppercase mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
              Verification Failed
            </h2>
            <p className="text-sm font-mono" style={{ color: '#525252' }}>
              {error}: {registryId}
            </p>
            <p className="text-xs font-mono mt-4" style={{ color: '#737373' }}>
              This certificate is not registered in the Karma Cleanse archive.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8" style={{ background: '#F4F4F0' }}>
      <div className="max-w-2xl w-full border-2 p-8 relative overflow-hidden" style={{ background: '#FFFFFF', borderColor: '#0A0A0A' }} data-testid="verification-page">
        {/* AI-generated sketch watermark (paid tier only) */}
        {certificate.sketch_url && (
          <div
            className="absolute pointer-events-none"
            style={{
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '75%',
              maxWidth: '520px',
              opacity: 0.18,
              zIndex: 0,
              mixBlendMode: 'multiply',
            }}
            data-testid="verification-sketch-watermark"
          >
            <img
              src={certificate.sketch_url}
              alt=""
              className="w-full h-auto"
              style={{ filter: 'grayscale(100%) contrast(1.05)' }}
            />
          </div>
        )}

        <div className="relative" style={{ zIndex: 2 }}>
        {/* Stamp */}
        <div className="text-center mb-6">
          <div className="inline-block px-6 py-3 border-2 transform -rotate-3"
            style={{ borderColor: '#15803D', color: '#15803D' }}>
            <span className="text-lg font-black uppercase tracking-widest" style={{ fontFamily: 'Chivo, sans-serif' }}>
              VERIFIED
            </span>
          </div>
        </div>

        <h1 className="text-3xl font-black uppercase tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Karma Cleanse
        </h1>
        <div className="text-xs uppercase tracking-widest mb-6" style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}>
          Official Registry Verification
        </div>

        <div className="border-t-2 pt-4 mb-4" style={{ borderColor: '#E5E5DF' }}>
          <div className="text-xs uppercase font-bold tracking-widest mb-1" style={{ color: '#737373' }}>
            Registry ID
          </div>
          <div className="text-2xl font-black tracking-tight" style={{ fontFamily: 'Chivo, sans-serif' }}>
            {certificate.registry_id}
          </div>
        </div>

        <div className="border-t-2 pt-4 mb-4" style={{ borderColor: '#E5E5DF' }}>
          <div className="text-xs uppercase font-bold tracking-widest mb-1" style={{ color: '#737373' }}>
            Subject
          </div>
          <div className="text-base font-mono">{certificate.name || 'Anonymous Entity'}</div>
        </div>

        {certificate.confession && (
          <div className="border-t-2 pt-4 mb-4" style={{ borderColor: '#E5E5DF' }}>
            <div className="text-xs uppercase font-bold tracking-widest mb-2" style={{ color: '#737373' }}>
              Incident Report
            </div>
            <blockquote
              className="text-sm font-mono whitespace-pre-wrap border-l-4 pl-3 py-1"
              style={{ color: '#0A0A0A', borderColor: '#0A0A0A', background: 'rgba(244,244,240,0.6)' }}
              data-testid="verification-confession-text"
            >
              {certificate.confession}
            </blockquote>
          </div>
        )}

        <div className="border-t-2 pt-4 mb-4" style={{ borderColor: '#E5E5DF' }}>
          <div className="text-xs uppercase font-bold tracking-widest mb-2" style={{ color: '#737373' }}>
            Classification
          </div>
          <div className="inline-block px-4 py-2 border-2"
            style={{ borderColor: getSeverityColor(certificate.severity_class), color: getSeverityColor(certificate.severity_class) }}>
            <span className="text-lg font-black uppercase tracking-wider" style={{ fontFamily: 'Chivo, sans-serif' }}>
              CLASS {certificate.severity_class.toUpperCase()}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 border-t-2 pt-4 mb-4" style={{ borderColor: '#E5E5DF' }}>
          <div>
            <div className="text-xs uppercase font-bold tracking-widest mb-1" style={{ color: '#737373' }}>
              Stability
            </div>
            <div className="text-sm font-mono">{certificate.stability}</div>
          </div>
          <div>
            <div className="text-xs uppercase font-bold tracking-widest mb-1" style={{ color: '#737373' }}>
              Risk Score
            </div>
            <div className="text-sm font-mono">{certificate.risk_score}/100</div>
          </div>
        </div>

        <div className="border-t-2 pt-4 mb-4" style={{ borderColor: '#E5E5DF' }}>
          <div className="text-xs uppercase font-bold tracking-widest mb-1" style={{ color: '#737373' }}>
            Protocol Applied
          </div>
          <div className="text-sm font-mono">{certificate.protocol}</div>
        </div>

        <div className="border-t-2 pt-4 mb-4" style={{ borderColor: '#E5E5DF' }}>
          <div className="text-xs uppercase font-bold tracking-widest mb-1" style={{ color: '#737373' }}>
            Status
          </div>
          <div className="text-sm font-mono uppercase font-bold"
            style={{ color: certificate.tier === 'paid' ? '#15803D' : '#B45309' }}>
            {certificate.status} — {certificate.tier} tier
          </div>
        </div>

        <div className="border-t-2 pt-4" style={{ borderColor: '#E5E5DF' }}>
          <div className="text-xs uppercase font-bold tracking-widest mb-1" style={{ color: '#737373' }}>
            Issued
          </div>
          <div className="text-sm font-mono">
            {new Date(certificate.created_at).toLocaleString()}
          </div>
        </div>

        <p className="text-xs text-center mt-6 font-mono" style={{ color: '#737373' }}>
          This certificate is authentic and registered in the Karma Cleanse archive.
          <br />
          Emotional bureaucracy since 2026.
        </p>
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Funnel />} />
        <Route path="/verify/:registryId" element={<VerificationPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
