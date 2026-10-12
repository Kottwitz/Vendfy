import { cookies } from "next/headers";
import { NextResponse } from "next/server";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

const TOKEN_COOKIE = "vendfy_access_token";

async function proxyRequest(request: Request, context: RouteContext) {
  const { path } = await context.params;
  const allowedPath =
    path[0] === "clients" ||
    path[0] === "quotes" ||
    (path[0] === "companies" && path[1] === "me" && path.length === 2) ||
    (path[0] === "users" && path[1] === "me" && path.length === 2);
  if (!allowedPath) {
    return NextResponse.json({ detail: "Rota não permitida." }, { status: 404 });
  }

  const upstreamUrl = new URL(
    `/${path.map(encodeURIComponent).join("/")}`,
    process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000",
  );
  upstreamUrl.search = new URL(request.url).search;

  const cookieStore = await cookies();
  const token = cookieStore.get(TOKEN_COOKIE)?.value;
  if (!token) {
    return NextResponse.json(
      { detail: "Autenticação necessária." },
      { status: 401 },
    );
  }

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  headers.set("authorization", `Bearer ${token}`);

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      method: request.method,
      headers,
      body:
        request.method === "GET" || request.method === "DELETE"
          ? undefined
          : await request.arrayBuffer(),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar à API Vendfy." },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  const upstreamContentType = upstream.headers.get("content-type");
  if (upstreamContentType) {
    responseHeaders.set("content-type", upstreamContentType);
  }
  const contentDisposition = upstream.headers.get("content-disposition");
  if (contentDisposition) {
    responseHeaders.set("content-disposition", contentDisposition);
  }
  const cacheControl = upstream.headers.get("cache-control");
  if (cacheControl) {
    responseHeaders.set("cache-control", cacheControl);
  }
  const nosniff = upstream.headers.get("x-content-type-options");
  if (nosniff) {
    responseHeaders.set("x-content-type-options", nosniff);
  }

  if (upstream.status === 401) {
    const response = NextResponse.json(
      { detail: "Sua sessão expirou. Entre novamente." },
      { status: 401 },
    );
    response.cookies.delete(TOKEN_COOKIE);
    return response;
  }
  if (upstream.status === 204) {
    return new NextResponse(null, { status: 204 });
  }
  return new NextResponse(await upstream.arrayBuffer(), {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
