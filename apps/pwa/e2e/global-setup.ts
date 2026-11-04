// The API needs a signed-in user for every route: register the tests' user on both test APIs (a second run
// finds the nickname taken, which is fine).
export default async function globalSetup(): Promise<void> {
  for (const port of [8011, 8012]) {
    try {
      await fetch(`http://localhost:${port}/api/users/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ nickname: "e2e tester" }) });
    } catch {
      /* the second API is only needed by the AI-off spec */
    }
  }
}
