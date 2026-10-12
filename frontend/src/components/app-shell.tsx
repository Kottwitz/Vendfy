"use client";

import {
  ArrowDownLeft,
  Bell,
  ChevronDown,
  CircleHelp,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  UsersRound,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { User } from "@/lib/types";

const navigation = [
  { href: "/", label: "Visão geral", icon: LayoutDashboard },
  { href: "/clients", label: "Clientes", icon: UsersRound },
  { href: "/quotes", label: "Orçamentos", icon: FileText },
];

function initials(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    let active = true;
    fetch("/api/backend/users/me", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) {
          router.replace("/login");
          return;
        }
        const currentUser = (await response.json()) as User;
        if (active) setUser(currentUser);
      })
      .catch(() => router.replace("/login"))
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router]);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  if (loading || !user) {
    return (
      <main className="grid min-h-screen place-items-center">
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-teal-600" />
          Preparando seu espaço de trabalho
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-screen lg:flex">
      {menuOpen && (
        <button
          className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden"
          aria-label="Fechar menu"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[264px] flex-col bg-[var(--navy-deep)] text-white transition-transform lg:translate-x-0 ${
          menuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-[78px] items-center justify-between border-b border-white/10 px-6">
          <Link href="/" className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-teal-500 text-sm font-black text-white">
              V
            </span>
            <span className="text-[19px] font-bold tracking-tight">vendfy</span>
          </Link>
          <button
            className="rounded-lg p-2 text-white/60 hover:bg-white/10 lg:hidden"
            aria-label="Fechar menu"
            onClick={() => setMenuOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-4 pt-7">
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
            Workspace
          </p>
          <nav className="space-y-1">
            {navigation.map(({ href, label, icon: Icon }) => {
              const active =
                href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMenuOpen(false)}
                  className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition ${
                    active
                      ? "bg-white/10 text-white shadow-sm"
                      : "text-slate-400 hover:bg-white/[0.06] hover:text-white"
                  }`}
                >
                  <Icon
                    size={17}
                    className={active ? "text-teal-300" : "text-slate-500 group-hover:text-slate-300"}
                  />
                  {label}
                  {label === "Orçamentos" && (
                    <span className="ml-auto rounded-md bg-white/10 px-1.5 py-0.5 text-[10px] text-slate-300">
                      CRM
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="mt-auto p-4">
          <div className="mb-3 rounded-2xl border border-white/10 bg-white/[0.045] p-4">
            <div className="mb-3 flex items-center gap-2 text-teal-300">
              <CircleHelp size={15} />
              <span className="text-xs font-semibold text-white">Precisa de ajuda?</span>
            </div>
            <p className="mb-3 text-[11px] leading-5 text-slate-400">
              Organize sua operação comercial com mais clareza.
            </p>
            <span className="text-[11px] font-semibold text-teal-300">
              Central de suporte <ArrowDownLeft className="ml-1 inline" size={12} />
            </span>
          </div>
          <div className="flex items-center gap-3 rounded-xl px-2 py-2">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-teal-700 text-xs font-bold">
              {initials(user.name)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold">{user.name}</p>
              <p className="truncate text-[10px] text-slate-400">{user.email}</p>
            </div>
            <button
              onClick={logout}
              title="Sair"
              className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white"
              aria-label="Sair da conta"
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      <div className="min-h-screen min-w-0 flex-1 lg:ml-[264px]">
        <header className="sticky top-0 z-30 flex h-[78px] items-center justify-between border-b border-[var(--line)] bg-white/90 px-5 backdrop-blur-md sm:px-8">
          <div className="flex items-center gap-3">
            <button
              className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
              onClick={() => setMenuOpen(true)}
              aria-label="Abrir menu"
            >
              <Menu size={20} />
            </button>
            <div className="hidden items-center gap-2 text-xs text-slate-400 sm:flex">
              Vendfy <span className="text-slate-300">/</span>
              <span className="font-semibold text-slate-700">
                {navigation.find((item) =>
                  item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
                )?.label ?? "Configurações"}
              </span>
            </div>
            <span className="font-bold tracking-tight text-[var(--navy)] sm:hidden">
              vendfy
            </span>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <span className="hidden rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1.5 text-[11px] font-semibold text-emerald-700 md:inline-flex">
              <span className="mr-2 mt-1 h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Plano gratuito
            </span>
            <button
              className="relative rounded-xl p-2.5 text-slate-500 hover:bg-slate-100"
              aria-label="Notificações"
            >
              <Bell size={18} />
              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-rose-500 ring-2 ring-white" />
            </button>
            <Link
              href="/settings"
              aria-label="Configurações"
              className="rounded-xl p-2.5 text-slate-500 hover:bg-slate-100"
            >
              <Settings size={18} />
            </Link>
            <div className="hidden h-8 w-px bg-slate-200 sm:block" />
            <button className="hidden items-center gap-2 sm:flex">
              <span className="grid h-8 w-8 place-items-center rounded-full bg-[#dcebe8] text-[11px] font-bold text-teal-800">
                {initials(user.name)}
              </span>
              <ChevronDown size={14} className="text-slate-400" />
            </button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1440px] px-5 py-7 sm:px-8 sm:py-9">
          {children}
        </main>
      </div>
    </div>
  );
}
