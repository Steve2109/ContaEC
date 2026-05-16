import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: number;
  email: string;
  full_name?: string;
  is_admin?: boolean;
  language?: string;
  license_expiry?: string;
  license_type?: string;
}

interface StoreState {
  // Auth
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;

  // UI
  darkMode: boolean;
  language: string;

  // Data
  currentCompanyId: number | null;

  // Actions
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setLoading: (loading: boolean) => void;
  toggleDarkMode: () => void;
  setLanguage: (lang: string) => void;
  setCurrentCompany: (id: number | null) => void;
  logout: () => void;
}

export const useStore = create<StoreState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      loading: true,
      darkMode: false,
      language: 'es-EC',
      currentCompanyId: null,

      setUser: (user) => set({ user, isAuthenticated: !!user, loading: false }),
      setToken: (token) => set({ token, isAuthenticated: !!token }),
      setLoading: (loading) => set({ loading }),

      toggleDarkMode: () => set((state) => {
        const newMode = !state.darkMode;
        if (newMode) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
        return { darkMode: newMode };
      }),

      setLanguage: (lang) => {
        set({ language: lang });
      },

      setCurrentCompany: (id) => set({ currentCompanyId: id }),

      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({ user: null, token: null, isAuthenticated: false, currentCompanyId: null });
        window.location.href = '/login';
      },
    }),
    {
      name: 'contaec-storage',
      partialize: (state) => ({
        darkMode: state.darkMode,
        language: state.language,
        currentCompanyId: state.currentCompanyId,
      }),
    }
  )
);
