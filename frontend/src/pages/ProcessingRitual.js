import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import useRitualStore from '../store/ritualStore';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const scanPhrases = [
  'Scanning interpersonal residue...',
  'Cross-referencing emotional records...',
  'Consulting accountability archive...',
  'Balancing karmic inconsistencies...',
];

const diagnosticPhrases = [
  'Passive aggression residue detected.',
  'Unread emotional debt identified.',
  'Interpersonal friction coefficient elevated.',
  'Social contract violation logged.',
];

const fakeWarning = {
  warning: 'Warning...',
  resolution: 'False alarm.',
};

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const ProcessingRitual = () => {
  const [currentText, setCurrentText] = useState('');
  const [showWarning, setShowWarning] = useState(false);
  const [progress, setProgress] = useState(0);
  const { confession, setSeverity, setStep } = useRitualStore();

  useEffect(() => {
    const runSequence = async () => {
      // Phase 1: Scanning (4 phrases, ~800ms each)
      for (let i = 0; i < scanPhrases.length; i++) {
        setCurrentText(scanPhrases[i]);
        setProgress((i + 1) * 20);
        await delay(800 + Math.random() * 400);
      }

      // Phase 2: Fake warning
      setShowWarning(true);
      setCurrentText(fakeWarning.warning);
      setProgress(85);
      await delay(1500);
      setShowWarning(false);
      setCurrentText(fakeWarning.resolution);
      await delay(1000);

      // Phase 3: Diagnostic
      const diagnostic =
        diagnosticPhrases[Math.floor(Math.random() * diagnosticPhrases.length)];
      setCurrentText(diagnostic);
      setProgress(95);
      await delay(1200);

      // Phase 4: Analyze with backend
      try {
        const response = await axios.post(`${API}/analyze`, {
          confession,
        });
        setSeverity(response.data);
        setProgress(100);
        await delay(500);
        setStep('severity');
      } catch (error) {
        console.error('Analysis failed:', error);
        setCurrentText('Error: Analysis failed. Please try again.');
      }
    };

    runSequence();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="max-w-md w-full text-center p-8"
      data-testid="processing-ritual"
    >
      {/* Spinner */}
      <div className="mb-8">
        <div
          className="w-16 h-16 border-2 rounded-full animate-spin mx-auto mb-6"
          style={{
            borderColor: '#737373',
            borderTopColor: '#0A0A0A',
          }}
        />
      </div>

      {/* Text */}
      <AnimatePresence mode="wait">
        <motion.p
          key={currentText}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="text-base font-mono mb-8 min-h-[60px] flex items-center justify-center"
          style={{
            color: showWarning ? '#D92D20' : '#0A0A0A',
            fontWeight: showWarning ? 'bold' : 'normal',
          }}
        >
          {currentText}
        </motion.p>
      </AnimatePresence>

      {/* Progress bar */}
      <div
        className="h-0.5 rounded overflow-hidden"
        style={{ background: '#E5E5DF' }}
      >
        <motion.div
          className="h-full"
          style={{ background: '#0A0A0A' }}
          initial={{ width: '0%' }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>

      <p
        className="text-xs font-mono mt-2"
        style={{ color: '#737373' }}
      >
        {progress}% complete
      </p>
    </motion.div>
  );
};

export default ProcessingRitual;