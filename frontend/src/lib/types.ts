export type User = {
  id: string;
  company_id: string;
  name: string;
  email: string;
  role: string;
  created_at: string;
};

export type CompanySettings = {
  id: string;
  name: string;
  document: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  whatsapp_phone_number_id: string | null;
  whatsapp_configured: boolean;
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_username: string | null;
  smtp_security: "starttls" | "ssl";
  smtp_configured: boolean;
};

export type Client = {
  id: string;
  company_id: string;
  name: string;
  phone: string | null;
  email: string | null;
  document: string | null;
  address: string | null;
  created_at: string;
  updated_at: string;
};

export type QuoteStatus =
  | "DRAFT"
  | "SENT"
  | "VIEWED"
  | "APPROVED"
  | "REJECTED"
  | "EXPIRED"
  | "CANCELLED";

export type QuoteItem = {
  id: string;
  quote_id: string;
  description: string;
  quantity: string;
  unit_price: string;
  unit_cost: string | null;
  total: string;
};

export type Quote = {
  id: string;
  company_id: string;
  client_id: string;
  number: number;
  status: QuoteStatus;
  subtotal: string;
  discount: string;
  total: string;
  description: string | null;
  valid_until: string | null;
  created_at: string;
  updated_at: string;
  items: QuoteItem[];
};

export type QuoteFinancialSummary = {
  gross_revenue: string;
  expenses: string;
  profit: string;
  missing_cost_items: number;
};

export type ApiError = {
  detail?: string | Array<{ msg?: string }>;
};
