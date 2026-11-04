export type RoleType = "admin" | "researcher" | "reviewer" | "viewer";

export interface User {
  id: string;
  email: string;
  name: string;
  role: RoleType;
  created_at: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface DemoUser {
  email: string;
  name: string;
  role: RoleType;
  password: string;
  description: string;
}
