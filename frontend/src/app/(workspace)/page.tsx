"use client";

import {
  ArrowUpRight,
  BadgeDollarSign,
  FilePlus2,
  Plus,
  Receipt,
  TrendingUp,
  UsersRound,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { apiRequest, formatCurrency, formatDate } from "@/lib/api";
import type { Client, Quote, QuoteFinancialSummary } from "@/lib/types";

const statusLabel: Record<string, string> = {
  DRAFT: "Rascunho",
  SENT: "Enviado",
  VIEWED: "Visualizado",
  APPROVED: "Aprovado",
  REJECTED: "Recusado",
  EXPIRED: "Expirado",
  CANCELLED: "Cancelado",
};

export default function DashboardPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [financialSummary, setFinancialSummary] = useState<QuoteFinancialSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiRequest<Client[]>("clients?limit=100"),
      apiRequest<Quote[]>("quotes?limit=100"),
      apiRequest<QuoteFinancialSummary>("quotes/summary"),
    ])
      .then(([clientData, quoteData, summary]) => {
        setClients(clientData);
        setQuotes(quoteData);
        setFinancialSummary(summary);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  const activeQuotes = quotes.filter((quote) =>
    ["DRAFT", "SENT", "VIEWED"].includes(quote.status),
  );
  const recentQuotes = [...quotes]
    .sort((left, right) => right.created_at.localeCompare(left.created_at))
    .slice(0, 5);

  return (
    <div className="space-y-8">
      <section className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-teal-700">
            {new Intl.DateTimeFormat("pt-BR", {
              weekday: "long",
              day: "numeric",
              month: "long",
            }).format(new Date())}
          </p>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--navy)] sm:text-[30px]">
            Visão geral
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Acompanhe o que está acontecendo no seu negócio.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/clients"
            className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-xs font-semibold text-slate-700 transition hover:border-slate-300"
          >
            <Plus size={15} /> Novo cliente
          </Link>
          <Link
            href="/quotes"
            className="inline-flex h-10 items-center gap-2 rounded-xl bg-[var(--teal)] px-4 text-xs font-semibold text-white shadow-sm transition hover:bg-teal-800"
          >
            <FilePlus2 size={15} /> Criar orçamento
          </Link>
        </div>
      </section>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Clientes cadastrados"
          value={String(clients.length)}
          footnote="Na sua carteira"
          icon={UsersRound}
          tone="teal"
        />
        <MetricCard
          label="Orçamentos ativos"
          value={String(activeQuotes.length)}
          footnote="Rascunhos, enviados e visualizados"
          icon={FilePlus2}
          tone="blue"
        />
        <MetricCard
          label="Aprovados"
          value={String(quotes.filter((quote) => quote.status === "APPROVED").length)}
          footnote="Orçamentos ganhos"
          icon={TrendingUp}
          tone="green"
        />
        <MetricCard
          label="Faturamento bruto"
          value={formatCurrency(Number(financialSummary?.gross_revenue ?? 0))}
          footnote="Total dos orçamentos aprovados"
          icon={ArrowUpRight}
          tone="amber"
        />
        <MetricCard
          label="Gastos"
          value={formatCurrency(Number(financialSummary?.expenses ?? 0))}
          footnote="Custos informados nos aprovados"
          icon={Receipt}
          tone="blue"
        />
        <MetricCard
          label="Lucro estimado"
          value={formatCurrency(Number(financialSummary?.profit ?? 0))}
          footnote="Aprovados menos custos informados"
          icon={BadgeDollarSign}
          tone="green"
        />
      </section>
      {Boolean(financialSummary?.missing_cost_items) && (
        <p className="-mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-800">
          O lucro é parcial: informe os custos de {financialSummary?.missing_cost_items} item(ns) em orçamentos aprovados para completar o cálculo.
        </p>
      )}

      <section className="grid gap-5 xl:grid-cols-[1.55fr_1fr]">
        <div className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
            <div>
              <h2 className="text-sm font-bold text-[var(--navy)]">Orçamentos recentes</h2>
              <p className="mt-1 text-xs text-slate-400">Atividade comercial da sua empresa</p>
            </div>
            <Link href="/quotes" className="text-xs font-semibold text-teal-700 hover:text-teal-900">
              Ver todos <ArrowUpRight className="ml-1 inline" size={13} />
            </Link>
          </div>
          {recentQuotes.length ? (
            <div className="divide-y divide-slate-100">
              {recentQuotes.map((quote) => {
                const customer = clients.find((client) => client.id === quote.client_id);
                return (
                  <div key={quote.id} className="flex items-center gap-3 px-5 py-4 sm:px-6">
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-slate-50 text-slate-500">
                      <FilePlus2 size={17} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-semibold text-slate-800">
                        Orçamento #{quote.number} · {customer?.name ?? "Cliente"}
                      </p>
                      <p className="mt-1 text-[11px] text-slate-400">{formatDate(quote.created_at)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs font-bold text-slate-800">{formatCurrency(quote.total)}</p>
                      <p className="mt-1 text-[10px] text-slate-400">{statusLabel[quote.status]}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyState
              title="Ainda não há orçamentos"
              action="Criar o primeiro"
              href="/quotes"
            />
          )}
        </div>

        <div className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
            <div>
              <h2 className="text-sm font-bold text-[var(--navy)]">Clientes recentes</h2>
              <p className="mt-1 text-xs text-slate-400">Relacionamentos adicionados</p>
            </div>
            <Link href="/clients" className="text-xs font-semibold text-teal-700 hover:text-teal-900">
              Ver todos <ArrowUpRight className="ml-1 inline" size={13} />
            </Link>
          </div>
          {clients.length ? (
            <div className="divide-y divide-slate-100">
              {[...clients].slice(0, 5).map((client) => (
                <div key={client.id} className="flex items-center gap-3 px-5 py-3.5 sm:px-6">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#e4f0ee] text-xs font-bold text-teal-800">
                    {client.name.slice(0, 1).toUpperCase()}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold text-slate-800">{client.name}</p>
                    <p className="truncate text-[11px] text-slate-400">{client.email ?? client.phone ?? "Sem contato informado"}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="Sua carteira começa aqui" action="Adicionar cliente" href="/clients" />
          )}
        </div>
      </section>
    </div>
  );
}

function MetricCard({
  label,
  value,
  footnote,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  footnote: string;
  icon: typeof UsersRound;
  tone: "teal" | "blue" | "green" | "amber";
}) {
  const tones = {
    teal: "bg-teal-50 text-teal-700",
    blue: "bg-blue-50 text-blue-700",
    green: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
  };
  return (
    <div className="rounded-2xl border border-[var(--line)] bg-white p-5">
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <span className={`grid h-9 w-9 place-items-center rounded-xl ${tones[tone]}`}>
          <Icon size={17} />
        </span>
      </div>
      <p className="mt-4 text-[25px] font-bold tracking-tight text-[var(--navy)]">{value}</p>
      <p className="mt-1 text-[11px] text-slate-400">{footnote}</p>
    </div>
  );
}

function EmptyState({
  title,
  action,
  href,
}: {
  title: string;
  action: string;
  href: string;
}) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center px-6 text-center">
      <span className="grid h-11 w-11 place-items-center rounded-2xl bg-slate-50 text-slate-400">
        <FilePlus2 size={19} />
      </span>
      <p className="mt-3 text-xs font-semibold text-slate-600">{title}</p>
      <Link href={href} className="mt-2 text-xs font-semibold text-teal-700 hover:underline">
        {action}
      </Link>
    </div>
  );
}
