// The access token lives only in this module's memory (rule 20: never localStorage/sessionStorage). AuthProvider
// writes it; the API client reads it for the bearer header. A page reload forgets it - P07 restores the session with
// the refresh cookie.
let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function clearAccessToken(): void {
  accessToken = null;
}
