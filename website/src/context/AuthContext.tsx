import React, { createContext, useContext, useEffect, useState } from "react";
import { DemoUser, RoleType, User } from "../types/auth";
import {
  getDemoUsersApi,
  getMeApi,
  getStoredToken,
  loginApi,
  registerApi,
  setStoredToken,
} from "../services/api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  demoUsers: DemoUser[];
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string, role?: RoleType) => Promise<void>;
  logout: () => void;
  loginAsDemo: (role: RoleType) => Promise<void>;
  hasRole: (allowedRoles: RoleType[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [demoUsers, setDemoUsers] = useState<DemoUser[]>([]);

  // Fetch demo accounts for fast UI testing
  useEffect(() => {
    getDemoUsersApi()
      .then((demos) => setDemoUsers(demos))
      .catch((err) => console.warn("Failed to load demo accounts:", err));
  }, []);

  // Check stored token and restore session
  useEffect(() => {
    const initAuth = async () => {
      const stored = getStoredToken();
      if (!stored) {
        setIsLoading(false);
        return;
      }

      try {
        const currentUser = await getMeApi();
        setUser(currentUser);
        setToken(stored);
      } catch (err) {
        console.warn("Session expired or invalid token:", err);
        setStoredToken(null);
        setToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const resp = await loginApi(email, password);
      setStoredToken(resp.access_token);
      setToken(resp.access_token);
      setUser(resp.user);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (
    email: string,
    name: string,
    password: string,
    role: RoleType = "researcher"
  ) => {
    setIsLoading(true);
    try {
      const resp = await registerApi(email, name, password, role);
      setStoredToken(resp.access_token);
      setToken(resp.access_token);
      setUser(resp.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setStoredToken(null);
    setToken(null);
    setUser(null);
  };

  const loginAsDemo = async (targetRole: RoleType) => {
    const demo = demoUsers.find((d) => d.role === targetRole);
    if (!demo) {
      throw new Error(`Demo account for role '${targetRole}' not available.`);
    }
    await login(demo.email, demo.password);
  };

  const hasRole = (allowedRoles: RoleType[]): boolean => {
    if (!user) return false;
    return allowedRoles.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        demoUsers,
        login,
        register,
        logout,
        loginAsDemo,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
