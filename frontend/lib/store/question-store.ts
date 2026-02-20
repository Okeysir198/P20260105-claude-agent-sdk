import { create } from 'zustand';
import type { UIQuestion } from '@/types';

interface QuestionState {
  isOpen: boolean;
  questionId: string | null;
  questions: UIQuestion[];
  timeoutSeconds: number;
  remainingSeconds: number;
  answers: Record<string, string | string[]>;
  submittedAnswers: Record<string, Record<string, string | string[]>>;

  openModal: (questionId: string, questions: UIQuestion[], timeout: number) => void;
  closeModal: () => void;
  setAnswer: (question: string, answer: string | string[]) => void;
  tick: () => void;
  reset: () => void;
  submitAnswers: (questionId: string, answers: Record<string, string | string[]>) => void;
  getSubmittedAnswer: (questionId: string) => Record<string, string | string[]> | null;
}

export const useQuestionStore = create<QuestionState>((set, get) => ({
  isOpen: false,
  questionId: null,
  questions: [],
  timeoutSeconds: 60,
  remainingSeconds: 60,
  answers: {},
  submittedAnswers: {},

  openModal: (questionId, questions, timeout) => set({
    isOpen: true,
    questionId,
    questions,
    timeoutSeconds: timeout,
    remainingSeconds: timeout,
    answers: {},
  }),

  closeModal: () => set({
    isOpen: false,
    // Don't clear questionId, questions, or submittedAnswers - keep them for display
    answers: {},
  }),

  setAnswer: (question, answer) => set(state => ({
    answers: { ...state.answers, [question]: answer }
  })),

  tick: () => set(state => ({
    remainingSeconds: Math.max(0, state.remainingSeconds - 1)
  })),

  submitAnswers: (questionId, answers) => set(state => ({
    submittedAnswers: { ...state.submittedAnswers, [questionId]: answers }
  })),

  getSubmittedAnswer: (questionId) => {
    return get().submittedAnswers[questionId] || null;
  },

  reset: () => set({
    isOpen: false,
    questionId: null,
    questions: [],
    timeoutSeconds: 60,
    remainingSeconds: 60,
    answers: {},
  }),
}));
