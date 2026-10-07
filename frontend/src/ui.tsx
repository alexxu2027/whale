import type { ComponentProps, ReactNode } from 'react'
import { cx } from './format'

type Tone = 'gold' | 'buy' | 'sell' | 'ghost' | 'plain'

const TONES: Record<Tone, string> = {
  gold: 'bg-gold-400 text-velvet-950 hover:bg-gold-300 shadow-[0_4px_0_var(--color-gold-500)] active:translate-y-0.5 active:shadow-none',
  buy: 'bg-buy-400 text-velvet-950 hover:brightness-110 shadow-[0_4px_0_var(--color-buy-500)] active:translate-y-0.5 active:shadow-none',
  sell: 'bg-sell-400 text-velvet-950 hover:brightness-110 shadow-[0_4px_0_var(--color-sell-500)] active:translate-y-0.5 active:shadow-none',
  ghost: 'bg-transparent text-velvet-200 ring-1 ring-velvet-600 hover:bg-velvet-800',
  plain: 'bg-velvet-700 text-white hover:bg-velvet-600',
}

export function Button({
  tone = 'plain',
  className,
  children,
  ...rest
}: ComponentProps<'button'> & { tone?: Tone }) {
  return (
    <button
      type="button"
      {...rest}
      className={cx(
        'rounded-xl px-4 py-2.5 font-bold transition disabled:opacity-40 disabled:shadow-none disabled:translate-y-0',
        TONES[tone],
        className,
      )}
    >
      {children}
    </button>
  )
}

export function Card({ title, children, className, accent }: { title?: ReactNode; children: ReactNode; className?: string; accent?: string }) {
  return (
    <section className={cx('rounded-2xl bg-velvet-800/80 p-4 ring-1 ring-velvet-700 backdrop-blur', className)}>
      {title && (
        <h2 className={cx('mb-2 text-xs font-extrabold uppercase tracking-widest', accent ?? 'text-velvet-400')}>{title}</h2>
      )}
      {children}
    </section>
  )
}

/** A big number with − / + buttons. */
export function Stepper({
  value,
  onChange,
  min,
  max,
  label,
  tone,
}: {
  value: number
  onChange: (v: number) => void
  min: number
  max: number
  label?: string
  tone?: 'buy' | 'sell'
}) {
  const clamp = (v: number) => Math.min(max, Math.max(min, v))
  const color = tone === 'buy' ? 'text-buy-400' : tone === 'sell' ? 'text-sell-400' : 'text-white'
  return (
    <div className="flex flex-col items-center gap-1">
      {label && <div className="text-[11px] font-extrabold uppercase tracking-widest text-velvet-400">{label}</div>}
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          aria-label={`Lower ${label ?? 'value'}`}
          className="h-9 w-9 rounded-lg bg-velvet-700 text-xl font-bold hover:bg-velvet-600"
          onClick={() => onChange(clamp(value - 1))}
        >
          −
        </button>
        <input
          aria-label={label}
          inputMode="numeric"
          value={value}
          onChange={(e) => {
            const n = parseInt(e.target.value.replace(/\D/g, ''), 10)
            if (!Number.isNaN(n)) onChange(clamp(n))
          }}
          className={cx('w-16 rounded-lg bg-velvet-950/60 py-1 text-center font-display text-3xl outline-none ring-1 ring-velvet-700 focus:ring-gold-400', color)}
        />
        <button
          type="button"
          aria-label={`Raise ${label ?? 'value'}`}
          className="h-9 w-9 rounded-lg bg-velvet-700 text-xl font-bold hover:bg-velvet-600"
          onClick={() => onChange(clamp(value + 1))}
        >
          +
        </button>
      </div>
    </div>
  )
}

export function Pill({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cx('rounded-full px-2 py-0.5 text-[11px] font-bold', className)}>{children}</span>
}
