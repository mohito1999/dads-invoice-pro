// src/contexts/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { UserProfile } from '@/types';
// We'll define User type based on our backend's UserOut schema later
// For now, a simple user object or any.
// import { User } from '@/types'; // Example, if you create a types file

interface AuthContextType {
  isAuthenticated: boolean;
  user: UserProfile | null; // Replace 'any' with a proper User type later
  token: string | null;
  login: (token: string, userData: any) => void; // userData can be more specific
  logout: () => void;
  isLoading: boolean; // To handle initial auth check
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<UserProfile | null>(null); // Replace 'any'
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true); // Start as true

  useEffect(() => {
    // Check for token in localStorage on initial load
    const storedToken = localStorage.getItem('accessToken');
    const storedUser = localStorage.getItem('userData'); // We'll store user data too
    
    if (storedToken) {
      setToken(storedToken);
      // You might want to verify the token with the backend here
      // or fetch user data based on the token if only token is stored.
      // For simplicity now, if token exists, we assume it's valid initially.
      // A better approach is to have a /users/me endpoint that validates the token
      // and returns user data.
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch (e) {
          console.error("Failed to parse stored user data", e);
          localStorage.removeItem('userData'); // Clear corrupted data
        }
      }
      setIsAuthenticated(true);
    }
    setIsLoading(false); // Finished initial check
  }, []);

  const login = (newToken: string, userData: UserProfile) => { // userData should be typed
    localStorage.setItem('accessToken', newToken);
    localStorage.setItem('userData', JSON.stringify(userData)); // Store user data
    setToken(newToken);
    setUser(userData);
    setIsAuthenticated(true);
  };

  const logout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('userData');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    // Optionally redirect to login page using useNavigate from react-router-dom
    // const navigate = useNavigate(); navigate('/login'); (but can't use hook here directly)
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};