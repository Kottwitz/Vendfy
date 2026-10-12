"use client";

import {
  Building2,
  Mail,
  Pencil,
  Phone,
  Plus,
  Search,
  Trash2,
  UsersRound,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest } from "@/lib/api";
import type { Client } from "@/lib/types";

type ClientPayload = {
  name: string;
  phone: string | null;
  email: string | null;
  document: string | null;
  address: string | null;
};

const blankClient: ClientPayload = {
  name: "",
  phone: "",
  email: "",
  document: "",
  address: "",
};

function toPayload(form: ClientPayload): ClientPayload {
  return {
    name: form.name.trim(),
    phone: form.phone?.trim() || null,
    email: form.email?.trim() || null,
    document: form.document?.trim() || null,
    address: form.address?.trim() || null,
  };
}

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Client | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadClients = useCallback(async () => {
    try {
      setClients(await apiRequest<Client[]>("clients?limit=100"));
      setError("");
    } catch (reason) {
      setError((reason as Error).message);
    }
  }, []);

  useEffect(() => {
    let active = true;
    apiRequest<Client[]>("clients?limit=100")
      .then((data) => {
        if (active) setClients(data);
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, []);

  const visibleClients = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("pt-BR");
    if (!query) return clients;
    return clients.filter((client) =>
      [client.name, client.email, client.phone, client.document]
        .filter(Boolean)
        .some((value) => value!.toLocaleLowerCase("pt-BR").includes(query)),
    );
  }, [clients, search]);

  function openCreate() {
    setEditing(null);
    setModalOpen(true);
    setNotice("");
  }

  function openEdit(client: Client) {
    setEditing(client);
    setModalOpen(true);
    setNotice("");
  }

  async function saveClient(payload: ClientPayload) {
    setBusy(true);
    setError("");
    try {
      if (editing) {
        await apiRequest<Client>(`clients/${editing.id}`, {
          method: "PATCH",
          body: JSON.stringify(toPayload(payload)),
        });
        setNotice("Cliente atualizado com sucesso.");
      } else {
        await apiRequest<Client>("clients", {
          method: "POST",
          body: JSON.stringify(toPayload(payload)),
        });
        setNotice("Cliente cadastrado com sucesso.");
      }
      setModalOpen(false);
      await loadClients();
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function removeClient(client: Client) {
    if (!window.confirm(`Excluir o cadastro de ${client.name}?`)) return;
    setError("");
    setNotice("");
    try {
      await apiRequest<void>(`clients/${client.id}`, { method: "DELETE" });
      setNotice("Cliente removido.");
      await loadClients();
    } catch (reason) {
      setError((reason as Error).message);
    }
  }

  return (
    <div className="space-y-7">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-teal-700">
            Relacionamento
          </p>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--navy)] sm:text-[30px]">
            Clientes
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Mantenha seus contatos e dados comerciais organizados.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-[var(--teal)] px-4 text-xs font-semibold text-white shadow-sm transition hover:bg-teal-800"
        >
          <Plus size={16} /> Adicionar cliente
        </button>
      </section>

      {error && <Alert tone="error" text={error} />}
      {notice && <Alert tone="success" text={notice} />}

      <section className="rounded-2xl border border-[var(--line)] bg-white">
        <div className="flex flex-col justify-between gap-4 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:px-6">
          <div>
            <h2 className="text-sm font-bold text-[var(--navy)]">Sua carteira</h2>
            <p className="mt-1 text-xs text-slate-400">
              {clients.length} {clients.length === 1 ? "cliente cadastrado" : "clientes cadastrados"}
            </p>
          </div>
          <label className="relative block w-full sm:max-w-[280px]">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por nome, email ou documento"
              className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-xs outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/10"
            />
          </label>
        </div>

        {visibleClients.length ? (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[680px] text-left">
                <thead>
                  <tr className="bg-slate-50/70 text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-400">
                    <th className="px-6 py-3">Cliente</th>
                    <th className="px-4 py-3">Contato</th>
                    <th className="px-4 py-3">Documento</th>
                    <th className="px-4 py-3">Cadastro</th>
                    <th className="w-24 px-4 py-3 text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {visibleClients.map((client) => (
                    <tr key={client.id} className="transition hover:bg-slate-50/60">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <ClientAvatar name={client.name} />
                          <span className="text-xs font-semibold text-slate-800">{client.name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <p className="text-xs text-slate-700">{client.email ?? "—"}</p>
                        <p className="mt-1 text-[11px] text-slate-400">{client.phone ?? "Sem telefone"}</p>
                      </td>
                      <td className="px-4 py-4 text-xs text-slate-600">{client.document ?? "—"}</td>
                      <td className="px-4 py-4 text-xs text-slate-500">
                        {new Intl.DateTimeFormat("pt-BR").format(new Date(client.created_at))}
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex justify-end gap-1">
                          <button onClick={() => openEdit(client)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-teal-700" aria-label={`Editar ${client.name}`}>
                            <Pencil size={14} />
                          </button>
                          <button onClick={() => void removeClient(client)} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600" aria-label={`Excluir ${client.name}`}>
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="divide-y divide-slate-100 md:hidden">
              {visibleClients.map((client) => (
                <div key={client.id} className="flex items-start gap-3 p-4">
                  <ClientAvatar name={client.name} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-semibold text-slate-800">{client.name}</p>
                    <p className="mt-1 truncate text-[11px] text-slate-500">{client.email ?? client.phone ?? "Sem contato informado"}</p>
                    {client.document && <p className="mt-1 text-[11px] text-slate-400">{client.document}</p>}
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => openEdit(client)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-teal-700" aria-label={`Editar ${client.name}`}><Pencil size={14} /></button>
                    <button onClick={() => void removeClient(client)} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600" aria-label={`Excluir ${client.name}`}><Trash2 size={14} /></button>
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="flex min-h-[280px] flex-col items-center justify-center px-5 text-center">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-slate-50 text-slate-400">
              {search ? <Search size={19} /> : <UsersRound size={20} />}
            </span>
            <h3 className="mt-4 text-sm font-semibold text-slate-700">
              {search ? "Nenhum cliente encontrado" : "Sua carteira começa aqui"}
            </h3>
            <p className="mt-1 max-w-xs text-xs leading-5 text-slate-400">
              {search ? "Tente buscar por outro nome ou documento." : "Cadastre seu primeiro cliente para criar orçamentos com mais agilidade."}
            </p>
            {!search && (
              <button onClick={openCreate} className="mt-4 text-xs font-semibold text-teal-700 hover:underline">
                Adicionar primeiro cliente
              </button>
            )}
          </div>
        )}
      </section>

      {modalOpen && (
        <ClientModal
          client={editing}
          busy={busy}
          onClose={() => setModalOpen(false)}
          onSave={saveClient}
        />
      )}
    </div>
  );
}

function ClientAvatar({ name }: { name: string }) {
  return (
    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#e4f0ee] text-xs font-bold text-teal-800">
      {name.trim().slice(0, 1).toUpperCase()}
    </span>
  );
}

function Alert({ tone, text }: { tone: "error" | "success"; text: string }) {
  return (
    <div className={`rounded-xl border px-4 py-3 text-xs ${tone === "error" ? "border-rose-200 bg-rose-50 text-rose-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
      {text}
    </div>
  );
}

function ClientModal({
  client,
  busy,
  onClose,
  onSave,
}: {
  client: Client | null;
  busy: boolean;
  onClose: () => void;
  onSave: (payload: ClientPayload) => Promise<void>;
}) {
  const [form, setForm] = useState<ClientPayload>(
    client
      ? {
          name: client.name,
          phone: client.phone ?? "",
          email: client.email ?? "",
          document: client.document ?? "",
          address: client.address ?? "",
        }
      : blankClient,
  );

  function update(field: keyof ClientPayload, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <div className="fixed inset-0 z-[60] grid place-items-center overflow-y-auto bg-slate-950/40 p-4" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void onSave(form);
        }}
        className="my-auto w-full max-w-[520px] rounded-2xl bg-white shadow-2xl"
      >
        <div className="flex items-start justify-between border-b border-slate-100 px-6 py-5">
          <div>
            <h2 className="text-base font-bold text-[var(--navy)]">{client ? "Editar cliente" : "Novo cliente"}</h2>
            <p className="mt-1 text-xs text-slate-400">Os dados ficam visíveis apenas para sua empresa.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Fechar"><X size={17} /></button>
        </div>
        <div className="grid gap-4 p-6 sm:grid-cols-2">
          <Field label="Nome *" className="sm:col-span-2">
            <input required maxLength={200} value={form.name} onChange={(event) => update("name", event.target.value)} placeholder="Nome do cliente ou empresa" className={inputClass} />
          </Field>
          <Field label="Email">
            <span className="relative block"><Mail size={14} className="absolute left-3 top-3 text-slate-400" /><input type="email" value={form.email ?? ""} onChange={(event) => update("email", event.target.value)} placeholder="email@empresa.com" className={`${inputClass} pl-9`} /></span>
          </Field>
          <Field label="Telefone">
            <span className="relative block"><Phone size={14} className="absolute left-3 top-3 text-slate-400" /><input value={form.phone ?? ""} onChange={(event) => update("phone", event.target.value)} placeholder="(00) 00000-0000" className={`${inputClass} pl-9`} /></span>
          </Field>
          <Field label="CPF / CNPJ">
            <input value={form.document ?? ""} onChange={(event) => update("document", event.target.value)} placeholder="Documento" className={inputClass} />
          </Field>
          <Field label="Endereço">
            <span className="relative block"><Building2 size={14} className="absolute left-3 top-3 text-slate-400" /><input value={form.address ?? ""} onChange={(event) => update("address", event.target.value)} placeholder="Cidade, estado" className={`${inputClass} pl-9`} /></span>
          </Field>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 px-6 py-4">
          <button type="button" onClick={onClose} className="h-10 rounded-xl px-4 text-xs font-semibold text-slate-600 hover:bg-slate-50">Cancelar</button>
          <button disabled={busy} className="h-10 rounded-xl bg-[var(--teal)] px-5 text-xs font-semibold text-white transition hover:bg-teal-800 disabled:opacity-60">
            {busy ? "Salvando..." : client ? "Salvar alterações" : "Cadastrar cliente"}
          </button>
        </div>
      </form>
    </div>
  );
}

const inputClass = "h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/10";

function Field({ label, className = "", children }: { label: string; className?: string; children: React.ReactNode }) {
  return <label className={`block ${className}`}><span className="mb-1.5 block text-[11px] font-semibold text-slate-600">{label}</span>{children}</label>;
}
