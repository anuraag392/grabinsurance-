/**
 * ABBadge.jsx
 * Developer-mode badge displaying the assigned A/B variant.
 * Only renders in development (Vite's import.meta.env.DEV).
 */

export default function ABBadge({ variant }) {
    if (!import.meta.env.DEV || !variant) return null

    const colors =
        variant === 'A'
            ? 'bg-emerald-900/60 border-emerald-500/40 text-emerald-300'
            : 'bg-violet-900/60 border-violet-500/40 text-violet-300'

    return (
        <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colors}`}
        >
            <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
            Variant {variant}
        </span>
    )
}
