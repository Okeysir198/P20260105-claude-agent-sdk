import { create } from 'zustand';

export interface UIPlanStep {
  description: string;
  status: 'pending' | 'in_progress' | 'completed';
}

interface PlanState {
  isOpen: boolean;
  planId: string | null;
  title: string;
  summary: string;
  steps: UIPlanStep[];
  timeoutSeconds: number;
  remainingSeconds: number;
  feedback: string;

  openModal: (planId: string, title: string, summary: string, steps: UIPlanStep[], timeout: number) => void;
  closeModal: () => void;
  setFeedback: (feedback: string) => void;
  tick: () => void;
  reset: () => void;
}

export const usePlanStore = create<PlanState>((set) => ({
  isOpen: false,
  planId: null,
  title: '',
  summary: '',
  steps: [],
  timeoutSeconds: 120,
  remainingSeconds: 120,
  feedback: '',

  openModal: (planId, title, summary, steps, timeout) => set({
    isOpen: true,
    planId,
    title,
    summary,
    steps,
    timeoutSeconds: timeout,
    remainingSeconds: timeout,
    feedback: '',
  }),

  closeModal: () => set({
    isOpen: false,
    planId: null,
    title: '',
    summary: '',
    steps: [],
    feedback: '',
  }),

  setFeedback: (feedback) => set({ feedback }),

  tick: () => set(state => ({
    remainingSeconds: Math.max(0, state.remainingSeconds - 1)
  })),

  reset: () => set({
    isOpen: false,
    planId: null,
    title: '',
    summary: '',
    steps: [],
    timeoutSeconds: 120,
    remainingSeconds: 120,
    feedback: '',
  }),
}));
