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
import Terms from './pages/Terms';
import AdminDashboard from './pages/AdminDashboard';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Main funnel controller
const Funnel = () => {
  const step = useRitualStore((state) => state.step);
  const setStep = useRitualStore((state) => state.setStep);
  const location = useLocation();
  const navigate = useNavigate();
  const [pollingState, setPollingState] = useState(null); // { provider, attempt, max }

  // Handle payment return
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const polarSuccess = params.get('polar_success');
    const plisioSuccess = params.get('plisio_success');
    const certUuid = params.get('cert_uuid');

    if (polarSuccess === 'true') {
      // Prefer cert_uuid from URL; fall back to persisted store value
      const uuid = certUuid || useRitualStore.getState().certificateUuid;
      if (uuid) pollPaymentByCert(uuid, 'polar');
    } else if (plisioSuccess === 'true') {
      const uuid = certUuid || useRitualStore.getState().certificateUuid;
      if (uuid) pollPaymentByCert(uuid, 'plisio');
    }
  }, [location]);

  // Unified polling: 60 attempts × 5 seconds = 5 minutes
  const POLL_MAX = 60;
  const POLL_INTERVAL = 5000;

  const pollPaymentByCert = async (certUuid, provider, attempts = 0) => {
    setPollingState((prev) => ({
      ...(prev || {}),
      provider,
      certUuid,
      attempt: attempts + 1,
      max: POLL_MAX,
      reconciling: prev?.reconciling || false,
    }));
    if (attempts >= POLL_MAX) {
      setPollingState({ provider, certUuid, timedOut: true });
      return;
    }
    try {
      const response = await axios.get(`${API}/payment/status/${certUuid}`);
      if (response.data.is_paid) {
        setPollingState(null);
        setStep('certificate');
        navigate('/', { replace: true });
      } else {
        setTimeout(() => pollPaymentByCert(certUuid, provider, attempts + 1), POLL_INTERVAL);
      }
    } catch (error) {
      console.error(`${provider} poll error:`, error);
      setTimeout(() => pollPaymentByCert(certUuid, provider, attempts + 1), POLL_INTERVAL);
    }
  };

  const triggerReconcile = async (certUuid) => {
    if (!certUuid) return;
    setPollingState((prev) => ({ ...(prev || {}), reconciling: true }));
    try {
      const response = await axios.post(`${API}/payment/reconcile`, {
        certificate_uuid: certUuid,
      });
      if (response.data.is_paid) {
        setPollingState(null);
        setStep('certificate');
        navigate('/', { replace: true });
      } else {
        setPollingState((prev) => ({
          ...(prev || {}),
          reconciling: false,
          reconcileMessage: response.data.message || 'Polar reports the payment is not yet confirmed.',
        }));
      }
    } catch (error) {
      console.error('Reconcile error:', error);
      setPollingState((prev) => ({
        ...(prev || {}),
        reconciling: false,
        reconcileMessage: 'Reconciliation failed. Please contact support.',
      }));
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
      className="min-h-screen flex items-center justify-center px-4 py-8 relative"
      style={{ background: '#F4F4F0' }}
    >
      {pollingState && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center px-4"
          style={{ background: 'rgba(244,244,240,0.96)' }}
          data-testid="payment-polling-overlay"
        >
          <div
            className="max-w-md w-full border-2 p-8 text-center"
            style={{ background: '#FFFFFF', borderColor: '#0A0A0A' }}
          >
            <div
              className="text-xs uppercase tracking-widest mb-4"
              style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
            >
              Payment Provider · {pollingState.provider === 'polar' ? 'Polar.sh' : 'Plisio'}
            </div>
            {!pollingState.timedOut ? (
              <>
                <h2
                  className="text-2xl font-black uppercase tracking-tight mb-2"
                  style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
                >
                  Verifying Payment
                </h2>
                <p
                  className="text-sm font-mono mb-6"
                  style={{ color: '#525252' }}
                >
                  Awaiting webhook confirmation from {pollingState.provider}. This usually takes 10-30 seconds.
                </p>
                <div className="flex items-center justify-center gap-2 mb-4">
                  <span className="inline-block w-3 h-3 animate-pulse" style={{ background: '#0A0A0A' }} />
                  <span className="inline-block w-3 h-3 animate-pulse" style={{ background: '#0A0A0A', animationDelay: '0.2s' }} />
                  <span className="inline-block w-3 h-3 animate-pulse" style={{ background: '#0A0A0A', animationDelay: '0.4s' }} />
                </div>
                <div
                  className="text-xs font-mono mb-4"
                  style={{ color: '#737373' }}
                >
                  Attempt {pollingState.attempt} of {pollingState.max} · Elapsed ~{Math.round((pollingState.attempt * 5))} sec
                </div>
                {pollingState.attempt > 6 && pollingState.provider === 'polar' && (
                  <button
                    onClick={() => triggerReconcile(pollingState.certUuid)}
                    disabled={pollingState.reconciling}
                    className="py-2 px-4 font-bold uppercase text-xs border-2 disabled:opacity-50"
                    style={{
                      background: 'transparent',
                      color: '#0A0A0A',
                      borderColor: '#0A0A0A',
                      fontFamily: 'Chivo, sans-serif',
                    }}
                    data-testid="reconcile-payment-btn"
                  >
                    {pollingState.reconciling ? 'Checking with Polar...' : 'I already paid — verify now'}
                  </button>
                )}
              </>
            ) : (
              <>
                <h2
                  className="text-2xl font-black uppercase tracking-tight mb-2"
                  style={{ fontFamily: 'Chivo, sans-serif', color: '#B45309' }}
                >
                  Confirmation Pending
                </h2>
                <p
                  className="text-sm font-mono mb-6"
                  style={{ color: '#525252' }}
                >
                  Your payment may still be processing on the {pollingState.provider} network.
                  Your certificate will be issued automatically once confirmed.
                  You can safely close this page and return later.
                </p>
                <div className="flex flex-col gap-2">
                  {pollingState.provider === 'polar' && (
                    <button
                      onClick={() => triggerReconcile(pollingState.certUuid)}
                      disabled={pollingState.reconciling}
                      className="py-2 px-6 font-bold uppercase text-sm border-2 disabled:opacity-50"
                      style={{
                        background: '#0A0A0A',
                        color: '#F4F4F0',
                        borderColor: '#0A0A0A',
                        fontFamily: 'Chivo, sans-serif',
                      }}
                      data-testid="reconcile-timeout-btn"
                    >
                      {pollingState.reconciling ? 'Checking...' : 'Verify Payment with Polar'}
                    </button>
                  )}
                  <button
                    onClick={() => {
                      setPollingState(null);
                      navigate('/', { replace: true });
                    }}
                    className="py-2 px-6 font-bold uppercase text-sm border-2"
                    style={{
                      background: 'transparent',
                      color: '#0A0A0A',
                      borderColor: '#0A0A0A',
                      fontFamily: 'Chivo, sans-serif',
                    }}
                    data-testid="polling-dismiss-btn"
                  >
                    Return to Home
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
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

        {certificate.receipt_type === 'tc_acknowledgment' && (
          <>
            <div className="border-t-2 pt-4 mb-4" style={{ borderColor: '#E5E5DF' }}>
              <div className="text-xs uppercase font-bold tracking-widest mb-1" style={{ color: '#737373' }}>
                Declared Jurisdiction
              </div>
              <div className="text-base font-mono">{certificate.jurisdiction || 'Unspecified'}</div>
            </div>

            <div className="border-t-2 pt-4 mb-4" style={{ borderColor: '#E5E5DF' }}>
              <div className="text-xs uppercase font-bold tracking-widest mb-2" style={{ color: '#737373' }}>
                Documents Acknowledged
              </div>
              <ul className="pl-6 text-sm font-mono space-y-1" style={{ listStyleType: 'square' }}>
                {(certificate.acknowledgments || []).map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          </>
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

        {certificate.receipt_type !== 'tc_acknowledgment' && (
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
        )}

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
        <Route path="/terms" element={<Terms />} />
        <Route path="/admin" element={<AdminDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
