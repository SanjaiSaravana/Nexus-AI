import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User, TokenResponse } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, username?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('nexus_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const setAuthData = (data: TokenResponse) => {
    localStorage.setItem('nexus_token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
  };

  const logout = () => {
    localStorage.removeItem('nexus_token');
    setToken(null);
    setUser(null);
    window.history.pushState({}, '', '/login');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };

  const refreshUser = async () => {
    try {
      const currentUser = await api.users.getMe();
      setUser(currentUser);
    } catch (err) {
      console.error('Failed to refresh user profile:', err);
      logout();
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('nexus_token');
      if (storedToken) {
        try {
          const currentUser = await api.users.getMe();
          setUser(currentUser);
        } catch {
          localStorage.removeItem('nexus_token');
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const data = await api.auth.login({ email, password });
    setAuthData(data);
  };

  const register = async (email: string, password: string, username?: string) => {
    const data = await api.auth.register({ email, password, username });
    setAuthData(data);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
