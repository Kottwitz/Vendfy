"use client";

import {
  Building2,
  KeyRound,
  LogOut,
  Mail,
  MessageCircle,
  Save,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import type { CompanySettings, User } from "@/lib/types";

type CompanyForm = {
  name: string;
  document: string;
  phone: string;
  email: string;
  address: string;
  whatsapp_phone_number_id: string;
  whatsapp_access_token: string;
  clear_whatsapp_access_token: boolean;
  smtp_host: string;
  smtp_port: string;
  smtp_username: string;
  smtp_password: string;
  clear_smtp_password: boolean;
  smtp_security: "starttls" | "ssl";
};

const emptyCompanyForm: CompanyForm = {
  name: "",
  document: "",
  phone: "",
  email: "",
  address: "",
  whatsapp_phone_number_id: "",
  whatsapp_access_token: "",
  clear_whatsapp_access_token: false,
  smtp_host: "",
  smtp_port: "",
  smtp_username: "",
  smtp_password: "",
  clear_smtp_password: false,
  smtp_security: "starttls",
};

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [company, setCompany] = useState<CompanySettings | null>(null);
  const [form, setForm] = useState<CompanyForm>(emptyCompanyForm);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const router = useRouter();

  useEffect(() => {
    let active = true;
    Promise.all([
      fetch("/api/backend/users/me", { cache: "no-store" }),
      fetch("/api/backend/companies/me", { cache: "no-store" }),
    ])
      .then(async ([userResponse, companyResponse]) => {
        if (!userResponse.ok || !companyResponse.ok) {
          throw new Error("Não foi possível carregar as configurações.");
        }
        const [currentUser, currentCompany] = await Promise.all([
          userResponse.json() as Promise<User>,
          companyResponse.json() as Promise<CompanySettings>,
        ]);
        if (!active) return;
        setUser(currentUser);
        setCompany(currentCompany);
        setForm({
          ...emptyCompanyForm,
          name: currentCompany.name,
          document: currentCompany.document ?? "",
          phone: currentCompany.phone ?? "",
          email: currentCompany.email ?? "",
          address: currentCompany.address ?? "",
          whatsapp_phone_number_id:
            currentCompany.whatsapp_phone_number_id ?? "",
          smtp_host: currentCompany.smtp_host ?? "",
          smtp_port: currentCompany.smtp_port
            ? String(currentCompany.smtp_port)
            : "",
          smtp_username: currentCompany.smtp_username ?? "",
          smtp_security: currentCompany.smtp_security,
        });
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function updateForm(field: keyof CompanyForm, value: string | boolean) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function saveCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    const payload: Record<string, string | number | boolean | null> = {
      name: form.name,
      document: form.document || null,
      phone: form.phone || null,
      email: form.email || null,
      address: form.address || null,
      whatsapp_phone_number_id: form.whatsapp_phone_number_id || null,
      clear_whatsapp_access_token: form.clear_whatsapp_access_token,
      smtp_host: form.smtp_host || null,
      smtp_port: form.smtp_port ? Number(form.smtp_port) : null,
      smtp_username: form.smtp_username || null,
      clear_smtp_password: form.clear_smtp_password,
      smtp_security: form.smtp_security,
    };
    if (form.whatsapp_access_token) {
      payload.whatsapp_access_token = form.whatsapp_access_token;
    }
    if (form.smtp_password) payload.smtp_password = form.smtp_password;

    try {
      const response = await fetch("/api/backend/companies/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const data = (await response.json()) as { detail?: string };
        throw new Error(data.detail ?? "Não foi possível salvar os dados.");
      }
      const updated = (await response.json()) as CompanySettings;
      setCompany(updated);
      setForm((current) => ({
        ...current,
        whatsapp_access_token: "",
        clear_whatsapp_access_token: false,
        smtp_password: "",
        clear_smtp_password: false,
      }));
      setNotice("Dados da empresa e integrações salvos.");
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  return (
    <div className="space-y-7">
      <section>
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-teal-700">Sua conta</p>
        <h1 className="text-2xl font-bold tracking-tight text-[var(--navy)] sm:text-[30px]">Configurações</h1>
        <p className="mt-2 text-sm text-slate-500">Perfil, dados comerciais e canais de envio dos orçamentos.</p>
      </section>
      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-700">{error}</div>}
      {notice && <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs text-emerald-700">{notice}</div>}

      <section className="max-w-3xl overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
        <div className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-teal-50 text-teal-700"><UserRound size={18} /></span>
          <div><h2 className="text-sm font-bold text-[var(--navy)]">Perfil</h2><p className="mt-1 text-xs text-slate-400">Dados vinculados à sua conta</p></div>
        </div>
        <div className="grid gap-5 p-6 sm:grid-cols-2">
          <ProfileField label="Nome" value={user?.name ?? (loading ? "Carregando..." : "—")} />
          <ProfileField label="Email da conta" value={user?.email ?? "—"} />
          <ProfileField label="Função" value={user?.role === "owner" ? "Proprietário" : user?.role ?? "—"} />
          <ProfileField label="Identificador da empresa" value={user?.company_id ?? "—"} />
        </div>
      </section>

      <form onSubmit={saveCompany} className="max-w-3xl space-y-5">
        <section className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
          <SectionHeading icon={Building2} title="Dados comerciais" subtitle="Esses dados aparecem no orçamento enviado ao cliente." />
          <div className="grid gap-4 p-6 sm:grid-cols-2">
            <Field label="Nome da empresa *"><input required maxLength={200} value={form.name} onChange={(event) => updateForm("name", event.target.value)} className={inputClass} /></Field>
            <Field label="CNPJ / documento"><input maxLength={32} value={form.document} onChange={(event) => updateForm("document", event.target.value)} className={inputClass} /></Field>
            <Field label="Telefone de envio WhatsApp"><input type="tel" maxLength={32} placeholder="+55 11 99999-9999" value={form.phone} onChange={(event) => updateForm("phone", event.target.value)} className={inputClass} /></Field>
            <Field label="Email remetente"><input type="email" value={form.email} onChange={(event) => updateForm("email", event.target.value)} placeholder="orcamentos@suaempresa.com.br" className={inputClass} /></Field>
            <Field label="Endereço" className="sm:col-span-2"><input maxLength={500} value={form.address} onChange={(event) => updateForm("address", event.target.value)} className={inputClass} /></Field>
          </div>
        </section>

        <section className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
          <SectionHeading icon={MessageCircle} title="WhatsApp Business Cloud API" subtitle="O envio sai do número vinculado à sua conta Meta Business." configured={company?.whatsapp_configured} />
          <div className="grid gap-4 p-6 sm:grid-cols-2">
            <Field label="Phone Number ID"><input value={form.whatsapp_phone_number_id} onChange={(event) => updateForm("whatsapp_phone_number_id", event.target.value)} placeholder="ID do número no Meta for Developers" className={inputClass} /></Field>
            <Field label="Access Token"><input type="password" autoComplete="new-password" value={form.whatsapp_access_token} onChange={(event) => updateForm("whatsapp_access_token", event.target.value)} placeholder={company?.whatsapp_configured ? "Token salvo; preencha para substituir" : "Token permanente da Cloud API"} className={inputClass} /></Field>
            {company?.whatsapp_configured && <ClearCredential checked={form.clear_whatsapp_access_token} onChange={(value) => updateForm("clear_whatsapp_access_token", value)} label="Remover token salvo" />}
          </div>
        </section>

        <section className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
          <SectionHeading icon={Mail} title="Email (SMTP)" subtitle="Use uma conta e remetente autorizados pelo seu provedor de email." configured={company?.smtp_configured} />
          <div className="grid gap-4 p-6 sm:grid-cols-2">
            <Field label="Servidor SMTP"><input value={form.smtp_host} onChange={(event) => updateForm("smtp_host", event.target.value)} placeholder="smtp.suaempresa.com.br" className={inputClass} /></Field>
            <Field label="Porta"><input type="number" min={1} max={65535} value={form.smtp_port} onChange={(event) => updateForm("smtp_port", event.target.value)} placeholder="587" className={inputClass} /></Field>
            <Field label="Usuário SMTP"><input autoComplete="username" value={form.smtp_username} onChange={(event) => updateForm("smtp_username", event.target.value)} className={inputClass} /></Field>
            <Field label="Senha SMTP"><input type="password" autoComplete="new-password" value={form.smtp_password} onChange={(event) => updateForm("smtp_password", event.target.value)} placeholder={company?.smtp_configured ? "Senha salva; preencha para substituir" : "Senha ou senha de aplicativo"} className={inputClass} /></Field>
            <Field label="Segurança da conexão"><select value={form.smtp_security} onChange={(event) => updateForm("smtp_security", event.target.value as CompanyForm["smtp_security"])} className={inputClass}><option value="starttls">STARTTLS (geralmente porta 587)</option><option value="ssl">SSL/TLS (geralmente porta 465)</option></select></Field>
            {company?.smtp_configured && <ClearCredential checked={form.clear_smtp_password} onChange={(value) => updateForm("clear_smtp_password", value)} label="Remover senha SMTP salva" />}
          </div>
        </section>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-xl text-[11px] leading-5 text-slate-500">Tokens e senhas são criptografados no banco. Configure também <code>SECURITY__CREDENTIAL_ENCRYPTION_KEY</code> no ambiente do backend e mantenha uma cópia segura da chave.</p>
          <button disabled={busy || loading} className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-xl bg-[var(--teal)] px-4 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-60"><Save size={15} />{busy ? "Salvando..." : "Salvar configurações"}</button>
        </div>
      </form>

      <section className="max-w-3xl overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
        <div className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-50 text-blue-700"><ShieldCheck size={18} /></span>
          <div><h2 className="text-sm font-bold text-[var(--navy)]">Segurança</h2><p className="mt-1 text-xs text-slate-400">Autenticação e acesso</p></div>
        </div>
        <div className="divide-y divide-slate-100 px-6">
          <SettingRow icon={KeyRound} title="Sessão protegida" detail="Seu token fica em cookie HttpOnly e não é acessível por JavaScript." />
          <SettingRow icon={Building2} title="Dados da empresa" detail="As informações exibidas pela plataforma são isoladas por empresa." />
          <button onClick={logout} className="flex w-full items-center gap-3 py-4 text-left">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-rose-50 text-rose-600"><LogOut size={16} /></span>
            <span className="flex-1"><span className="block text-xs font-semibold text-rose-700">Sair da conta</span><span className="mt-1 block text-[11px] text-slate-400">Encerra a sessão neste navegador</span></span>
          </button>
        </div>
      </section>
    </div>
  );
}

function SectionHeading({ icon: Icon, title, subtitle, configured }: { icon: typeof Building2; title: string; subtitle: string; configured?: boolean }) {
  return <div className="flex items-center gap-3 border-b border-slate-100 px-6 py-5"><span className="grid h-10 w-10 place-items-center rounded-xl bg-teal-50 text-teal-700"><Icon size={18} /></span><div className="min-w-0 flex-1"><h2 className="text-sm font-bold text-[var(--navy)]">{title}</h2><p className="mt-1 text-xs text-slate-400">{subtitle}</p></div>{configured !== undefined && <span className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-semibold ${configured ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{configured ? "Configurado" : "Pendente"}</span>}</div>;
}

function Field({ label, className = "", children }: { label: string; className?: string; children: React.ReactNode }) {
  return <label className={`block ${className}`}><span className="mb-1.5 block text-[11px] font-semibold text-slate-600">{label}</span>{children}</label>;
}

function ClearCredential({ checked, onChange, label }: { checked: boolean; onChange: (checked: boolean) => void; label: string }) {
  return <label className="flex items-center gap-2 text-[11px] text-rose-700 sm:col-span-2"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="accent-rose-600" />{label}</label>;
}

function ProfileField({ label, value }: { label: string; value: string }) {
  return <div><p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-400">{label}</p><p className="mt-2 break-all text-xs font-medium text-slate-700">{value}</p></div>;
}

function SettingRow({ icon: Icon, title, detail }: { icon: typeof KeyRound; title: string; detail: string }) {
  return <div className="flex items-center gap-3 py-4"><span className="grid h-9 w-9 place-items-center rounded-xl bg-slate-50 text-slate-500"><Icon size={16} /></span><span><span className="block text-xs font-semibold text-slate-700">{title}</span><span className="mt-1 block text-[11px] text-slate-400">{detail}</span></span></div>;
}

const inputClass = "h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/10";
