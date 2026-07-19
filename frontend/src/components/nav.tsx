"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, MessageSquare, Shield } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { canAccessAdmin } from "@/lib/types";
import { cn } from "@/lib/utils";

export function AppNav() {
  const pathname = usePathname();
  const { user, logout, loading } = useAuth();
  const showAdmin = canAccessAdmin(user?.role);

  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between gap-4 px-4">
        <div className="flex items-center gap-6">
          <Link href="/" className="font-semibold tracking-tight">
            Enterprise RAG
          </Link>
          {user && (
            <nav className="flex items-center gap-1 text-sm">
              <Link
                href="/"
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 hover:bg-muted",
                  pathname === "/" && "bg-muted font-medium",
                )}
              >
                <MessageSquare className="h-4 w-4" aria-hidden />
                Chat
              </Link>
              {showAdmin && (
                <Link
                  href="/admin"
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 hover:bg-muted",
                    pathname?.startsWith("/admin") && "bg-muted font-medium",
                  )}
                >
                  <Shield className="h-4 w-4" aria-hidden />
                  Admin
                </Link>
              )}
            </nav>
          )}
        </div>
        <div className="flex items-center gap-3 text-sm">
          {loading ? (
            <span className="text-muted-foreground">…</span>
          ) : user ? (
            <>
              <div className="hidden text-right sm:block">
                <div className="font-medium leading-tight">{user.name}</div>
                <div className="text-xs text-muted-foreground">
                  {user.email} · {user.role}
                </div>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={logout}
                aria-label="Sign out"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Sign out</span>
              </Button>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-md bg-primary px-3 py-1.5 text-primary-foreground"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
