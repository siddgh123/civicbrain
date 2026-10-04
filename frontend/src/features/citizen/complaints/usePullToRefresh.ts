import { useEffect, useRef, useState } from 'react';

const PULL_PX = 80;

/**
 * Pull-to-refresh for a mobile list (docs/05_UI_SPEC.md §4.6): a downward swipe of more than 80 px that starts at the
 * top of the page calls `onRefresh` on release. Returns true while the pull is far enough ("Release to refresh").
 * The page also has a Refresh button (keyboard and desktop users).
 */
export function usePullToRefresh(onRefresh: () => void): boolean {
  const [ready, setReady] = useState(false);
  const callback = useRef(onRefresh);
  useEffect(() => {
    callback.current = onRefresh;
  });

  useEffect(() => {
    let startY: number | null = null;
    let armed = false;
    const onStart = (event: TouchEvent) => {
      startY = window.scrollY <= 0 ? (event.touches[0]?.clientY ?? null) : null;
    };
    const onMove = (event: TouchEvent) => {
      if (startY === null) return;
      armed = (event.touches[0]?.clientY ?? startY) - startY > PULL_PX;
      setReady(armed);
    };
    const onEnd = () => {
      if (armed) callback.current();
      startY = null;
      armed = false;
      setReady(false);
    };
    window.addEventListener('touchstart', onStart, { passive: true });
    window.addEventListener('touchmove', onMove, { passive: true });
    window.addEventListener('touchend', onEnd);
    window.addEventListener('touchcancel', onEnd);
    return () => {
      window.removeEventListener('touchstart', onStart);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend', onEnd);
      window.removeEventListener('touchcancel', onEnd);
    };
  }, []);

  return ready;
}
