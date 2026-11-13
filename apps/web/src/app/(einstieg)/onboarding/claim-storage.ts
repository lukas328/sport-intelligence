// a claimed team waits for «Das ist mein Team» also across a reload (UX test B24): the claim in
// the session storage, a cookie tells the server page not to send the coach into the app yet
export const CLAIM_KEY = "hb_claim";
export const CONFIRM_COOKIE = "hb_confirm";

export function forgetClaim() {
  try {
    window.sessionStorage.removeItem(CLAIM_KEY);
  } catch {
    /* storage unavailable */
  }
  document.cookie = `${CONFIRM_COOKIE}=; path=/; max-age=0; samesite=lax`;
}
