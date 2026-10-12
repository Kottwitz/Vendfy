import { NextResponse } from "next/server";

function backendUrl(path: string): string {
  const baseUrl = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";
  return new URL(path, baseUrl).toString();
}

export async function POST(request: Request) {
  const payload: unknown = await request.json();

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl("/register"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar à API Vendfy." },
      { status: 502 },
    );
  }

  const responseBody = await upstream.json().catch(() => null);
  return NextResponse.json(responseBody, { status: upstream.status });
}
