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
  const location = useLocation();
  const navigate = useNavigate();
  const { setStep, setCertificate } = useRitualStore();

  // Handle payment return
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const success = params.get('success');
    const sessionId = params.get('session_id');

    if (success === 'true' && sessionId) {
      // Poll payment status
      pollPaymentStatus(sessionId);
    }
  }, [location]);

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

  useEffect(() => {
    // Fetch certificate by registry ID
    // This would need a backend endpoint to look up by registry_id
    // For now, simplified
    setLoading(false);
  }, [registryId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center font-mono">Loading verification...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-2xl w-full border-2 p-8 bg-white">
        <h1 className="text-3xl font-black uppercase mb-4">
          Certificate Verification
        </h1>
        <p className="font-mono">Registry ID: {registryId}</p>
        {/* Display certificate details */}
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
