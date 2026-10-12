import type { ReactNode } from "react";
import { AppShell } from "@/components/app-shell";

export const instant = false;

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
