/** Drop-shaped mark cut by horizontal strata lines (SPEC.md §11.4). */
export function Wordmark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size * 1.25} viewBox="0 0 20 25" aria-hidden="true">
      <defs><clipPath id="kkdrop"><path d="M10 0 C10 0 1 11 1 16.5 A9 8.5 0 0 0 19 16.5 C19 11 10 0 10 0Z" /></clipPath></defs>
      <path d="M10 0 C10 0 1 11 1 16.5 A9 8.5 0 0 0 19 16.5 C19 11 10 0 10 0Z" fill="var(--ink)" />
      <g clipPath="url(#kkdrop)" stroke="var(--paper)" strokeWidth="1.1">
        <line x1="0" y1="12" x2="20" y2="12" /><line x1="0" y1="15.5" x2="20" y2="15.5" /><line x1="0" y1="19" x2="20" y2="19" />
      </g>
    </svg>
  );
}
