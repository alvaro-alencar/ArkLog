export const ARK_SESSION_KEY = 'ark_session';

export function getArkSessionToken(): string {
  return window.localStorage.getItem(ARK_SESSION_KEY) || '';
}

export function clearArkSession(): void {
  window.localStorage.removeItem(ARK_SESSION_KEY);
  window.localStorage.removeItem('arklog_account');
}
