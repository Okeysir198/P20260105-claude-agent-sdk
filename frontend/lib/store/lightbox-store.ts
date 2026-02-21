import { create } from 'zustand';

interface LightboxState {
  isOpen: boolean;
  images: string[];
  currentIndex: number;
  open: (images: string[], startIndex?: number) => void;
  close: () => void;
  next: () => void;
  prev: () => void;
  goTo: (index: number) => void;
}

export const useLightboxStore = create<LightboxState>((set, get) => ({
  isOpen: false,
  images: [],
  currentIndex: 0,
  open: (images, startIndex = 0) =>
    set({ isOpen: true, images, currentIndex: startIndex }),
  close: () => set({ isOpen: false, images: [], currentIndex: 0 }),
  next: () => {
    const { currentIndex, images } = get();
    if (currentIndex < images.length - 1) {
      set({ currentIndex: currentIndex + 1 });
    }
  },
  prev: () => {
    const { currentIndex } = get();
    if (currentIndex > 0) {
      set({ currentIndex: currentIndex - 1 });
    }
  },
  goTo: (index) => {
    const { images } = get();
    if (index >= 0 && index < images.length) {
      set({ currentIndex: index });
    }
  },
}));
