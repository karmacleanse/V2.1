import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import QRCode from 'react-qr-code';
import axios from 'axios';
import useRitualStore from '../store/ritualStore';

const CertificateView = () => {
  const { registryId, name, severity, tier, status } = useRitualStore();
  const [showDelivery, setShowDelivery] = useState(false);

  const verificationUrl = `${window.location.origin}/verify/${registryId}`;

  const getSeverityColor = () => {
    if (!severity) return '#525252';
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

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: 'Karma Cleanse Certificate',
        text: `Certificate ${registryId}`,
        url: verificationUrl,
      });
    } else {
      navigator.clipboard.writeText(verificationUrl);
      alert('Link copied to clipboard!');
    }
  };

  if (!severity) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-3xl w-full"
      data-testid="certificate-view"
    >
      {/* Certificate */}
      <div
        className="border-2 p-8 mb-6"
        style={{
          background: '#FFFFFF',
          borderColor: '#0A0A0A',
        }}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1
              className="text-3xl font-black uppercase tracking-tight mb-2"
              style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
            >
              Karma Cleanse
            </h1>
            <div
              className="text-xs uppercase tracking-widest"
              style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
            >
              Official Certificate v2.1
            </div>
          </div>
          <img
            src="https://static.prod-images.emergentagent.com/jobs/ffea1c83-c6cc-46b9-b35f-810f49dbc24e/images/7c21a7f1a11372181bf010fe1e96f49aaffa8a407a0bc1c67d9e00400f23885a.png"
            alt="Seal"
            className="w-16 h-16"
          />
        </div>

        {/* Registry ID */}
        <div className="mb-6">
          <div
            className="text-xs uppercase font-bold tracking-widest mb-1"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Registry ID
          </div>
          <div
            className="text-2xl font-black tracking-tight"
            style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
          >
            {registryId}
          </div>
        </div>

        {/* Subject */}
        <div className="border-t-2 pt-4 mb-4" style={{ borderColor: '#E5E5DF' }}>
          <div
            className="text-xs uppercase font-bold tracking-widest mb-1"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Subject
          </div>
          <div
            className="text-base font-mono"
            style={{ color: '#0A0A0A' }}
          >
            {name || 'Anonymous Entity'}
          </div>
        </div>

        {/* Severity Classification */}
        <div className="border-t-2 pt-4 mb-4" style={{ borderColor: '#E5E5DF' }}>
          <div
            className="text-xs uppercase font-bold tracking-widest mb-2"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Classification
          </div>
          <div
            className="inline-block px-4 py-2 border-2"
            style={{
              borderColor: getSeverityColor(),
              color: getSeverityColor(),
            }}
          >
            <span
              className="text-lg font-black uppercase tracking-wider"
              style={{ fontFamily: 'Chivo, sans-serif' }}
            >
              CLASS {severity.severity_class.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-2 gap-4 border-t-2 pt-4 mb-6" style={{ borderColor: '#E5E5DF' }}>
          <div>
            <div
              className="text-xs uppercase font-bold tracking-widest mb-1"
              style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
            >
              Stability
            </div>
            <div
              className="text-sm font-mono"
              style={{ color: '#0A0A0A' }}
            >
              {severity.stability}
            </div>
          </div>
          <div>
            <div
              className="text-xs uppercase font-bold tracking-widest mb-1"
              style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
            >
              Risk Score
            </div>
            <div
              className="text-sm font-mono"
              style={{ color: '#0A0A0A' }}
            >
              {severity.risk_score}/100
            </div>
          </div>
        </div>

        {/* Protocol */}
        <div className="border-t-2 pt-4 mb-6" style={{ borderColor: '#E5E5DF' }}>
          <div
            className="text-xs uppercase font-bold tracking-widest mb-1"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Protocol Applied
          </div>
          <div
            className="text-sm font-mono"
            style={{ color: '#0A0A0A' }}
          >
            {severity.protocol}
          </div>
        </div>

        {/* Status */}
        <div className="border-t-2 pt-4 mb-6" style={{ borderColor: '#E5E5DF' }}>
          <div
            className="text-xs uppercase font-bold tracking-widest mb-1"
            style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Status
          </div>
          <div
            className="text-sm font-mono uppercase font-bold"
            style={{ color: tier === 'paid' ? '#15803D' : '#B45309' }}
          >
            {status} — {tier} tier
          </div>
        </div>

        {/* QR Code */}
        <div className="border-t-2 pt-6 flex justify-between items-center" style={{ borderColor: '#E5E5DF' }}>
          <div>
            <div
              className="text-xs uppercase font-bold tracking-widest mb-2"
              style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
            >
              Verification
            </div>
            <div
              className="text-xs font-mono break-all max-w-xs"
              style={{ color: '#525252' }}
            >
              {verificationUrl}
            </div>
          </div>
          <div className="border-2 p-2" style={{ borderColor: '#0A0A0A' }}>
            <QRCode value={verificationUrl} size={100} />
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-4 mb-6">
        <button
          onClick={handleShare}
          className="flex-1 py-3 font-bold uppercase text-sm border-2 transition-colors"
          style={{
            background: '#0A0A0A',
            color: '#F4F4F0',
            borderColor: '#0A0A0A',
            fontFamily: 'Chivo, sans-serif',
          }}
          data-testid="share-certificate-btn"
        >
          Share Certificate
        </button>
        <button
          onClick={() => setShowDelivery(!showDelivery)}
          className="flex-1 py-3 font-bold uppercase text-sm border-2 transition-colors"
          style={{
            background: 'transparent',
            color: '#0A0A0A',
            borderColor: '#0A0A0A',
            fontFamily: 'Chivo, sans-serif',
          }}
          data-testid="schedule-delivery-btn"
        >
          Schedule Delivery
        </button>
      </div>

      {/* Delivery Form */}
      {showDelivery && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="border-2 p-6"
          style={{
            background: '#FFFFFF',
            borderColor: '#0A0A0A',
          }}
        >
          <h3
            className="text-xl font-bold uppercase mb-4"
            style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
          >
            Schedule Email Delivery
          </h3>
          <DeliveryForm />
        </motion.div>
      )}

      {/* Footer */}
      <p
        className="text-xs text-center mt-8"
        style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
      >
        This certificate represents administrative absolution only.
        <br />
        Not legally binding. Emotional bureaucracy since 2026.
      </p>
    </motion.div>
  );
};

const DeliveryForm = () => {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [hours, setHours] = useState(24);
  const [submitted, setSubmitted] = useState(false);
  const { certificateUuid } = useRitualStore();

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/api/delivery/schedule`,
        {
          certificate_uuid: certificateUuid,
          recipient_email: email,
          message,
          delay_hours: hours,
        }
      );

      setSubmitted(true);
    } catch (error) {
      console.error('Failed to schedule delivery:', error);
      alert('Failed to schedule delivery. Please try again.');
    }
  };

  if (submitted) {
    return (
      <div
        className="text-center py-6 font-mono"
        style={{ color: '#15803D' }}
      >
        ✓ Delivery scheduled successfully!
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          className="text-xs uppercase font-bold tracking-widest mb-2 block"
          style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
        >
          Recipient Email
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full border-2 px-4 py-2 text-sm font-mono"
          style={{
            background: '#F4F4F0',
            borderColor: '#0A0A0A',
            color: '#0A0A0A',
          }}
          data-testid="delivery-email-input"
        />
      </div>

      <div>
        <label
          className="text-xs uppercase font-bold tracking-widest mb-2 block"
          style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
        >
          Delay (hours)
        </label>
        <input
          type="number"
          value={hours}
          onChange={(e) => setHours(parseInt(e.target.value))}
          min="1"
          max="168"
          required
          className="w-full border-2 px-4 py-2 text-sm font-mono"
          style={{
            background: '#F4F4F0',
            borderColor: '#0A0A0A',
            color: '#0A0A0A',
          }}
          data-testid="delivery-hours-input"
        />
      </div>

      <div>
        <label
          className="text-xs uppercase font-bold tracking-widest mb-2 block"
          style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
        >
          Optional Message
        </label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          className="w-full border-2 px-4 py-2 text-sm font-mono resize-none"
          style={{
            background: '#F4F4F0',
            borderColor: '#0A0A0A',
            color: '#0A0A0A',
          }}
          data-testid="delivery-message-input"
        />
      </div>

      <button
        type="submit"
        className="w-full py-3 font-bold uppercase text-sm border-2 transition-colors"
        style={{
          background: '#0A0A0A',
          color: '#F4F4F0',
          borderColor: '#0A0A0A',
          fontFamily: 'Chivo, sans-serif',
        }}
        data-testid="submit-delivery-btn"
      >
        Schedule Delivery
      </button>
    </form>
  );
};

export default CertificateView;