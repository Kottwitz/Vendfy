"use client";

import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

type FormMode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<FormMode>("login");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim().toLowerCase();
    const password = String(form.get("password") ?? "");

    try {
      if (mode === "register") {
        if (password !== String(form.get("confirm_password") ?? "")) {
          throw new Error("As senhas não coincidem.");
        }
        const registration = await fetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email,
            password,
          }),
        });
        if (!registration.ok) {
          const data = (await registration.json()) as { detail?: string };
          throw new Error(data.detail ?? "Não foi possível criar sua conta.");
        }
        setMode("login");
        setNotice("Conta criada com sucesso. Entre usando seu email e senha.");
        return;
      }

      const loginForm = new FormData();
      loginForm.set("email", email);
      loginForm.set("password", password);
      const login = await fetch("/api/auth/token", {
        method: "POST",
        body: loginForm,
      });
      if (!login.ok) {
        const data = (await login.json()) as { detail?: string };
        throw new Error(data.detail ?? "Não foi possível entrar.");
      }
      router.replace("/");
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-white lg:grid lg:grid-cols-[1.02fr_0.98fr]">
      <section className="relative hidden overflow-hidden bg-[var(--navy-deep)] px-12 py-10 text-white lg:flex lg:flex-col lg:justify-between xl:px-20">
        <div className="absolute -right-28 top-24 h-80 w-80 rounded-full border border-white/[0.07]" />
        <div className="absolute -right-16 top-36 h-56 w-56 rounded-full border border-white/[0.08]" />
        <div className="absolute -bottom-44 -left-28 h-96 w-96 rounded-full bg-teal-600/10 blur-2xl" />
        <Link href="/login" className="relative flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-teal-500 font-black">V</span>
          <span className="text-xl font-bold tracking-tight">vendfy</span>
        </Link>
        <div className="relative max-w-[510px] py-14">
          <span className="inline-flex items-center gap-2 rounded-full border border-teal-300/20 bg-teal-300/10 px-3 py-1.5 text-[11px] font-semibold text-teal-200">
            <Sparkles size={13} /> Gestão comercial sem complicação
          </span>
          <h1 className="mt-7 text-[42px] font-bold leading-[1.15] tracking-tight xl:text-[52px]">
            Seu próximo grande negócio começa com uma boa proposta.
          </h1>
          <p className="mt-5 max-w-md text-sm leading-7 text-slate-300">
            Centralize clientes e orçamentos, acompanhe cada oportunidade e mantenha sua operação em movimento.
          </p>
          <div className="mt-10 flex items-center gap-4 border-t border-white/10 pt-6">
            <div className="flex -space-x-2">
              {["A", "M", "C"].map((letter, index) => (
                <span key={letter} className={`grid h-8 w-8 place-items-center rounded-full border-2 border-[var(--navy-deep)] text-[10px] font-bold ${index === 0 ? "bg-[#dcebe8] text-teal-800" : index === 1 ? "bg-[#e9e2f5] text-violet-800" : "bg-[#f2e6d7] text-amber-800"}`}>{letter}</span>
              ))}
            </div>
            <p className="text-[11px] text-slate-400">Feito para equipes que constroem o futuro.</p>
          </div>
        </div>
        <p className="relative text-[10px] text-slate-500">© 2026 Vendfy · Gestão que acompanha seu ritmo.</p>
      </section>

      <section className="flex min-h-screen flex-col px-5 py-7 sm:px-10 lg:px-12 xl:px-20">
        <div className="flex items-center gap-2.5 lg:hidden">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-[var(--navy)] text-sm font-black text-white">V</span>
          <span className="text-lg font-bold tracking-tight text-[var(--navy)]">vendfy</span>
        </div>
        <div className="mx-auto flex w-full max-w-[420px] flex-1 flex-col justify-center py-12">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-teal-700">
            {mode === "login" ? "Bem-vindo de volta" : "Comece por aqui"}
          </p>
          <h2 className="mt-2 text-[28px] font-bold tracking-tight text-[var(--navy)]">
            {mode === "login" ? "Acesse sua conta" : "Crie seu espaço Vendfy"}
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            {mode === "login" ? "Entre para continuar cuidando do seu negócio." : "Crie sua conta e configure os dados da empresa depois."}
          </p>

          <div className="mt-8 grid grid-cols-2 rounded-xl bg-slate-100 p-1">
            <button onClick={() => { setMode("login"); setError(""); setNotice(""); }} className={`h-9 rounded-lg text-xs font-semibold transition ${mode === "login" ? "bg-white text-[var(--navy)] shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>Entrar</button>
            <button onClick={() => { setMode("register"); setError(""); setNotice(""); }} className={`h-9 rounded-lg text-xs font-semibold transition ${mode === "register" ? "bg-white text-[var(--navy)] shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>Criar conta</button>
          </div>

          {notice && <p role="status" className="mt-4 rounded-xl border border-teal-100 bg-teal-50 px-3.5 py-3 text-xs leading-5 text-teal-800">{notice}</p>}
          <form onSubmit={submit} className="mt-6 space-y-4">
            <AuthField label={mode === "register" ? "Email de acesso" : "Email"}>
              <span className="relative block"><Mail size={15} className="absolute left-3.5 top-3.5 text-slate-400" /><input required type="email" name="email" autoComplete="email" autoCapitalize="none" spellCheck={false} placeholder="voce@empresa.com" className={`${authInput} pl-10`} /></span>
            </AuthField>
            {mode === "register" && <p className="-mt-2 text-[11px] leading-5 text-slate-500">Os dados comerciais podem ser preenchidos depois em Configurações.</p>}
            <AuthField label="Senha">
              <span className="relative block">
                <LockKeyhole size={15} className="absolute left-3.5 top-3.5 text-slate-400" />
                <input required minLength={mode === "register" ? 8 : 1} maxLength={128} type={showPassword ? "text" : "password"} name="password" autoComplete={mode === "login" ? "current-password" : "new-password"} placeholder={mode === "login" ? "Digite sua senha" : "Mínimo de 8 caracteres"} className={`${authInput} pl-10 pr-11`} />
                <button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute right-3.5 top-3 text-slate-400 hover:text-slate-600" aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}>{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button>
              </span>
            </AuthField>
            {mode === "register" && (
              <AuthField label="Confirme sua senha">
                <input
                  required
                  minLength={8}
                  maxLength={128}
                  type="password"
                  name="confirm_password"
                  autoComplete="new-password"
                  placeholder="Digite a mesma senha novamente"
                  className={authInput}
                />
              </AuthField>
            )}

            {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-3 text-xs leading-5 text-rose-700">{error}</div>}

            <button disabled={busy} className="mt-2 flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[var(--teal)] text-xs font-bold text-white shadow-sm transition hover:bg-teal-800 disabled:cursor-wait disabled:opacity-60">
              {busy ? "Aguarde..." : mode === "login" ? "Entrar na plataforma" : "Criar minha conta"}
              {!busy && <ArrowRight size={15} />}
            </button>
          </form>
          <p className="mt-6 text-center text-[11px] leading-5 text-slate-400">
            Ao continuar, você concorda com nossos termos de uso e política de privacidade.
          </p>
        </div>
        <p className="text-center text-[10px] text-slate-400 lg:text-right">© 2026 Vendfy</p>
      </section>
    </main>
  );
}

const authInput = "h-11 w-full rounded-xl border border-slate-200 bg-white px-3.5 text-xs text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10";

function AuthField({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-2 block text-[11px] font-semibold text-slate-700">{label}</span>{children}</label>;
}
