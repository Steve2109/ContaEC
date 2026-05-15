import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, Company, License } from '../types';

interface AppState {
  user: User | null;
  token: string | null;
  companies: Company[];
  currentCompany: Company | null;
  license: License | null;
  isDarkMode: boolean;
  language: 'es-EC' | 'en' | 'pt';
  
  // Actions
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setCompanies: (companies: Company[]) => void;
  setCurrentCompany: (company: Company | null) => void;
  setLicense: (license: License | null) => void;
  toggleDarkMode: () => void;
  setLanguage: (lang: 'es-EC' | 'en' | 'pt') => void;
  logout: () => void;
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      companies: [],
      currentCompany: null,
      license: null,
      isDarkMode: false,
      language: 'es-EC',

      setUser: (user) => set({ user }),
      setToken: (token) => {
        if (token) localStorage.setItem('token', token);
        else localStorage.removeItem('token');
        set({ token });
      },
      setCompanies: (companies) => set({ companies }),
      setCurrentCompany: (company) => set({ currentCompany: company }),
      setLicense: (license) => set({ license }),
      toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
      setLanguage: (language) => set({ language }),
      
      logout: () => {
        localStorage.removeItem('token');
        set({
          user: null,
          token: null,
          companies: [],
          currentCompany: null,
          license: null,
        });
      },
    }),
    {
      name: 'contaec-storage',
      partialize: (state) => ({
        isDarkMode: state.isDarkMode,
        language: state.language,
      }),
    }
  )
);
