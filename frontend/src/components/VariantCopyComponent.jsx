/**
 * VariantCopyComponent.jsx
 * Displays the three AI-generated offer copy variants (A/B/C).
 * Users can select a preferred variant; active variant is highlighted.
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, Flame, TrendingUp, Heart, RefreshCw, Copy, Check } from 'lucide-react'

const TONE_CONFIG = {
    urgency: {
        label: 'Urgency',
        icon: Flame,
        color: 'text-orange-400',
        border: 'border-orange-500/40',
        bg: 'bg-orange-900/20',
        activeBg: 'bg-orange-900/40',
        ring: 'ring-orange-500/50',
        desc: 'Creates FOMO and risk awareness',
    },
    value: {
        label: 'Value',
        icon: TrendingUp,
        color: 'text-brand-400',
        border: 'border-brand-500/40',
        bg: 'bg-brand-900/20',
        activeBg: 'bg-brand-900/40',
        ring: 'ring-brand-500/50',
        desc: 'Highlights ROI and coverage ratio',
    },
    reassurance: {
        label: 'Reassurance',
        icon: Heart,
        color: 'text-emerald-400',
        border: 'border-emerald-500/40',
        bg: 'bg-emerald-900/20',
        activeBg: 'bg-emerald-900/40',
        ring: 'ring-emerald-500/50',
        desc: 'Builds trust and peace of mind',
    },
}

function CopyChip({ copied, onCopy }) {
    return (
        <button
            onClick={onCopy}
            className="absolute top-3 right-3 p-1.5 rounded-lg transition-all text-slate-500 hover:text-slate-200 hover:bg-slate-700/60"
            title="Copy message"
        >
            {copied
                ? <Check className="w-3.5 h-3.5 text-emerald-400" />
                : <Copy className="w-3.5 h-3.5" />
            }
        </button>
    )
}

function VariantCard({ v, isSelected, onClick }) {
    const [copied, setCopied] = useState(false)
    const tc = TONE_CONFIG[v.tone] || TONE_CONFIG.value
    const Icon = tc.icon

    function handleCopy(e) {
        e.stopPropagation()
        navigator.clipboard.writeText(v.message).then(() => {
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        })
    }

    return (
        <motion.div
            layout
            onClick={onClick}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            className={`
        relative p-4 rounded-xl border cursor-pointer transition-all duration-200
        ${isSelected
                    ? `${tc.activeBg} ${tc.border} ring-1 ${tc.ring}`
                    : `${tc.bg} border-slate-700/50 hover:border-slate-600/60`
                }
      `}
        >
            {/* Tone badge */}
            <div className={`flex items-center gap-1.5 mb-2.5 ${tc.color}`}>
                <Icon className="w-3.5 h-3.5" />
                <span className="text-xs font-bold uppercase tracking-wider">{tc.label}</span>
                <span className="text-xs text-slate-500 font-normal normal-case ml-1">{tc.desc}</span>
            </div>

            {/* Message */}
            <p className="text-sm text-slate-200 leading-relaxed pr-8">{v.message}</p>

            {/* Char count */}
            <div className="flex items-center justify-between mt-2.5">
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${isSelected ? `${tc.color} ${tc.bg} border ${tc.border}` : 'text-slate-600 bg-slate-800'
                    }`}>
                    Variant {v.variant}
                </span>
                <span className="text-xs text-slate-600">{v.chars} chars</span>
            </div>

            <CopyChip copied={copied} onCopy={handleCopy} />

            {/* Selected ring pulse */}
            {isSelected && (
                <div className={`absolute inset-0 rounded-xl ring-1 ${tc.ring} pointer-events-none`} />
            )}
        </motion.div>
    )
}

export default function VariantCopyComponent({ variants, isLoading, onRefresh, selectedVariant, onSelect }) {
    const [hovered, setHovered] = useState(null)

    if (isLoading) return (
        <div className="rounded-2xl border border-slate-700/50 bg-slate-900/60 p-5 space-y-3">
            <div className="h-4 w-40 rounded bg-slate-800 animate-pulse" />
            {[0, 1, 2].map(i => (
                <div key={i} className="h-20 rounded-xl bg-slate-800 animate-pulse" style={{ animationDelay: `${i * 0.1}s` }} />
            ))}
        </div>
    )

    if (!variants?.length) return null

    return (
        <div className="rounded-2xl border border-slate-700/50 overflow-hidden"
            style={{ background: 'linear-gradient(160deg, #0d1b2a 0%, #0a1320 100%)' }}>

            {/* Header */}
            <div className="px-5 pt-5 pb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-brand-400" />
                    <h4 className="text-sm font-bold text-white">AI Offer Copy</h4>
                    <span className="text-xs text-slate-500">— pick the message that resonates</span>
                </div>
                {onRefresh && (
                    <button
                        onClick={onRefresh}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-brand-400 hover:bg-brand-900/20 transition-all"
                        title="Regenerate copy"
                    >
                        <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                )}
            </div>

            {/* Variant cards */}
            <div className="px-5 pb-5 space-y-2.5">
                <AnimatePresence mode="wait">
                    {variants.map(v => (
                        <VariantCard
                            key={v.variant + v.tone}
                            v={v}
                            isSelected={selectedVariant === v.variant}
                            onClick={() => onSelect?.(v.variant)}
                        />
                    ))}
                </AnimatePresence>
            </div>
        </div>
    )
}
