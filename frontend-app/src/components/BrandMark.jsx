// Developer: Ravi Kafley
// Local Torilaure logo lockup copied into this project and recolored from the broader product-family styling.
export function BrandMark({ compact = false }) {
  return (
    <div className={`brand-lockup ${compact ? "brand-lockup-compact" : ""}`} aria-label="Torilaure Intelligence OS brand">
      <div className="brand-logo" aria-hidden="true">
        <svg viewBox="0 0 660 140" role="img">
          <defs>
            <linearGradient id="torilaureBlueGreen" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#5fb8f0" />
              <stop offset="48%" stopColor="#7fd4c4" />
              <stop offset="100%" stopColor="#2c7984" />
            </linearGradient>
          </defs>
          <g transform="translate(6,16)">
            <path d="M36 92c26-34 60-54 98-58" stroke="#c7ccd7" strokeWidth="10" fill="none" strokeLinecap="round" />
            <path d="M28 72c12-10 24-12 36 2" stroke="#8a93a4" strokeWidth="12" fill="none" strokeLinecap="round" />
            <path d="M68 40c-9-8-15-16-19-25" stroke="#c0c7d3" strokeWidth="11" fill="none" strokeLinecap="round" />
            <path d="M88 44c-11-5-18-13-24-23" stroke="#98a0b1" strokeWidth="11" fill="none" strokeLinecap="round" />
            <path d="M66 104c8-24 26-38 52-36" stroke="url(#torilaureBlueGreen)" strokeWidth="10" fill="none" strokeLinecap="round" />
            <path d="M106 74c11 1 21 8 27 20" stroke="#6cbcae" strokeWidth="12" fill="none" strokeLinecap="round" />
            <circle cx="20" cy="62" r="8" fill="#bec6d2" />
            <circle cx="86" cy="26" r="6" fill="#c7ccd7" />
            <circle cx="116" cy="66" r="7" fill="#7fd4c4" />
            <circle cx="56" cy="104" r="8" fill="#5fb8f0" />
          </g>
          <text x="170" y="68" fontSize="68" fill="#8cd7ca" fontWeight="700" fontFamily="Space Grotesk, Segoe UI, sans-serif">
            Torilaure
          </text>
          {!compact && (
            <text x="170" y="120" fontSize="54" fill="#d8deea" fontWeight="600" fontFamily="Space Grotesk, Segoe UI, sans-serif">
              Intelligence OS
            </text>
          )}
        </svg>
      </div>
    </div>
  );
}
