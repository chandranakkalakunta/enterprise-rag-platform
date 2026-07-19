export type UserRole = "viewer" | "content_admin" | "admin";

export interface MeResponse {
  uid: string;
  email: string;
  name: string;
  picture: string | null;
  role: UserRole;
}

export interface HealthResponse {
  status: string;
  service?: string;
  version: string;
  deployed_at: string;
}

export function canAccessAdmin(role: UserRole | null | undefined): boolean {
  return role === "content_admin" || role === "admin";
}
