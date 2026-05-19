import { create } from 'zustand';

const useRitualStore = create((set) => ({
  // Current step
  step: 'landing',
  
  // User data
  name: null,
  isAnonymous: false,
  
  // Confession
  confession: '',
  
  // Severity analysis result
  severity: null,
  
  // Certificate data
  certificateUuid: null,
  registryId: null,
  tier: 'free',
  status: 'temporary',
  
  // Payment
  paymentAmount: 0,
  
  // Actions
  setStep: (step) => set({ step }),
  
  setName: (name) => set({ name, isAnonymous: false }),
  
  setAnonymous: () => set({ name: null, isAnonymous: true }),
  
  setConfession: (confession) => set({ confession }),
  
  setSeverity: (severity) => set({ severity }),
  
  setCertificate: (uuid, registryId, tier, status) => set({
    certificateUuid: uuid,
    registryId,
    tier,
    status,
  }),
  
  setTier: (tier) => set({ tier }),
  
  setPaymentAmount: (amount) => set({ paymentAmount: amount }),
  
  reset: () => set({
    step: 'landing',
    name: null,
    isAnonymous: false,
    confession: '',
    severity: null,
    certificateUuid: null,
    registryId: null,
    tier: 'free',
    status: 'temporary',
    paymentAmount: 0,
  }),
}));

export default useRitualStore;