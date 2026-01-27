import { create } from 'zustand';
import type { UIQuestion } from '@/types';

interface QuestionState {
  // State
  isOpen: boolean;
  questionId: string | null;
  questions: UIQuestion[];
  timeoutSeconds: number;
  remainingSeconds: number;
  answers: Record<string, string | string[]>;  // question text -> answer(s)

  // Actions
  openModal: (questionId: string, questions: UIQuestion[], timeout: number) => void;
  closeModal: () => void;
  setAnswer: (question: string, answer: string | string[]) => void;
  tick: () => void;  // Called every second to update countdown
  reset: () => void;
}

export const useQuestionStore = create<QuestionState>((set, get) => ({
  isOpen: false,
  questionId: null,
  questions: [],
  timeoutSeconds: 60,
  remainingSeconds: 60,
  answers: {},

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
    questionId: null,
    questions: [],
    answers: {},
  }),

  setAnswer: (question, answer) => set(state => ({
    answers: { ...state.answers, [question]: answer }
  })),

  tick: () => set(state => ({
    remainingSeconds: Math.max(0, state.remainingSeconds - 1)
  })),

  reset: () => set({
    isOpen: false,
    questionId: null,
    questions: [],
    timeoutSeconds: 60,
    remainingSeconds: 60,
    answers: {},
  }),
}));
