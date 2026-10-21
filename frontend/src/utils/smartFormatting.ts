// Smart Formatting Utilities – applied client-side after Whisper returns text.

export interface SmartFormattingOptions {
  autoCapitalize: boolean;
  paragraphBreaks: boolean;
  numberFormatting: boolean;
  smartQuotes: boolean;
}

// ─── Number word maps ───

const ONES: Record<string, number> = {
  zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5,
  six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15,
  sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19,
};

const TENS: Record<string, number> = {
  twenty: 20, thirty: 30, forty: 40, fifty: 50,
  sixty: 60, seventy: 70, eighty: 80, ninety: 90,
};

/**
 * Converts simple spoken number phrases to digits.
 * e.g. "twenty five" → "25", "one hundred" → "100"
 */
function convertSpokenNumbers(text: string): string {
  // Handle compound numbers like "twenty-five" or "twenty five"
  let result = text;

  // Replace hyphenated compound numbers first
  result = result.replace(
    /\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[-\s](one|two|three|four|five|six|seven|eight|nine)\b/gi,
    (match, tens, ones) => {
      const t = TENS[tens.toLowerCase()];
      const o = ONES[ones.toLowerCase()];
      return t !== undefined && o !== undefined ? String(t + o) : match;
    }
  );

  // Replace standalone tens
  result = result.replace(
    /\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\b/gi,
    (match) => {
      const v = TENS[match.toLowerCase()];
      return v !== undefined ? String(v) : match;
    }
  );

  // Replace "X hundred [and Y]"
  result = result.replace(
    /\b(one|two|three|four|five|six|seven|eight|nine)\s+hundred(?:\s+and\s+(\w+))?\b/gi,
    (match, hundreds, rest) => {
      const h = ONES[hundreds.toLowerCase()];
      if (h === undefined) return match;
      let base = h * 100;
      if (rest) {
        const r = ONES[rest.toLowerCase()] ?? TENS[rest.toLowerCase()];
        if (r !== undefined) base += r;
        else return match;
      }
      return String(base);
    }
  );

  // Replace standalone ones/teens
  result = result.replace(/\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen)\b/gi, (match) => {
    const v = ONES[match.toLowerCase()];
    return v !== undefined ? String(v) : match;
  });

  return result;
}

/**
 * Capitalise the first letter of every sentence.
 * Sentences end with . ! ? or are the start of the string.
 */
function capitalizeSentences(text: string): string {
  // Capitalize very first character
  let result = text.charAt(0).toUpperCase() + text.slice(1);
  // Capitalize after . ! ?
  result = result.replace(/([.!?]\s+)([a-z])/g, (_, punct, letter) => punct + letter.toUpperCase());
  return result;
}

/**
 * Convert straight quotes to curly (typographic) quotes.
 */
function applySmartQuotes(text: string): string {
  return text
    .replace(/"([^"]*)"/g, '\u201C$1\u201D')  // "..." → "..."
    .replace(/'([^']*)'/g, '\u2018$1\u2019');   // '...' → '...'
}

/**
 * Add paragraph breaks where Whisper included long pauses (indicated by
 * multiple spaces or explicit ". " at sentence end). This is a heuristic.
 */
function addParagraphBreaks(text: string): string {
  // After 3+ sentences (ends with . ! ?) add a paragraph break
  return text.replace(/([.!?])\s{2,}/g, '$1\n\n');
}

// ─── Main export ───

/**
 * Apply smart formatting to a transcribed text chunk.
 */
export function applySmartFormatting(
  text: string,
  options: SmartFormattingOptions
): string {
  if (!text || !text.trim()) return text;

  let result = text.trim();

  if (options.numberFormatting) {
    result = convertSpokenNumbers(result);
  }

  if (options.autoCapitalize) {
    result = capitalizeSentences(result);
  }

  if (options.paragraphBreaks) {
    result = addParagraphBreaks(result);
  }

  if (options.smartQuotes) {
    result = applySmartQuotes(result);
  }

  return result;
}

/**
 * Format a timestamp for display in the history list.
 */
export function formatTimestamp(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: diffDays > 365 ? 'numeric' : undefined,
    });
  } catch {
    return '';
  }
}

/**
 * Returns a short preview (first N chars) of a transcription.
 */
export function textPreview(text: string, maxChars: number = 80): string {
  if (!text) return '';
  const clean = text.replace(/\n+/g, ' ').trim();
  if (clean.length <= maxChars) return clean;
  return clean.slice(0, maxChars).trimEnd() + '…';
}
