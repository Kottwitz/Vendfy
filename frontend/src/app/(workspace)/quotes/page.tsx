"use client";

import {
  CalendarDays,
  Check,
  ChevronDown,
  CirclePlus,
  Download,
  Eye,
  FileText,
  Mail,
  MessageCircle,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, formatCurrency, formatDate } from "@/lib/api";
import type { Client, Quote, QuoteItem, QuoteStatus } from "@/lib/types";

const statusMeta: Record<QuoteStatus, { label: string; style: string }> = {
  DRAFT: { label: "Rascunho", style: "bg-slate-100 text-slate-600" },
  SENT: { label: "Enviado", style: "bg-blue-50 text-blue-700" },
  VIEWED: { label: "Visualizado", style: "bg-violet-50 text-violet-700" },
  APPROVED: { label: "Aprovado", style: "bg-emerald-50 text-emerald-700" },
  REJECTED: { label: "Recusado", style: "bg-rose-50 text-rose-700" },
  EXPIRED: { label: "Expirado", style: "bg-amber-50 text-amber-700" },
  CANCELLED: { label: "Cancelado", style: "bg-slate-200 text-slate-600" },
};

type QuoteItemInput = { description: string; quantity: string; unit_price: string; unit_cost: string };
const emptyItem: QuoteItemInput = { description: "", quantity: "1", unit_price: "", unit_cost: "" };

export default function QuotesPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedQuote, setSelectedQuote] = useState<Quote | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [downloadingQuoteId, setDownloadingQuoteId] = useState<string | null>(null);
  const [sendingQuoteId, setSendingQuoteId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [clientData, quoteData] = await Promise.all([
        apiRequest<Client[]>("clients?limit=100"),
        apiRequest<Quote[]>("quotes?limit=100"),
      ]);
      setClients(clientData);
      setQuotes(quoteData);
      setError("");
    } catch (reason) {
      setError((reason as Error).message);
    }
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([
      apiRequest<Client[]>("clients?limit=100"),
      apiRequest<Quote[]>("quotes?limit=100"),
    ])
      .then(([clientData, quoteData]) => {
        if (active) {
          setClients(clientData);
          setQuotes(quoteData);
        }
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, []);

  const visibleQuotes = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("pt-BR");
    return quotes.filter((quote) => {
      if (statusFilter && quote.status !== statusFilter) return false;
      if (!query) return true;
      const clientName = clients.find((client) => client.id === quote.client_id)?.name ?? "";
      return `${quote.number} ${clientName} ${quote.description ?? ""}`
        .toLocaleLowerCase("pt-BR")
        .includes(query);
    });
  }, [clients, quotes, search, statusFilter]);

  async function transition(quote: Quote, nextStatus: QuoteStatus) {
    setError("");
    setNotice("");
    try {
      await apiRequest<Quote>(`quotes/${quote.id}/status`, {
        method: "POST",
        body: JSON.stringify({ status: nextStatus }),
      });
      setNotice(`Orçamento #${quote.number} atualizado.`);
      await loadData();
    } catch (reason) {
      setError((reason as Error).message);
    }
  }

  async function cancelQuote(quote: Quote) {
    setError("");
    setNotice("");
    try {
      await apiRequest<Quote>(`quotes/${quote.id}/cancel`, { method: "POST" });
      setNotice(`Orçamento #${quote.number} cancelado.`);
      await loadData();
    } catch (reason) {
      setError((reason as Error).message);
    }
  }

  async function deleteQuote(quote: Quote) {
    if (!window.confirm(`Excluir permanentemente o orçamento #${quote.number}?`)) return;
    setError("");
    setNotice("");
    try {
      await apiRequest<void>(`quotes/${quote.id}`, { method: "DELETE" });
      setNotice(`Orçamento #${quote.number} excluído.`);
      if (selectedQuote?.id === quote.id) setSelectedQuote(null);
      await loadData();
    } catch (reason) {
      setError((reason as Error).message);
    }
  }

  async function saveQuote(payload: {
    client_id: string;
    items: QuoteItemInput[];
    discount: string;
    description: string;
    valid_until: string;
  }) {
    setError("");
    try {
      await apiRequest<Quote>("quotes", {
        method: "POST",
        body: JSON.stringify({
          client_id: payload.client_id,
          items: payload.items
            .filter((item) => item.description.trim() && item.unit_price)
            .map((item) => ({
              description: item.description.trim(),
              quantity: item.quantity,
              unit_price: item.unit_price,
              unit_cost: item.unit_cost || null,
            })),
          discount: payload.discount || "0",
          description: payload.description.trim() || null,
          valid_until: payload.valid_until || null,
        }),
      });
      setCreateOpen(false);
      setNotice("Orçamento criado como rascunho.");
      await loadData();
    } catch (reason) {
      setError((reason as Error).message);
    }
  }

  async function addItem(quote: Quote, item: QuoteItemInput) {
    try {
      const updated = await apiRequest<Quote>(`quotes/${quote.id}/items`, {
        method: "POST",
        body: JSON.stringify({
          description: item.description.trim(),
          quantity: item.quantity,
          unit_price: item.unit_price,
          unit_cost: item.unit_cost || null,
        }),
      });
      setSelectedQuote(updated);
      setNotice("Item adicionado e total recalculado.");
      await loadData();
    } catch (reason) {
      setError((reason as Error).message);
    }
  }

  async function removeItem(quote: Quote, item: QuoteItem) {
    try {
      await apiRequest<void>(`quotes/${quote.id}/items/${item.id}`, {
        method: "DELETE",
      });
      const refreshed = await apiRequest<Quote>(`quotes/${quote.id}`);
      setSelectedQuote(refreshed);
      setNotice("Item removido e total recalculado.");
      await loadData();
    } catch (reason) {
      setError((reason as Error).message);
    }
  }

  async function updateItemCost(
    quote: Quote,
    item: QuoteItem,
    unitCost: string,
  ): Promise<void> {
    await apiRequest<QuoteItem>(`quotes/${quote.id}/items/${item.id}`, {
      method: "PATCH",
      body: JSON.stringify({ unit_cost: unitCost || null }),
    });
    const refreshed = await apiRequest<Quote>(`quotes/${quote.id}`);
    setSelectedQuote(refreshed);
    setNotice("Custo do item atualizado.");
    await loadData();
  }

  async function downloadQuotePdf(quote: Quote) {
    setError("");
    setDownloadingQuoteId(quote.id);
    try {
      const response = await fetch(`/api/backend/quotes/${quote.id}/pdf`, {
        cache: "no-store",
      });
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string };
        throw new Error(
          payload.detail || `Não foi possível gerar o PDF (${response.status}).`,
        );
      }

      const pdf = await response.blob();
      const objectUrl = URL.createObjectURL(pdf);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = `orcamento-${String(quote.number).padStart(4, "0")}.pdf`;
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } finally {
      setDownloadingQuoteId(null);
    }
  }

  async function sendQuote(
    quote: Quote,
    channel: "email" | "whatsapp",
    recipient: string,
    message: string,
  ) {
    setSendingQuoteId(quote.id);
    try {
      const payload =
        channel === "email"
          ? { recipient: recipient || null, message: message || null }
          : { recipient_phone: recipient || null, message: message || null };
      const result = await apiRequest<{ detail: string }>(
        `quotes/${quote.id}/send/${channel}`,
        { method: "POST", body: JSON.stringify(payload) },
      );
      setNotice(result.detail);
    } finally {
      setSendingQuoteId(null);
    }
  }

  return (
    <div className="space-y-7">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-teal-700">Comercial</p>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--navy)] sm:text-[30px]">Orçamentos</h1>
          <p className="mt-2 text-sm text-slate-500">Crie propostas, acompanhe o status e organize seus itens.</p>
        </div>
        <button
          onClick={() => {
            setCreateOpen(true);
            setNotice("");
          }}
          disabled={!clients.length}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-[var(--teal)] px-4 text-xs font-semibold text-white shadow-sm transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Plus size={16} /> Novo orçamento
        </button>
      </section>

      {!clients.length && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
          Cadastre pelo menos um cliente antes de criar um orçamento.
        </div>
      )}
      {error && <Alert tone="error" text={error} />}
      {notice && <Alert tone="success" text={notice} />}

      <section className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
        <div className="flex flex-col justify-between gap-4 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:px-6">
          <div>
            <h2 className="text-sm font-bold text-[var(--navy)]">Todas as propostas</h2>
            <p className="mt-1 text-xs text-slate-400">{visibleQuotes.length} orçamento(s)</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <label className="relative block">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar orçamento ou cliente" className={`${inputClass} pl-9 sm:w-[220px]`} />
            </label>
            <label className="relative block">
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className={`${inputClass} appearance-none pr-9 sm:w-[160px]`}>
                <option value="">Todos os status</option>
                {Object.entries(statusMeta).map(([key, value]) => <option key={key} value={key}>{value.label}</option>)}
              </select>
              <ChevronDown size={14} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400" />
            </label>
          </div>
        </div>
        {visibleQuotes.length ? (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[780px] text-left">
                <thead><tr className="bg-slate-50/70 text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-400">
                  <th className="px-6 py-3">Orçamento</th><th className="px-4 py-3">Cliente</th><th className="px-4 py-3">Data</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Total</th><th className="px-6 py-3 text-right">Ações</th>
                </tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {visibleQuotes.map((quote) => {
                    const customer = clients.find((client) => client.id === quote.client_id);
                    return (
                      <tr key={quote.id} className={`cursor-pointer transition hover:bg-slate-50/70 ${selectedQuote?.id === quote.id ? "bg-teal-50/40" : ""}`} onClick={() => setSelectedQuote(quote)}>
                        <td className="px-6 py-4"><span className="text-xs font-bold text-slate-800">#{quote.number}</span><p className="mt-1 max-w-48 truncate text-[11px] text-slate-400">{quote.description ?? `${quote.items.length} item(ns)`}</p></td>
                        <td className="px-4 py-4 text-xs font-medium text-slate-700">{customer?.name ?? "Cliente"}</td>
                        <td className="px-4 py-4 text-xs text-slate-500">{formatDate(quote.created_at)}</td>
                        <td className="px-4 py-4"><StatusBadge status={quote.status} /></td>
                        <td className="px-4 py-4 text-right text-xs font-bold text-slate-800">{formatCurrency(quote.total)}</td>
                        <td className="px-6 py-4" onClick={(event) => event.stopPropagation()}>
                          <QuoteActions quote={quote} onTransition={transition} onCancel={cancelQuote} onDelete={deleteQuote} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="divide-y divide-slate-100 md:hidden">
              {visibleQuotes.map((quote) => (
                <article key={quote.id} className="p-4" onClick={() => setSelectedQuote(quote)}>
                  <div className="flex items-start justify-between gap-3">
                    <div><p className="text-xs font-bold text-slate-800">Orçamento #{quote.number}</p><p className="mt-1 text-[11px] text-slate-500">{clients.find((client) => client.id === quote.client_id)?.name ?? "Cliente"}</p></div>
                    <StatusBadge status={quote.status} />
                  </div>
                  <div className="mt-3 flex items-center justify-between"><span className="text-[11px] text-slate-400">{formatDate(quote.created_at)}</span><span className="text-xs font-bold text-slate-800">{formatCurrency(quote.total)}</span></div>
                  <div className="mt-3" onClick={(event) => event.stopPropagation()}><QuoteActions quote={quote} onTransition={transition} onCancel={cancelQuote} onDelete={deleteQuote} /></div>
                </article>
              ))}
            </div>
          </>
        ) : (
          <div className="flex min-h-[280px] flex-col items-center justify-center px-6 text-center">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-slate-50 text-slate-400"><FileText size={20} /></span>
            <h3 className="mt-4 text-sm font-semibold text-slate-700">{quotes.length ? "Nenhum resultado encontrado" : "Nenhum orçamento por aqui"}</h3>
            <p className="mt-1 max-w-sm text-xs leading-5 text-slate-400">Crie seu primeiro orçamento para acompanhar propostas e valores em um só lugar.</p>
            {clients.length > 0 && <button onClick={() => setCreateOpen(true)} className="mt-4 text-xs font-semibold text-teal-700 hover:underline">Criar primeiro orçamento</button>}
          </div>
        )}
      </section>

      {selectedQuote && (
        <QuoteDetail
          quote={selectedQuote}
          client={clients.find((client) => client.id === selectedQuote.client_id) ?? null}
          downloading={downloadingQuoteId === selectedQuote.id}
          sending={sendingQuoteId === selectedQuote.id}
          onClose={() => setSelectedQuote(null)}
          onAddItem={addItem}
          onRemoveItem={removeItem}
          onUpdateItemCost={updateItemCost}
          onDownload={() => downloadQuotePdf(selectedQuote)}
          onSend={(channel, recipient, message) =>
            sendQuote(selectedQuote, channel, recipient, message)
          }
        />
      )}
      {createOpen && (
        <QuoteModal clients={clients} onClose={() => setCreateOpen(false)} onSave={saveQuote} />
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: QuoteStatus }) {
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-semibold ${statusMeta[status].style}`}>{statusMeta[status].label}</span>;
}

function QuoteActions({ quote, onTransition, onCancel, onDelete }: {
  quote: Quote;
  onTransition: (quote: Quote, status: QuoteStatus) => Promise<void>;
  onCancel: (quote: Quote) => Promise<void>;
  onDelete: (quote: Quote) => Promise<void>;
}) {
  return (
    <div className="flex flex-wrap justify-end gap-1.5">
      {quote.status === "DRAFT" && <ActionButton label="Enviar" onClick={() => void onTransition(quote, "SENT")} />}
      {["SENT", "VIEWED"].includes(quote.status) && <>
        <ActionButton label="Aprovar" onClick={() => void onTransition(quote, "APPROVED")} />
        <ActionButton label="Recusar" onClick={() => void onTransition(quote, "REJECTED")} tone="muted" />
      </>}
      {["DRAFT", "SENT", "VIEWED"].includes(quote.status) && <ActionButton label="Cancelar" onClick={() => void onCancel(quote)} tone="danger" />}
      <button onClick={() => void onDelete(quote)} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-600" aria-label={`Excluir orçamento ${quote.number}`} title="Excluir orçamento"><Trash2 size={14} /></button>
    </div>
  );
}

function ActionButton({ label, onClick, tone = "primary" }: { label: string; onClick: () => void; tone?: "primary" | "muted" | "danger" }) {
  const classes = {
    primary: "border-teal-100 bg-teal-50 text-teal-700 hover:bg-teal-100",
    muted: "border-slate-200 bg-white text-slate-600 hover:bg-slate-50",
    danger: "border-rose-100 bg-white text-rose-600 hover:bg-rose-50",
  };
  return <button onClick={onClick} className={`rounded-lg border px-2.5 py-1.5 text-[10px] font-semibold transition ${classes[tone]}`}>{label}</button>;
}

function Alert({ tone, text }: { tone: "error" | "success"; text: string }) {
  return <div className={`rounded-xl border px-4 py-3 text-xs ${tone === "error" ? "border-rose-200 bg-rose-50 text-rose-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>{text}</div>;
}

function QuoteModal({ clients, onClose, onSave }: {
  clients: Client[];
  onClose: () => void;
  onSave: (payload: { client_id: string; items: QuoteItemInput[]; discount: string; description: string; valid_until: string }) => Promise<void>;
}) {
  const [clientId, setClientId] = useState(clients[0]?.id ?? "");
  const [items, setItems] = useState<QuoteItemInput[]>([{ ...emptyItem }]);
  const [discount, setDiscount] = useState("0");
  const [description, setDescription] = useState("");
  const [validUntil, setValidUntil] = useState("");
  const [busy, setBusy] = useState(false);
  const subtotal = items.reduce((sum, item) => sum + (Number(item.quantity) || 0) * (Number(item.unit_price) || 0), 0);

  function patchItem(index: number, field: keyof QuoteItemInput, value: string) {
    setItems((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: value } : item));
  }

  return (
    <ModalFrame title="Criar orçamento" subtitle="Comece uma proposta como rascunho." onClose={onClose}>
      <form onSubmit={async (event) => { event.preventDefault(); setBusy(true); await onSave({ client_id: clientId, items, discount, description, valid_until: validUntil }); setBusy(false); }}>
        <div className="space-y-4 p-6">
          <Field label="Cliente *">
            <select required value={clientId} onChange={(event) => setClientId(event.target.value)} className={inputClass}>
              {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
            </select>
          </Field>
          <Field label="Descrição"><input value={description} onChange={(event) => setDescription(event.target.value)} maxLength={4000} placeholder="Ex.: Reforma da área comercial" className={inputClass} /></Field>
          <div>
            <div className="mb-2 flex items-center justify-between"><span className="text-[11px] font-semibold text-slate-600">Itens do orçamento</span><span className="text-[10px] text-slate-400">Valores calculados automaticamente</span></div>
            <div className="space-y-2">
              {items.map((item, index) => (
                <div key={index} className="space-y-2 rounded-xl border border-slate-100 p-3">
                  <div className="flex gap-2">
                    <input required value={item.description} onChange={(event) => patchItem(index, "description", event.target.value)} placeholder="Serviço ou material" maxLength={500} className={inputClass} />
                    <button type="button" onClick={() => setItems((current) => current.filter((_, itemIndex) => itemIndex !== index))} disabled={items.length === 1} className="grid h-11 w-10 shrink-0 place-items-center rounded-lg text-slate-400 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-30" aria-label="Remover item"><X size={15} /></button>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <input required type="number" min="0.001" step="0.001" value={item.quantity} onChange={(event) => patchItem(index, "quantity", event.target.value)} aria-label="Quantidade" className={`${inputClass} px-2`} />
                    <input type="number" min="0" step="0.01" value={item.unit_cost} onChange={(event) => patchItem(index, "unit_cost", event.target.value)} placeholder="Custo unit." aria-label="Custo unitário, opcional" className={`${inputClass} px-2`} />
                    <input required type="number" min="0" step="0.01" value={item.unit_price} onChange={(event) => patchItem(index, "unit_price", event.target.value)} placeholder="Preço unit." aria-label="Preço unitário" className={`${inputClass} px-2`} />
                  </div>
                </div>
              ))}
            </div>
            <button type="button" onClick={() => setItems((current) => [...current, { ...emptyItem }])} className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-teal-700 hover:underline"><CirclePlus size={14} /> Adicionar item</button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Desconto (R$)"><input type="number" min="0" step="0.01" value={discount} onChange={(event) => setDiscount(event.target.value)} className={inputClass} /></Field>
            <Field label="Válido até"><span className="relative block"><CalendarDays size={14} className="absolute left-3 top-3 text-slate-400" /><input type="date" value={validUntil} onChange={(event) => setValidUntil(event.target.value)} className={`${inputClass} pl-9`} /></span></Field>
          </div>
          <div className="flex justify-between rounded-xl bg-slate-50 px-4 py-3 text-xs"><span className="text-slate-500">Subtotal estimado</span><strong className="text-slate-800">{formatCurrency(subtotal)}</strong></div>
        </div>
        <ModalActions onClose={onClose} busy={busy} label="Criar rascunho" />
      </form>
    </ModalFrame>
  );
}

function QuoteDetail({ quote, client, downloading, sending, onClose, onAddItem, onRemoveItem, onUpdateItemCost, onDownload, onSend }: {
  quote: Quote;
  client: Client | null;
  downloading: boolean;
  sending: boolean;
  onClose: () => void;
  onAddItem: (quote: Quote, item: QuoteItemInput) => Promise<void>;
  onRemoveItem: (quote: Quote, item: QuoteItem) => Promise<void>;
  onUpdateItemCost: (quote: Quote, item: QuoteItem, unitCost: string) => Promise<void>;
  onDownload: () => void;
  onSend: (channel: "email" | "whatsapp", recipient: string, message: string) => Promise<void>;
}) {
  const [item, setItem] = useState<QuoteItemInput>({ ...emptyItem });
  const [deliveryChannel, setDeliveryChannel] = useState<"email" | "whatsapp" | null>(null);
  const [recipient, setRecipient] = useState("");
  const [message, setMessage] = useState("");
  const [deliveryError, setDeliveryError] = useState("");
  const [deliveryNotice, setDeliveryNotice] = useState("");
  const editable = quote.status === "DRAFT";

  async function handleDownload() {
    setDeliveryError("");
    setDeliveryNotice("");
    try {
      await onDownload();
    } catch (reason) {
      setDeliveryError(
        reason instanceof Error
          ? reason.message
          : "Não foi possível gerar o PDF do orçamento.",
      );
    }
  }

  function openDelivery(channel: "email" | "whatsapp") {
    setDeliveryChannel(channel);
    setRecipient(channel === "email" ? client?.email ?? "" : client?.phone ?? "");
    setMessage("");
    setDeliveryError("");
    setDeliveryNotice("");
  }

  async function submitDelivery(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!deliveryChannel) return;
    setDeliveryError("");
    setDeliveryNotice("");
    try {
      await onSend(deliveryChannel, recipient.trim(), message.trim());
      setDeliveryNotice(
        deliveryChannel === "email"
          ? "Orçamento enviado por email."
          : "Orçamento enviado pelo WhatsApp.",
      );
    } catch (reason) {
      setDeliveryError(
        reason instanceof Error
          ? reason.message
          : "Não foi possível enviar o orçamento.",
      );
    }
  }

  return (
    <ModalFrame title={`Orçamento #${quote.number}`} subtitle={quote.description || "Detalhes e itens da proposta."} onClose={onClose}>
      <div className="p-6">
        <div className="mb-5 flex items-center justify-between rounded-xl bg-slate-50 p-4">
          <div><p className="text-[10px] text-slate-400">Total do orçamento</p><p className="mt-1 text-lg font-bold text-[var(--navy)]">{formatCurrency(quote.total)}</p></div>
          <StatusBadge status={quote.status} />
        </div>
        <div className="mb-3 flex justify-between text-[11px]"><span className="text-slate-500">Subtotal</span><span>{formatCurrency(quote.subtotal)}</span></div>
        <div className="mb-5 flex justify-between text-[11px]"><span className="text-slate-500">Desconto</span><span>- {formatCurrency(quote.discount)}</span></div>
        <div className="mb-2 flex items-center justify-between"><h3 className="text-xs font-bold text-slate-700">Itens ({quote.items.length})</h3><span className="text-[10px] text-slate-400">Totais automáticos</span></div>
        <div className="divide-y divide-slate-100 rounded-xl border border-slate-100">
          {quote.items.length ? quote.items.map((entry) => (
            <div key={entry.id} className="space-y-2 px-3 py-3">
              <div className="flex items-center gap-3">
                <div className="min-w-0 flex-1"><p className="truncate text-xs font-semibold text-slate-700">{entry.description}</p><p className="mt-1 text-[10px] text-slate-400">{entry.quantity} × {formatCurrency(entry.unit_price)} · Custo: {entry.unit_cost === null ? "não informado" : formatCurrency(entry.unit_cost)}</p></div>
                <span className="text-xs font-bold text-slate-700">{formatCurrency(entry.total)}</span>
                {editable && <button onClick={() => void onRemoveItem(quote, entry)} className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600" aria-label={`Remover ${entry.description}`}><Trash2 size={13} /></button>}
              </div>
              <ItemCostEditor
                initialCost={entry.unit_cost ?? ""}
                onSave={(unitCost) => onUpdateItemCost(quote, entry, unitCost)}
              />
            </div>
          )) : <p className="px-3 py-5 text-center text-xs text-slate-400">Nenhum item adicionado.</p>}
        </div>
        {editable && (
          <form className="mt-4 space-y-2" onSubmit={(event) => { event.preventDefault(); void onAddItem(quote, item).then(() => setItem({ ...emptyItem })); }}>
            <p className="text-[11px] font-semibold text-slate-600">Adicionar item</p>
            <input required value={item.description} onChange={(event) => setItem({ ...item, description: event.target.value })} placeholder="Descrição" maxLength={500} className={inputClass} />
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-[1fr_1fr_1fr_auto]">
              <input required type="number" min="0.001" step="0.001" value={item.quantity} onChange={(event) => setItem({ ...item, quantity: event.target.value })} aria-label="Quantidade" className={inputClass} />
              <input type="number" min="0" step="0.01" value={item.unit_cost} onChange={(event) => setItem({ ...item, unit_cost: event.target.value })} placeholder="Custo unit." aria-label="Custo unitário, opcional" className={inputClass} />
              <input required type="number" min="0" step="0.01" value={item.unit_price} onChange={(event) => setItem({ ...item, unit_price: event.target.value })} placeholder="Preço unitário" aria-label="Preço unitário" className={inputClass} />
              <button className="col-span-2 grid h-10 place-items-center rounded-xl bg-[var(--teal)] text-white hover:bg-teal-800 sm:col-span-1" aria-label="Adicionar item"><Plus size={16} /></button>
            </div>
          </form>
        )}
      </div>
      {deliveryError && <p role="alert" className="px-6 pb-3 text-xs text-rose-700">{deliveryError}</p>}
      {deliveryNotice && <p role="status" className="px-6 pb-3 text-xs text-emerald-700">{deliveryNotice}</p>}
      <div className="border-t border-slate-100 px-6 py-4">
        <p className="mb-3 text-[11px] font-semibold text-slate-600">Enviar orçamento ao cliente</p>
        {deliveryChannel ? (
          <form onSubmit={submitDelivery} className="space-y-3">
            <Field label={deliveryChannel === "email" ? "Email do destinatário" : "WhatsApp do destinatário (com código do país)"}>
              <input
                required
                type={deliveryChannel === "email" ? "email" : "tel"}
                value={recipient}
                onChange={(event) => setRecipient(event.target.value)}
                placeholder={deliveryChannel === "email" ? "cliente@empresa.com" : "+55 11 99999-9999"}
                className={inputClass}
              />
            </Field>
            <Field label="Mensagem (opcional)">
              <textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                rows={2}
                maxLength={deliveryChannel === "email" ? 2000 : 1000}
                placeholder="Mensagem que acompanha o PDF"
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/10"
              />
            </Field>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setDeliveryChannel(null)} className="h-9 rounded-xl px-3 text-xs font-semibold text-slate-600 hover:bg-slate-50">Voltar</button>
              <button disabled={sending} className="inline-flex h-9 items-center gap-2 rounded-xl bg-[var(--teal)] px-3 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-60">
                {deliveryChannel === "email" ? <Mail size={14} /> : <MessageCircle size={14} />}
                {sending ? "Enviando..." : "Enviar PDF"}
              </button>
            </div>
          </form>
        ) : (
          <div className="flex flex-wrap gap-2">
            <button onClick={() => openDelivery("email")} className="inline-flex h-9 items-center gap-2 rounded-xl border border-slate-200 px-3 text-xs font-semibold text-slate-600 hover:bg-slate-50"><Mail size={14} /> Enviar por email</button>
            <button onClick={() => openDelivery("whatsapp")} className="inline-flex h-9 items-center gap-2 rounded-xl border border-slate-200 px-3 text-xs font-semibold text-slate-600 hover:bg-slate-50"><MessageCircle size={14} /> Enviar por WhatsApp</button>
          </div>
        )}
      </div>
      <div className="flex flex-wrap justify-between gap-2 border-t border-slate-100 px-6 py-4">
        <div className="flex gap-2">
          <button
            onClick={() => void handleDownload()}
            disabled={downloading}
            className="inline-flex h-9 items-center gap-2 rounded-xl bg-[var(--teal)] px-3 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
          >
            <Download size={14} /> {downloading ? "Gerando PDF..." : "Baixar PDF"}
          </button>
          <a
            href={`/api/backend/quotes/${quote.id}/pdf?download=false`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-9 items-center gap-2 rounded-xl border border-slate-200 px-3 text-xs font-semibold text-slate-600 hover:bg-slate-50"
          >
            <Eye size={14} /> Visualizar
          </a>
        </div>
        <button onClick={onClose} className="h-9 rounded-xl px-4 text-xs font-semibold text-slate-600 hover:bg-slate-50">Fechar</button>
      </div>
    </ModalFrame>
  );
}

function ItemCostEditor({
  initialCost,
  onSave,
}: {
  initialCost: string;
  onSave: (unitCost: string) => Promise<void>;
}) {
  const [unitCost, setUnitCost] = useState(initialCost);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function saveCost(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onSave(unitCost);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <form onSubmit={(event) => void saveCost(event)} className="flex items-center gap-2">
        <input
          type="number"
          min="0"
          step="0.01"
          value={unitCost}
          onChange={(event) => setUnitCost(event.target.value)}
          placeholder="Custo unitário"
          aria-label="Custo unitário"
          className={`${inputClass} h-9 flex-1`}
        />
        <button
          disabled={busy}
          className="h-9 shrink-0 rounded-lg border border-slate-200 px-2.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          {busy ? "Salvando..." : "Salvar custo"}
        </button>
      </form>
      {error && <p role="alert" className="mt-1 text-[10px] text-rose-700">{error}</p>}
    </div>
  );
}

function ModalFrame({ title, subtitle, onClose, children }: { title: string; subtitle: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-[60] grid place-items-center overflow-y-auto bg-slate-950/40 p-4" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="my-auto max-h-[calc(100vh-32px)] w-full max-w-[600px] overflow-y-auto rounded-2xl bg-white shadow-2xl">
        <div className="flex items-start justify-between border-b border-slate-100 px-6 py-5">
          <div><h2 className="text-base font-bold text-[var(--navy)]">{title}</h2><p className="mt-1 text-xs text-slate-400">{subtitle}</p></div>
          <button onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100" aria-label="Fechar"><X size={17} /></button>
        </div>
        {children}
      </section>
    </div>
  );
}

function ModalActions({ onClose, busy, label }: { onClose: () => void; busy: boolean; label: string }) {
  return <div className="flex justify-end gap-2 border-t border-slate-100 px-6 py-4"><button type="button" onClick={onClose} className="h-10 rounded-xl px-4 text-xs font-semibold text-slate-600 hover:bg-slate-50">Cancelar</button><button disabled={busy} className="inline-flex h-10 items-center gap-2 rounded-xl bg-[var(--teal)] px-5 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-60"><Check size={15} />{busy ? "Salvando..." : label}</button></div>;
}

const inputClass = "h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-xs outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/10";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-1.5 block text-[11px] font-semibold text-slate-600">{label}</span>{children}</label>;
}
