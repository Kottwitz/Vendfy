import { NextResponse } from "next/server";

const TOKEN_COOKIE = "vendfy_access_token";

function backendUrl(path: string): string {
  const baseUrl = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";
  return new URL(path, baseUrl).toString();
}

export async function POST(request: Request) {
  const body = await request.formData();
  const form = new URLSearchParams();
  form.set("username", String(body.get("email") ?? ""));
  form.set("password", String(body.get("password") ?? ""));

  let upstream: Response;
  try {
    upstream = await fetch(backendUrl("/token"), {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar à API Vendfy." },
      { status: 502 },
    );
  }

  if (!upstream.ok) {
    const detail =
      upstream.status === 403
        ? "Confirme seu email pelo link enviado antes de entrar."
        : "Email ou senha incorretos.";
    return NextResponse.json(
      { detail },
      { status: upstream.status },
    );
  }

  const tokenData = (await upstream.json()) as {
    access_token: string;
    token_type: string;
  };
  const response = NextResponse.json({ ok: true });
  response.cookies.set(TOKEN_COOKIE, tokenData.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 30 * 60,
  });
  return response;
}
