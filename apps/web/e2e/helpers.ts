import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

export const MAILPIT = process.env.E2E_MAILPIT_URL ?? "http://localhost:8025";

export function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@hc-e2e.ch`;
}

/** Waits for the latest e-mail to `to` and returns the first link in it that contains `path`. */
export async function linkFromMail(page: Page, to: string, path: string): Promise<string> {
  // generous: during the full run the video analysis keeps the CPU busy
  for (let i = 0; i < 120; i++) {
    const res = await page.request.get(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:"${to}"`)}`);
    const { messages } = (await res.json()) as { messages: { ID: string }[] };
    if (messages.length > 0) {
      const msg = (await (await page.request.get(`${MAILPIT}/api/v1/message/${messages[0]!.ID}`)).json()) as {
        Text: string;
      };
      const match = msg.Text.match(new RegExp(`https?://\\S*${path}\\S*`));
      if (match) return match[0];
    }
    await page.waitForTimeout(250);
  }
  throw new Error(`no mail with ${path} for ${to}`);
}

export async function expectAccessible(page: Page) {
  // metadata (the <title>) is streamed after client-side navigations
  await expect.poll(() => page.title()).not.toBe("");
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  expect(
    result.violations.flatMap((v) => v.nodes.map((n) => `${v.id}: ${n.target.join(" ")} ${n.failureSummary ?? ""}`)),
  ).toEqual([]);
}

export async function register(page: Page, email: string, name = "Test Trainerin") {
  await page.goto("/register");
  await page.getByLabel("Vor- und Nachname").fill(name);
  await page.getByLabel("E-Mail").fill(email);
  await page.getByLabel("Passwort").fill("correct-horse-1");
  await page.getByLabel(/Nutzungsbedingungen/).check();
  await page.getByRole("button", { name: "Konto erstellen" }).click();
  // password hashing is deliberately slow; wait until the app has moved on
  await page.waitForURL((url) => !url.pathname.startsWith("/register"), { timeout: 30_000 });
}
