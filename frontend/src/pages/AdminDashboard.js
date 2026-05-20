import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Card = ({ label, value, sub, accent }) => (
  <div
    className="border-2 p-4"
    style={{ background: '#FFFFFF', borderColor: '#0A0A0A' }}
  >
    <div
      className="text-xs uppercase font-bold tracking-widest mb-2"
      style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
    >
      {label}
    </div>
    <div
      className="text-3xl font-black tracking-tight"
      style={{
        fontFamily: 'Chivo, sans-serif',
        color: accent || '#0A0A0A',
      }}
    >
      {value}
    </div>
    {sub && (
      <div
        className="text-xs font-mono mt-1"
        style={{ color: '#737373' }}
      >
        {sub}
      </div>
    )}
  </div>
);

const SectionTitle = ({ children }) => (
  <h2
    className="text-xs uppercase font-bold tracking-widest mb-3 mt-8"
    style={{ color: '#525252', fontFamily: 'IBM Plex Mono, monospace' }}
  >
    {children}
  </h2>
);

const SEVERITY_COLOR = {
  Low: '#15803D',
  Moderate: '#525252',
  High: '#B45309',
  Critical: '#D92D20',
  Compliance: '#15803D',
};

const AdminDashboard = () => {
  const [searchParams] = useSearchParams();
  const key = searchParams.get('key');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    if (!key) {
      setError('Missing ?key= parameter');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API}/admin/stats`, { params: { key } });
      setData(res.data);
    } catch (e) {
      console.error(e);
      setError(e.response?.data?.detail || 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000); // refresh every 30s
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  if (loading && !data) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: '#F4F4F0' }}
      >
        <div
          className="text-xs font-mono uppercase tracking-widest animate-pulse"
          style={{ color: '#737373' }}
        >
          Loading registry data...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="min-h-screen flex items-center justify-center px-4"
        style={{ background: '#F4F4F0' }}
      >
        <div
          className="max-w-md border-2 p-8 text-center"
          style={{ background: '#FFFFFF', borderColor: '#D92D20' }}
        >
          <div
            className="text-xs uppercase font-bold tracking-widest mb-2"
            style={{ color: '#D92D20', fontFamily: 'IBM Plex Mono, monospace' }}
          >
            Access Denied
          </div>
          <p className="text-sm font-mono mb-4">{error}</p>
          <p className="text-xs font-mono" style={{ color: '#737373' }}>
            Append <code>?key=YOUR_ADMIN_KEY</code> to the URL.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen px-4 py-8"
      style={{ background: '#F4F4F0' }}
      data-testid="admin-dashboard"
    >
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div
          className="mb-8 pb-4 flex items-center justify-between"
          style={{ borderBottom: '2px solid #0A0A0A' }}
        >
          <div>
            <h1
              className="text-3xl sm:text-4xl font-black uppercase tracking-tight"
              style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
            >
              Registry Console
            </h1>
            <div
              className="text-xs uppercase tracking-widest mt-1"
              style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
            >
              Karma Cleanse · Internal Dashboard · Auto-refresh 30s
            </div>
          </div>
          <Link
            to="/"
            className="text-xs uppercase font-bold tracking-widest hover:underline"
            style={{ color: '#0A0A0A', fontFamily: 'IBM Plex Mono, monospace' }}
            data-testid="admin-back-link"
          >
            ← App
          </Link>
        </div>

        {/* Overview */}
        <SectionTitle>Overview</SectionTitle>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card
            label="Total Certificates"
            value={data.overview.total_certificates}
            sub={`+${data.overview.last_24h} in last 24h`}
          />
          <Card
            label="Paid"
            value={data.overview.paid_certificates}
            sub={`${data.overview.conversion_rate}% conversion`}
            accent="#15803D"
          />
          <Card
            label="Free (temp)"
            value={data.overview.free_certificates}
            sub="Active free-tier"
          />
          <Card
            label="Compliance Receipts"
            value={data.overview.compliance_receipts}
            sub="T&C acknowledgments"
          />
        </div>

        {/* Revenue */}
        <SectionTitle>Revenue</SectionTitle>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card
            label="Total Revenue USD"
            value={`$${data.revenue.total_usd}`}
            sub={`${data.payments.completed} completed payments`}
            accent="#15803D"
          />
          <Card
            label="Pending Payments"
            value={data.payments.pending}
            sub="Awaiting webhook"
            accent={data.payments.pending > 0 ? '#B45309' : '#0A0A0A'}
          />
          <Card
            label="Last 7 Days"
            value={data.overview.last_7d}
            sub="New certificates"
          />
        </div>
        {data.revenue.by_method.length > 0 && (
          <div
            className="border-2 p-4 mt-4"
            style={{ background: '#FFFFFF', borderColor: '#0A0A0A' }}
          >
            <div
              className="text-xs uppercase font-bold tracking-widest mb-3"
              style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
            >
              Revenue by Payment Method
            </div>
            <table className="w-full text-sm font-mono">
              <thead>
                <tr style={{ borderBottom: '1px solid #E5E5DF' }}>
                  <th className="text-left py-2" style={{ color: '#737373' }}>
                    Method
                  </th>
                  <th className="text-right py-2" style={{ color: '#737373' }}>
                    Count
                  </th>
                  <th className="text-right py-2" style={{ color: '#737373' }}>
                    Revenue
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.revenue.by_method.map((r, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #F4F4F0' }}>
                    <td className="py-2">{r.method}</td>
                    <td className="py-2 text-right">{r.count}</td>
                    <td
                      className="py-2 text-right font-bold"
                      style={{ color: '#15803D' }}
                    >
                      ${r.revenue}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Severity */}
        <SectionTitle>Severity Distribution</SectionTitle>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {['Low', 'Moderate', 'High', 'Critical'].map((sev) => (
            <Card
              key={sev}
              label={`Class ${sev}`}
              value={data.severity_distribution[sev] || 0}
              accent={SEVERITY_COLOR[sev]}
            />
          ))}
        </div>

        {/* Emails */}
        <SectionTitle>Email Delivery</SectionTitle>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card
            label="Scheduled"
            value={data.emails.scheduled}
            sub="All delivery records"
          />
          <Card
            label="Sent"
            value={data.emails.sent}
            sub="Successfully dispatched"
            accent="#15803D"
          />
          <Card
            label="Pending"
            value={data.emails.pending}
            sub="Awaiting send_at"
          />
          <Card
            label="Failed"
            value={data.emails.failed}
            sub="After max retries"
            accent={data.emails.failed > 0 ? '#D92D20' : '#0A0A0A'}
          />
        </div>
        {Object.keys(data.emails.events).length > 0 && (
          <div
            className="border-2 p-4 mt-4"
            style={{ background: '#FFFFFF', borderColor: '#0A0A0A' }}
          >
            <div
              className="text-xs uppercase font-bold tracking-widest mb-3"
              style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
            >
              Resend Webhook Events
            </div>
            <div className="flex flex-wrap gap-4 text-sm font-mono">
              {Object.entries(data.emails.events).map(([evt, count]) => (
                <div key={evt}>
                  <span style={{ color: '#737373' }}>{evt}:</span>{' '}
                  <span className="font-bold">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Activity */}
        <SectionTitle>Recent Activity (Last 10)</SectionTitle>
        <div
          className="border-2 overflow-x-auto"
          style={{ background: '#FFFFFF', borderColor: '#0A0A0A' }}
        >
          <table className="w-full text-xs font-mono">
            <thead>
              <tr style={{ borderBottom: '2px solid #0A0A0A', background: '#F4F4F0' }}>
                <th className="text-left p-3 uppercase" style={{ color: '#737373' }}>
                  Time
                </th>
                <th className="text-left p-3 uppercase" style={{ color: '#737373' }}>
                  Registry ID
                </th>
                <th className="text-left p-3 uppercase" style={{ color: '#737373' }}>
                  Name
                </th>
                <th className="text-left p-3 uppercase" style={{ color: '#737373' }}>
                  Class
                </th>
                <th className="text-left p-3 uppercase" style={{ color: '#737373' }}>
                  Tier
                </th>
                <th className="text-right p-3 uppercase" style={{ color: '#737373' }}>
                  $
                </th>
              </tr>
            </thead>
            <tbody>
              {data.recent_activity.map((c, i) => (
                <tr
                  key={i}
                  style={{ borderBottom: '1px solid #F4F4F0' }}
                  data-testid={`recent-row-${i}`}
                >
                  <td className="p-3" style={{ color: '#525252' }}>
                    {new Date(c.created_at).toLocaleString('ru-RU', {
                      day: '2-digit',
                      month: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </td>
                  <td className="p-3 font-bold">
                    <Link
                      to={`/verify/${c.registry_id}`}
                      target="_blank"
                      className="hover:underline"
                      style={{ color: '#0A0A0A' }}
                    >
                      {c.registry_id}
                    </Link>
                  </td>
                  <td className="p-3" style={{ color: '#525252' }}>
                    {c.name || 'Anonymous'}
                  </td>
                  <td
                    className="p-3 font-bold"
                    style={{
                      color: SEVERITY_COLOR[c.severity_class] || '#0A0A0A',
                    }}
                  >
                    {c.severity_class}
                  </td>
                  <td
                    className="p-3 uppercase font-bold"
                    style={{
                      color: c.tier === 'paid' ? '#15803D' : '#737373',
                    }}
                  >
                    {c.tier}
                  </td>
                  <td className="p-3 text-right" style={{ color: '#525252' }}>
                    {c.payment_amount ? `$${c.payment_amount}` : '—'}
                  </td>
                </tr>
              ))}
              {data.recent_activity.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-6 text-center" style={{ color: '#737373' }}>
                    No certificates yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div
          className="text-xs font-mono text-center mt-8 pt-4"
          style={{
            color: '#737373',
            borderTop: '1px solid #E5E5DF',
          }}
        >
          Generated at {new Date(data.generated_at).toLocaleString()}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
