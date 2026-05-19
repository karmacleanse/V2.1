import { motion } from 'framer-motion';
import useRitualStore from '../store/ritualStore';
import LiveCounter from '../components/LiveCounter';

const Landing = () => {
  const setStep = useRitualStore((state) => state.setStep);

  return (
    <main
      className="min-h-screen flex flex-col items-center justify-center px-4"
      style={{ background: '#F4F4F0' }}
      data-testid="landing-page"
    >
      {/* Ministry Seal */}
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="mb-8"
      >
        <img
          src="https://static.prod-images.emergentagent.com/jobs/ffea1c83-c6cc-46b9-b35f-810f49dbc24e/images/7c21a7f1a11372181bf010fe1e96f49aaffa8a407a0bc1c67d9e00400f23885a.png"
          alt="Ministry Seal"
          className="w-24 h-24 md:w-32 md:h-32"
        />
      </motion.div>

      {/* Title */}
      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="text-4xl sm:text-5xl lg:text-6xl font-black uppercase tracking-tighter text-center mb-4"
        style={{ fontFamily: 'Chivo, sans-serif', color: '#0A0A0A' }}
      >
        Karma Cleanse
      </motion.h1>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="text-xs uppercase font-bold tracking-widest mb-2"
        style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
      >
        v2.1
      </motion.div>

      {/* Subtitle */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="text-sm md:text-base mb-12 text-center max-w-md"
        style={{ color: '#525252', fontFamily: 'IBM Plex Mono, monospace' }}
      >
        Emotional Bureaucracy & Administrative Absolution
      </motion.p>

      {/* CTA Button */}
      <motion.button
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setStep('identity')}
        className="px-10 py-4 text-base font-bold uppercase tracking-wide border-2"
        style={{
          background: '#0A0A0A',
          color: '#F4F4F0',
          borderColor: '#0A0A0A',
          fontFamily: 'Chivo, sans-serif',
        }}
        data-testid="begin-cleansing-btn"
      >
        Begin Karma Cleansing
      </motion.button>

      {/* Live Counter */}
      <LiveCounter />

      {/* Disclaimer */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
        className="absolute bottom-6 text-xs text-center px-4"
        style={{ color: '#737373', fontFamily: 'IBM Plex Mono, monospace' }}
      >
        Karma Cleanse is not legally recognized in most jurisdictions.
      </motion.p>
    </main>
  );
};

export default Landing;