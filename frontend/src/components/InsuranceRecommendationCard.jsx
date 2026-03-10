/**
 * InsuranceRecommendationCard.jsx
 * Shows the AI-recommended insurance product with premium, coverage,
 * confidence score, risk tier selector, and coverage value bar.
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Shield, Star, Zap, ChevronDown } from 'lucide-react'

const TIER_CONFIG = {
    low: { label: 'Low Risk', color: 'text-emerald-400', bg: 'bg-emerald-900/30 border-emerald-500/30', modifier: 0.8 },
    medium: { label: 'Medium Risk', color: 'text-amber-400', bg: 'bg-amber-900/30 border-amber-500/30', modifier: 1.0 },
    high: { label: 'High Risk', color: 'text-red-400', bg: 'bg-red-900/30 border-red-500/30', modifier: 1.3 },
}

// Maps raw DB/API category slugs → clean display labels
const CATEGORY_LABELS = {
    // DB ORM slugs (insurance_recommender.py)
    travel_cancellation: 'Travel Insurance',
    travel_medical: 'Travel Medical',
    travel_baggage: 'Travel Insurance',
    device_protection: 'Device Protection',
    extended_warranty: 'Extended Warranty',
    theft_protection: 'Theft Protection',
    personal_accident: 'Personal Accident',
    critical_illness: 'Critical Illness',
    hospital_cash: 'Health Insurance',
    vehicle_damage: 'Vehicle Insurance',
    roadside_assistance: 'Vehicle Insurance',
    home_contents: 'Home Insurance',
    appliance_protection: 'Home Insurance',
    fire_damage: 'Home Insurance',
    // Catalog JSON categories
    travel: 'Travel Insurance',
    electronics: 'Device Protection',
    food: 'Food Delivery Cover',
    health: 'Health Insurance',
    fashion: 'Purchase Protection',
}

function categoryLabel(raw) {
    if (!raw) return ''
    return CATEGORY_LABELS[raw] ?? raw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}



function ConfidenceBadge({ confidence }) {
    const pct = Math.round(confidence * 100)
    const color = pct >= 80 ? 'text-emerald-400' : pct >= 60 ? 'text-amber-400' : 'text-slate-400'
    return (
        <div className="flex items-center gap-1.5">
            <div className={`flex gap-0.5 ${color}`}>
                {[1, 2, 3, 4, 5].map(i => (
                    <Star key={i} className={`w-3 h-3 ${i <= Math.ceil(pct / 20) ? 'fill-current' : 'opacity-20'}`} />
                ))}
            </div>
            <span className={`text-xs font-semibold ${color}`}>{pct}% match</span>
        </div>
    )
}

function CoverageBar({ premium, coverage, currency }) {
    const ratio = coverage > 0 ? Math.round(coverage / premium) : 0
    const barPct = Math.min((premium / coverage) * 800, 100)
    const symbol = currency === 'INR' ? '₹' : 'S$'
    return (
        <div className="space-y-2">
            <div className="flex justify-between text-xs text-slate-400">
                <span>Premium paid</span>
                <span>Max payout</span>
            </div>
            <div className="relative h-2 rounded-full bg-slate-800">
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${barPct}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                    className="absolute left-0 top-0 h-2 rounded-full bg-gradient-to-r from-brand-500 to-teal-400"
                />
            </div>
            <div className="flex justify-between text-xs">
                <span className="text-brand-400 font-semibold">{symbol}{Number(premium).toLocaleString()}</span>
                <span className="text-teal-400 font-semibold">{symbol}{Number(coverage).toLocaleString()}</span>
            </div>
            <p className="text-xs text-slate-500 text-center">
                {ratio}× payout on every premium paid
            </p>
        </div>
    )
}

export default function InsuranceRecommendationCard({ recommendation, deal, onTierChange }) {
    const [tier, setTier] = useState('medium')
    const [open, setOpen] = useState(false)

    if (!recommendation) return (
        <div className="rounded-2xl border border-slate-700/50 bg-slate-900/60 p-6 space-y-3 animate-pulse">
            <div className="h-5 w-2/3 rounded bg-slate-800" />
            <div className="h-4 w-1/2 rounded bg-slate-800" />
            <div className="h-16 rounded-xl bg-slate-800 mt-4" />
        </div>
    )

    const { product, quote, intent } = recommendation
    const tc = TIER_CONFIG[tier]
    const premium = quote?.final_premium ?? quote?.premium_price ?? 0
    const coverage = quote?.coverage_amount ?? 0
    const currency = deal?.currency || 'INR'
    const symbol = currency === 'INR' ? '₹' : 'S$'

    function handleTierChange(t) {
        setTier(t)
        setOpen(false)
        onTierChange?.(t)
    }

    return (
        <motion.div
            key={product?.name}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35 }}
            className="rounded-2xl border border-slate-700/50 overflow-hidden"
            style={{ background: 'linear-gradient(160deg, #0f1f2e 0%, #0a1525 100%)' }}
        >
            {/* Gradient top bar */}
            <div className="h-1 w-full bg-gradient-to-r from-brand-500 via-teal-400 to-emerald-400" />

            <div className="p-6 space-y-5">
                {/* Header */}
                <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-600/30 to-teal-500/20 border border-brand-500/30 flex items-center justify-center">
                            <Shield className="w-5 h-5 text-brand-400" />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-white leading-snug">{product?.name}</h3>
                            <p className="text-xs text-slate-500 capitalize mt-0.5">{categoryLabel(product?.category)}</p>
                        </div>
                    </div>
                    <ConfidenceBadge confidence={intent?.confidence || 0.75} />
                </div>

                {/* Description */}
                <p className="text-xs text-slate-400 leading-relaxed">{product?.description}</p>

                {/* Premium center stage */}
                <div className="rounded-xl bg-slate-800/70 border border-slate-700/40 p-4 text-center">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Your Premium</p>
                    <div className="flex items-baseline justify-center gap-1">
                        <span className="text-4xl font-extrabold text-white tracking-tight">
                            {symbol}{Number(premium).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                        <span className="text-sm text-slate-500">one-time</span>
                    </div>
                    <div className="flex items-center justify-center gap-1.5 mt-2">
                        <Zap className="w-3 h-3 text-amber-400" />
                        <span className="text-xs text-amber-400">Instant cover activated on checkout</span>
                    </div>
                </div>

                {/* Coverage bar */}
                <CoverageBar premium={premium} coverage={coverage} currency={currency} />

                {/* Risk tier picker */}
                <div className="space-y-1.5">
                    <label className="text-xs text-slate-500 uppercase tracking-wider">Your Risk Profile</label>
                    <div className="relative">
                        <button
                            onClick={() => setOpen(!open)}
                            className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl text-sm font-medium border transition-all ${tc.bg} ${tc.color}`}
                        >
                            <span>{tc.label}</span>
                            <ChevronDown className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`} />
                        </button>
                        {open && (
                            <div className="absolute z-10 mt-1.5 w-full rounded-xl border border-slate-700 bg-slate-900 shadow-xl overflow-hidden">
                                {Object.entries(TIER_CONFIG).map(([key, cfg]) => (
                                    <button
                                        key={key}
                                        onClick={() => handleTierChange(key)}
                                        className={`w-full text-left px-4 py-2.5 text-sm font-medium transition-colors hover:bg-slate-800 ${cfg.color} ${tier === key ? 'bg-slate-800' : ''}`}
                                    >
                                        {cfg.label}
                                        <span className="text-slate-500 font-normal ml-2 text-xs">×{cfg.modifier} modifier</span>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </motion.div>
    )
}
