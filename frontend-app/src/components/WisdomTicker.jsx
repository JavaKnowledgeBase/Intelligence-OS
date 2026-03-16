import { useEffect, useMemo, useState } from "react";
import { wisdomCategories } from "../data/wisdomLines";

const TOTAL_WINDOW_MS = 16000;
const TYPING_WINDOW_MS = 10000;

function getActiveQuote(rotationIndex) {
  const categoryIndex = rotationIndex % wisdomCategories.length;
  const category = wisdomCategories[categoryIndex];
  const line = category.items[Math.floor(rotationIndex / wisdomCategories.length) % category.items.length];

  return {
    category: category.category,
    line,
  };
}

// Single-quote ticker for the login page, rotating across categories one at a time.
export function WisdomTicker() {
  const [rotationIndex, setRotationIndex] = useState(0);
  const [typedText, setTypedText] = useState("");
  const activeQuote = useMemo(() => getActiveQuote(rotationIndex), [rotationIndex]);

  useEffect(() => {
    let charIndex = 0;
    setTypedText("");

    const typingIntervalMs = Math.max(24, Math.floor(TYPING_WINDOW_MS / activeQuote.line.length));
    const typeInterval = window.setInterval(() => {
      charIndex += 1;
      setTypedText(activeQuote.line.slice(0, charIndex));
      if (charIndex >= activeQuote.line.length) {
        window.clearInterval(typeInterval);
      }
    }, typingIntervalMs);

    const advanceTimer = window.setTimeout(() => {
      setRotationIndex((current) => current + 1);
    }, TOTAL_WINDOW_MS);

    return () => {
      window.clearInterval(typeInterval);
      window.clearTimeout(advanceTimer);
    };
  }, [activeQuote]);

  return (
    <section className="wisdom-ticker" aria-live="polite">
      <span>{activeQuote.category}</span>
      <p>{typedText}</p>
    </section>
  );
}

