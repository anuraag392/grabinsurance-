/**
 * InsuranceOfferModal.jsx
 * Animated modal presenting the Claude-generated insurance offer.
 * Variant A = standard layout, Variant B = urgency badge + social proof.
 * Tracks impression on mount, click/accept/decline on interaction.
 */

import { useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Shield, X, CheckCircle2, ChevronRight, Clock, Users, Star, Zap,
} from 'lucide-react'
import { trackEvent } from '../api/client'
import ABBadge from './ABBadge'

const CATEGORY_COLOR = {
    travel: { from: '#0ea5e9', to: '#6366f1' },
    electronics: { from: '#3b82f6', to: '#06b6d4' },
    health: { from: '#10b981', to: '#06b6d4' },
    vehicle: { from: '#f59e0b', to: '#ef4444' },
    home: { from: '#8b5cf6', to: '#ec4899' },
    general: { from: '#5b8af5', to: '#a78bfa' },
}

function VariantBBadge() {
    return (
        <div className="flex items-center gap-4 mb-4">
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-900/40 border border-amber-500/30 text-amber-300 text-xs font-semibold">
                <Clock className="w-3 h-3" /> Limited-time offer
            </span>
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-900/40 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
                <Users className="w-3 h-3" /> 2,418 added this week
            </span>
        </div>
    )
}

export default function InsuranceOfferModal({ recommendation, onAccept, onDecline, onClose }) {
    const { recommendation_id, intent, product, quote, variant, copy } = recommendation
    const intentKey = intent?.intent || 'general'
    const colors = CATEGORY_COLOR[intentKey] || CATEGORY_COLOR.general

    // Track impression once on mount
    useEffect(() => {
        trackEvent({
            user_id: 'frontend_user',
            recommendation_id,
            event_type: 'impression',
            variant,
            category: product?.category || '',
        }).catch(() => { })
    }, [recommendation_id])

    const handleClick = useCallback(() => {
        trackEvent({
            user_id: 'frontend_user',
            recommendation_id,
            event_type: 'click',
            variant,
            category: product?.category || '',
        }).catch(() => { })
    }, [recommendation_id, variant, product])

    const handleAccept = useCallback(async () => {
        await trackEvent({
            user_id: 'frontend_user',
            recommendation_id,
            event_type: 'accept',
            variant,
            category: product?.category || '',
            premium: quote?.final_premium,
        }).catch(() => { })
        onAccept(recommendation)
    }, [recommendation, onAccept])

    const handleDecline = useCallback(async () => {
        await trackEvent({
            user_id: 'frontend_user',
            recommendation_id,
            event_type: 'decline',
            variant,
            category: product?.category || '',
        }).catch(() => { })
        onDecline()
    }, [recommendation_id, variant, product, onDecline])

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 modal-overlay flex items-end sm:items-center justify-center p-4">
                <motion.div
                    initial={{ opacity: 0, y: 60, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 40, scale: 0.95 }}
                    transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                    onClick={handleClick}
                    className="relative w-full max-w-md glass rounded-3xl overflow-hidden shadow-2xl"
                >
                    {/* Gradient header band */}
                    <div
                        className="h-1.5 w-full"
                        style={{ background: `linear-gradient(90deg, ${colors.from}, ${colors.to})` }}
                    />

                    <div className="p-6">
                        {/* Close */}
                        <button
                            onClick={onClose}
                            className="absolute top-5 right-5 p-1.5 rounded-full text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-colors"
                            aria-label="Close"
                        >
                            <X className="w-4 h-4" />
                        </button>

                        {/* Dev variant badge */}
                        <div className="flex items-center gap-2 mb-4">
                            <ABBadge variant={variant} />
                        </div>

                        {/* Variant B extras */}
                        {variant === 'B' && <VariantBBadge />}

                        {/* Icon + headline */}
                        <div className="flex items-start gap-4 mb-4">
                            <div
                                className="flex-shrink-0 w-12 h-12 rounded-2xl flex items-center justify-center pulse-ring"
                                style={{ background: `linear-gradient(135deg, ${colors.from}33, ${colors.to}33)`, border: `1px solid ${colors.from}55` }}
                            >
                                <Shield className="w-6 h-6" style={{ color: colors.from }} />
                            </div>
                            <div className="flex-1 min-w-0 pt-0.5">
                                <h2 className="text-lg font-bold text-white leading-snug">
                                    {copy?.headline || product?.name}
                                </h2>
                                <p className="text-sm text-slate-400 mt-1 leading-relaxed">
                                    {copy?.subheadline || product?.description}
                                </p>
                            </div>
                        </div>

                        {/* Price + coverage card */}
                        <div className="rounded-2xl p-4 mb-4 bg-slate-800/60 border border-border/40">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs text-slate-400 uppercase tracking-wide">Premium</span>
                                <div className="text-right">
                                    <span className="text-2xl font-extrabold text-white">
                                        SGD {quote?.final_premium?.toFixed(2)}
                                    </span>
                                    <span className="text-xs text-slate-500 ml-1">one-time</span>
                                </div>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-slate-400 uppercase tracking-wide">Coverage</span>
                                <span className="text-sm font-semibold text-brand-400">
                                    Up to SGD {quote?.coverage_amount?.toLocaleString('en-SG')}
                                </span>
                            </div>

                            {/* Coverage bar */}
                            <div className="mt-3">
                                <div className="h-1.5 w-full rounded-full bg-slate-700">
                                    <div
                                        className="h-1.5 rounded-full"
                                        style={{
                                            width: `${Math.min((quote?.final_premium / quote?.coverage_amount) * 10000, 100)}%`,
                                            background: `linear-gradient(90deg, ${colors.from}, ${colors.to})`,
                                        }}
                                    />
                                </div>
                                <p className="text-xs text-slate-500 mt-1">
                                    Value ratio: {((quote?.coverage_amount / quote?.final_premium) | 0)}× your premium
                                </p>
                            </div>
                        </div>

                        {/* What's covered bullets */}
                        <div className="space-y-1.5 mb-5">
                            {[product?.description].filter(Boolean).map((d, i) => (
                                <div key={i} className="flex items-start gap-2 text-sm text-slate-300">
                                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                                    {d}
                                </div>
                            ))}
                            {variant === 'B' && (
                                <div className="flex items-start gap-2 text-sm text-slate-300">
                                    <Star className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                                    Rated 4.8★ by 12,000+ customers
                                </div>
                            )}
                        </div>

                        {/* CTAs */}
                        <div className="space-y-2.5">
                            <button
                                onClick={handleAccept}
                                className="w-full flex items-center justify-center gap-2 py-3.5 px-6 rounded-2xl font-semibold text-white text-sm transition-all duration-200 active:scale-95 hover:opacity-90"
                                style={{ background: `linear-gradient(135deg, ${colors.from}, ${colors.to})` }}
                            >
                                {copy?.cta || 'Add Insurance'}
                                <ChevronRight className="w-4 h-4" />
                            </button>

                            <button
                                onClick={handleDecline}
                                className="w-full py-3 px-6 rounded-2xl text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-700/40 transition-colors font-medium"
                            >
                                No thanks, I'll risk it
                            </button>
                        </div>

                        {/* Trust badge */}
                        <div className="mt-4 flex items-center justify-center gap-1.5 text-xs text-slate-500">
                            <Zap className="w-3 h-3" />
                            {copy?.trust_badge || 'Instant digital policy issued'}
                        </div>
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    )
}
