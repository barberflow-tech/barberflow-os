// Ilustración del hero: poste de barbero, tijeras, navaja y peine dentro de un
// marco tipo espejo. Es decorativa (el texto de la página ya dice lo importante).

const ROJO = '#B3263B'
const ROJO_VIVO = '#E5283C'
const AZUL = '#174A7E'
const MARFIL = '#F7F1E8'

// Franjas del poste: paralelogramos con el mismo período (60 px) que el
// desplazamiento de la animación, para que el giro sea continuo.
const PERIODO = 60
const franjas = Array.from({ length: 9 }, (_, i) => i - 2).flatMap((i) =>
  [ROJO_VIVO, MARFIL, AZUL].map((color, j) => ({
    color,
    y: 96 + i * PERIODO + j * 20,
    clave: `${i}-${j}`,
  })),
)

export function IlustracionBarberia({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 520 480"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <radialGradient id="bf-resplandor" cx="50%" cy="50%" r="50%">
          <stop offset="0" stopColor={ROJO} stopOpacity=".4" />
          <stop offset="1" stopColor={ROJO} stopOpacity="0" />
        </radialGradient>
        <linearGradient id="bf-acero" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#8d99a6" />
          <stop offset=".5" stopColor="#f4f1ea" />
          <stop offset="1" stopColor="#5d6875" />
        </linearGradient>
        <linearGradient id="bf-laton" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#f1d9a0" />
          <stop offset=".55" stopColor="#c9a24d" />
          <stop offset="1" stopColor="#8a6a28" />
        </linearGradient>
        <linearGradient id="bf-vidrio" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#000" stopOpacity=".45" />
          <stop offset=".22" stopColor="#fff" stopOpacity=".22" />
          <stop offset=".4" stopColor="#fff" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity=".5" />
        </linearGradient>
        <clipPath id="bf-tubo">
          <rect x="318" y="96" width="92" height="262" rx="10" />
        </clipPath>
      </defs>

      {/* Resplandor y marco tipo espejo */}
      <circle cx="260" cy="250" r="230" fill="url(#bf-resplandor)" />
      <circle
        cx="260"
        cy="250"
        r="196"
        fill="none"
        stroke={MARFIL}
        strokeOpacity=".25"
        strokeWidth="1.5"
        strokeDasharray="3 9"
        strokeLinecap="round"
      />
      <circle
        cx="260"
        cy="250"
        r="170"
        fill="#16202B"
        stroke={MARFIL}
        strokeOpacity=".18"
        strokeWidth="2"
      />

      {/* Poste de barbero */}
      <g>
        <rect
          x="322"
          y="404"
          width="84"
          height="22"
          rx="4"
          fill="#101820"
          stroke={MARFIL}
          strokeOpacity=".25"
        />
        <path d="M306 402h116l-8-38H314z" fill="url(#bf-laton)" />
        <rect x="318" y="96" width="92" height="262" rx="10" fill={MARFIL} />
        <g clipPath="url(#bf-tubo)">
          <g className="bf-poste-gira">
            {franjas.map(({ color, y, clave }) => (
              <path
                key={clave}
                d={`M318 ${y}L410 ${y - 34}L410 ${y - 14}L318 ${y + 20}Z`}
                fill={color}
              />
            ))}
          </g>
        </g>
        <rect x="318" y="96" width="92" height="262" rx="10" fill="url(#bf-vidrio)" />
        <rect
          x="318"
          y="96"
          width="92"
          height="262"
          rx="10"
          fill="none"
          stroke="#5d6875"
          strokeWidth="2"
        />
        <path d="M306 100h116l-8 24H314z" fill="url(#bf-laton)" />
        <ellipse cx="364" cy="88" rx="34" ry="14" fill="url(#bf-laton)" />
        <circle cx="364" cy="70" r="14" fill="url(#bf-laton)" />
        <circle cx="359" cy="66" r="4" fill="#fff" fillOpacity=".55" />
      </g>

      {/* Tijeras */}
      <g transform="translate(150 180) rotate(-8)">
        <g className="bf-flota">
          <g transform="rotate(20)">
            <path
              d="M-7 0L7 0L3 -128L-3 -128Z"
              fill="url(#bf-acero)"
              stroke="#5d6875"
            />
            <path
              d="M-5 0L-9 62"
              stroke={ROJO_VIVO}
              strokeWidth="9"
              strokeLinecap="round"
            />
            <circle
              cx="-9"
              cy="88"
              r="24"
              fill="none"
              stroke={ROJO_VIVO}
              strokeWidth="9"
            />
          </g>
          <g transform="rotate(-20)">
            <path
              d="M-7 0L7 0L3 -128L-3 -128Z"
              fill="url(#bf-acero)"
              stroke="#5d6875"
            />
            <path
              d="M5 0L9 62"
              stroke={ROJO_VIVO}
              strokeWidth="9"
              strokeLinecap="round"
            />
            <circle
              cx="9"
              cy="88"
              r="24"
              fill="none"
              stroke={ROJO_VIVO}
              strokeWidth="9"
            />
          </g>
          <circle r="8" fill="#101820" stroke="url(#bf-laton)" strokeWidth="3" />
        </g>
      </g>

      {/* Navaja de afeitar */}
      <g transform="translate(110 360) rotate(24)">
        <g className="bf-flota bf-flota-b">
          <path
            d="M0 0h96c8 0 12 6 10 12-1 5-6 8-10 8H0z"
            fill="url(#bf-acero)"
            stroke="#5d6875"
          />
          <path
            d="M6 5h84"
            stroke="#fff"
            strokeOpacity=".6"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <rect
            x="-70"
            y="-2"
            width="76"
            height="24"
            rx="12"
            fill="#101820"
            stroke={MARFIL}
            strokeOpacity=".7"
            strokeWidth="2"
          />
          <circle cx="-56" cy="10" r="3" fill={ROJO_VIVO} />
          <circle cx="-40" cy="10" r="3" fill={MARFIL} />
          <circle cx="-24" cy="10" r="3" fill={AZUL} />
          <circle
            cx="4"
            cy="10"
            r="4"
            fill="#101820"
            stroke="url(#bf-laton)"
            strokeWidth="2"
          />
        </g>
      </g>

      {/* Peine */}
      <g transform="translate(210 74) rotate(-22)">
        <g className="bf-flota bf-flota-c">
          <rect x="0" y="0" width="120" height="18" rx="7" fill={MARFIL} />
          <g stroke={MARFIL} strokeWidth="3" strokeLinecap="round">
            <path d="M10 18v22M22 18v22M34 18v22M46 18v22M58 18v22M70 18v22M82 18v22M94 18v22M106 18v22" />
          </g>
          <path
            d="M6 6h108"
            stroke={ROJO}
            strokeOpacity=".55"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </g>
      </g>

      {/* Destellos */}
      <g fill={MARFIL}>
        <path
          className="bf-destello"
          d="M452 150l5 14 14 5-14 5-5 14-5-14-14-5 14-5z"
        />
        <path
          className="bf-destello bf-destello-b"
          d="M62 262l4 10 10 4-10 4-4 10-4-10-10-4 10-4z"
        />
        <path
          className="bf-destello bf-destello-c"
          d="M470 340l3 8 8 3-8 3-3 8-3-8-8-3 8-3z"
        />
      </g>
    </svg>
  )
}
