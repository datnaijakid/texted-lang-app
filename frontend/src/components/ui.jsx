export function Card({ children, className = '', ...props }) {
  return (
    <div
      className={`bg-base-900 border border-base-700 rounded-xl2 ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}

export function Button({ children, variant = 'primary', className = '', ...props }) {
  const base = 'px-5 py-2.5 rounded-xl font-semibold transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed'
  const variants = {
    primary: 'bg-accent text-base-950 hover:brightness-110 active:scale-[0.98]',
    ghost: 'bg-base-800 text-white hover:bg-base-700 active:scale-[0.98]',
    outline: 'border border-base-600 text-white hover:bg-base-800 active:scale-[0.98]',
  }
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  )
}

export function ProgressBar({ value, max }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0
  return (
    <div className="w-full h-2 bg-base-800 rounded-full overflow-hidden">
      <div
        className="h-full bg-accent transition-all duration-300 ease-out"
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

export function StreakBadge({ streak }) {
  return (
    <div className="flex items-center gap-1.5 bg-base-800 border border-base-700 rounded-full px-3 py-1.5">
      <span className="text-orange-400">🔥</span>
      <span className="font-semibold text-sm">{streak}</span>
    </div>
  )
}
