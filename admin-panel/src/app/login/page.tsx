"use client";

import { useState } from "react";
import Image from "next/image";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Loader2 } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al iniciar sesión");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg-dark p-4">
      {/* Subtle radial primary glow */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#3BAA8C] opacity-5 blur-3xl" />
      </div>

      <Card className="relative w-full max-w-md border-border-dark bg-bg-dark-2 text-text-light">
        <CardHeader className="space-y-1 text-center">
          <div className="mx-auto mb-4">
            <Image
              src="/logo-full-white.png"
              width={180}
              height={60}
              alt="Zanovix"
              className="object-contain"
            />
          </div>
          <CardTitle className="font-display text-2xl font-bold tracking-tight">
            Bienvenido
          </CardTitle>
          <CardDescription className="text-text-muted">
            Accede al panel de gestión de Zanovix CRM
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="text-text-light">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="admin@zanovix.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                disabled={isLoading}
                className="border-border-dark bg-bg-dark text-text-light placeholder:text-text-muted"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-text-light">
                Contraseña
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="********"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                className="border-border-dark bg-bg-dark text-text-light placeholder:text-text-muted"
              />
            </div>

            <Button
              type="submit"
              className="w-full transition-shadow hover:shadow-[0_0_30px_rgba(59,170,140,0.3)]"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Iniciando sesión...
                </>
              ) : (
                "Iniciar sesión"
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
