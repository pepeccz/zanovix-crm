"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import type { AdminRole, CurrentUser } from "@/lib/types";

interface User {
  id: string;
  email: string;
  display_name: string | null;
  role: AdminRole;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  hasRole: (role: AdminRole) => boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const checkAuth = useCallback(async () => {
    try {
      const userData: CurrentUser = await api.getMe();
      setUser({
        id: userData.id,
        email: userData.email,
        display_name: userData.display_name,
        role: userData.role,
      });
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email: string, password: string) => {
    await api.login(email, password);
    const userData: CurrentUser = await api.getMe();
    setUser({
      id: userData.id,
      email: userData.email,
      display_name: userData.display_name,
      role: userData.role,
    });
    const returnTo = sessionStorage.getItem("returnTo");
    sessionStorage.removeItem("returnTo");
    router.push(returnTo || "/dashboard");
  };

  const logout = () => {
    api.logout();
    setUser(null);
    router.push("/login");
  };

  const hasRole = useCallback(
    (role: AdminRole): boolean => {
      return user?.role === role;
    },
    [user]
  );

  const isAdmin = user?.role === "admin";

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        isAdmin,
        hasRole,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
