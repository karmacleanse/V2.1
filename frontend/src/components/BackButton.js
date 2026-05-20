import useRitualStore from '../store/ritualStore';

/**
 * Bureaucratic back button — small, top-left, always present on funnel steps.
 * Props: to (step name to navigate to)
 */
const BackButton = ({ to = 'landing', label = '← Back' }) => {
  const setStep = useRitualStore((state) => state.setStep);
  return (
    <button
      onClick={() => setStep(to)}
      className="text-xs uppercase tracking-widest font-bold hover:underline transition-opacity"
      style={{
        color: '#525252',
        fontFamily: 'IBM Plex Mono, monospace',
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
      }}
      data-testid={`back-to-${to}-btn`}
    >
      {label}
    </button>
  );
};

export default BackButton;
