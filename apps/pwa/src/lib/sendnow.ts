// Sending is gated by what she agreed to: class counts only go out when she has switched that on.
import { hasConsent } from "./consent";
import { flush, type FlushResult } from "./sync";
import { flushFeedback } from "./feedback";

export async function flushAllowed(online: boolean): Promise<FlushResult> {
  if (hasConsent("feedback")) await flushFeedback(online);
  return hasConsent("counts") ? flush(online) : { sent: 0, failed: 0 };
}
