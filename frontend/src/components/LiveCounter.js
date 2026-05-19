import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const LiveCounter = () => {
  const [count, setCount] = useState(12482);

  useEffect(() => {
    const interval = setInterval(() => {
      const delay = 3000 + Math.random() * 5000;
      setTimeout(() => {
        setCount((c) => c + 1);
      }, delay);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.8 }}
      className="mt-8 text-[#737373] text-sm font-mono"
      data-testid="live-counter"
    >
      <AnimatePresence mode="popLayout">
        <motion.span
          key={count}
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -10, opacity: 0 }}
          className="inline-block font-mono font-bold"
        >
          {count.toLocaleString()}
        </motion.span>
      </AnimatePresence>
      {' '}unresolved incidents processed
    </motion.div>
  );
};

export default LiveCounter;