// The Open cohort chat button. It opens the cohort's thread and shows a badge for new posts from other
// teachers since she last opened it (the time is kept on this phone only). When the cohort has no chat (a
// cohort of one class) the button is hidden and "No peers yet" is shown. Offline it still opens the page and
// says new messages need a connection.
import { useEffect, useState } from "react";
import { chatState, type ChatState } from "../lib/modules";
import { href } from "../lib/router";
import { useApp } from "../state";

const seenKey = (trackId: string) => `cc.chatSeen.${trackId}`;

function readSeen(trackId: string): string | undefined {
  try {
    return localStorage.getItem(seenKey(trackId)) ?? undefined;
  } catch {
    return undefined;
  }
}

export function OpenChat({ trackId, testId = "open-chat" }: { trackId: string; testId?: string; hideWhenNone?: boolean }) { // hideWhenNone is ignored: the button never vanishes
  const { tr, online } = useApp();
  const [state, setState] = useState<ChatState | null>(null);
  useEffect(() => {
    let live = true;
    if (!online) return;
    chatState(trackId, readSeen(trackId)).then(
      (s) => live && setState(s),
      () => live && setState(null),
    );
    return () => {
      live = false;
    };
  }, [trackId, online]);

  if (state && !state.available) {
    // A cohort of one class has no chat. The button stays on the page (greyed out, with the reason) instead of vanishing
    // a moment after it loads.
    return (
      <div className="open-chat">
        <span className="btn btn-secondary is-disabled" aria-disabled="true" data-testid={`${testId}-disabled`}>
          {tr("module.chat.open")}
        </span>
        <span className="muted" data-testid={`${testId}-none`}>
          {" "}
          {tr("module.share.no_peers")}
        </span>
      </div>
    );
  }
  const opened = () => {
    try {
      localStorage.setItem(seenKey(trackId), new Date().toISOString());
    } catch {
      /* private window: the badge simply stays */
    }
  };
  return (
    <div className="open-chat">
      <a className="btn btn-secondary" href={href("/cohort_chat")} onClick={opened} data-testid={testId}>
        {tr("module.chat.open")}
        {state && state.unread > 0 ? (
          <span className="chip open-chat-badge" data-testid={`${testId}-unread`}>
            {" "}
            {tr("module.chat.unread", { n: state.unread })}
          </span>
        ) : null}
      </a>
      {!online ? (
        <span className="muted" data-testid={`${testId}-offline`}>
          {tr("module.chat.offline_note")}
        </span>
      ) : null}
    </div>
  );
}
