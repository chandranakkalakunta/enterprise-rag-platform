"use client";

import type { ReactNode } from "react";

import { AppNav } from "@/components/nav";
import { ServiceWorkerRegister } from "@/components/service-worker-register";
import { VersionWatcher } from "@/components/version-watcher";
import { AuthProvider } from "@/lib/auth-context";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <ServiceWorkerRegister />
      <VersionWatcher />
      <div className="flex min-h-screen flex-col">
        <AppNav />
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">
          {children}
        </main>
        <footer className="border-t border-border py-3 text-center text-xs text-muted-foreground">
          Enterprise RAG Platform · answers require network · PWA shell only offline
        </footer>
      </div>
    </AuthProvider>
  );
}
