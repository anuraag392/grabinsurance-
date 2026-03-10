/**
 * CheckoutCTA.jsx
 * Final checkout call to action.
 * Shows order total with/without insurance, two primary actions,
 * and post-accept/decline confirmation states.
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    ShoppingCart, Shield, CheckCircle2, XCircle,
    Lock, ChevronRight, AlertCircle
} from 'lucide-react'

const STATUS = { IDLE: 'idle', ACCEPTED: 'accepted', DECLINED: 'declined' }

function TrustBar() {
    return (
        <div className="flex items-center justify-center gap-4 py-3 px-4 rounded-xl bg-slate-800/40 border border-slate-700/30">
            {[
                { icon: Lock, text: '256-bit secure' },
                { icon: Shield, text: 'Instant policy' },
                { icon: CheckCircle2, text: '5-day claims' },
            ].map(({ icon: Icon, text }) => (
                <div key={text} className="flex items-center gap-1.5 text-xs text-slate-500">
                    <Icon className="w-3 h-3 text-slate-600" />
                    {text}
                </div>
            ))}
        </div>
    )
}

export default function CheckoutCTA({
    deal,
    recommendation,
    selectedVariant,
    onAccept,
    onDecline,
}) {
    const [status, setStatus] = useState(STATUS.IDLE)

    if (!deal || !recommendation) return null

    const premium = recommendation.quote?.final_premium ?? recommendation.quote?.premium_price ?? 0
    const dealValue = deal.deal_value ?? 0
    const symbol = deal.currency === 'INR' ? '₹' : 'S$'
    const totalWith = dealValue + premium
    const totalWithout = dealValue

    function handleAccept() {
        setStatus(STATUS.ACCEPTED)
        onAccept?.()
    }

    function handleDecline() {
        setStatus(STATUS.DECLINED)
        onDecline?.()
    }

    return (
        <div className="rounded-2xl border border-slate-700/50 overflow-hidden"
            style={{ background: 'linear-gradient(160deg, #0a1320 0%, #070f1a 100%)' }}>

            {/* Gradient top bar */}
            <div className="h-0.5 w-full bg-gradient-to-r from-brand-600 via-teal-400 to-emerald-400" />

            <div className="p-5 space-y-4">

                {/* Order summary */}
                <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Order Summary</h4>
                    <div className="space-y-2 text-sm">
                        <div className="flex justify-between text-slate-300">
                            <span className="truncate mr-2 text-slate-400">{deal.deal_title}</span>
                            <span className="flex-shrink-0 font-medium">{symbol}{Number(dealValue).toLocaleString()}</span>
                        </div>

                        <AnimatePresence>
                            {status === STATUS.ACCEPTED && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className="flex justify-between text-emerald-400"
                                >
                                    <span className="flex items-center gap-1.5">
                                        <Shield className="w-3.5 h-3.5" />
                                        {recommendation.product?.name}
                                    </span>
                                    <span className="font-medium">+{symbol}{Number(premium).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <div className="h-px bg-slate-700/50" />

                        <div className="flex justify-between font-bold text-white text-base">
                            <span>Total</span>
                            <motion.span
                                key={status === STATUS.ACCEPTED ? 'with' : 'without'}
                                initial={{ opacity: 0, y: -4 }}
                                animate={{ opacity: 1, y: 0 }}
                            >
                                {symbol}{Number(status === STATUS.ACCEPTED ? totalWith : totalWithout).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </motion.span>
                        </div>
                    </div>
                </div>

                {/* Insurance CTA panel */}
                <AnimatePresence mode="wait">
                    {status === STATUS.IDLE && (
                        <motion.div
                            key="idle"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="space-y-2.5"
                        >
                            {/* Insurance offer strip */}
                            <div className="flex items-center justify-between rounded-xl bg-brand-900/20 border border-brand-500/25 px-4 py-3">
                                <div className="flex items-center gap-2.5">
                                    <Shield className="w-4 h-4 text-brand-400 flex-shrink-0" />
                                    <div>
                                        <p className="text-xs text-slate-300 font-medium">Add insurance</p>
                                        <p className="text-xs text-slate-500">
                                            {symbol}{Number(premium).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} · up to {symbol}{Number(recommendation.quote?.coverage_amount || 0).toLocaleString()} covered
                                        </p>
                                    </div>
                                </div>
                                {selectedVariant && (
                                    <span className="text-xs px-2 py-0.5 rounded-full bg-brand-800/50 border border-brand-600/30 text-brand-300 font-semibold">
                                        Variant {selectedVariant}
                                    </span>
                                )}
                            </div>

                            {/* Accept */}
                            <button
                                onClick={handleAccept}
                                className="w-full flex items-center justify-center gap-2 py-3.5 px-6 rounded-2xl font-bold text-white text-sm transition-all active:scale-95 hover:opacity-90 shadow-lg shadow-brand-900/40"
                                style={{ background: 'linear-gradient(135deg, #3b6ef7 0%, #10b981 100%)' }}
                            >
                                <Shield className="w-4 h-4" />
                                Add Insurance & Pay {symbol}{Number(totalWith).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                <ChevronRight className="w-4 h-4" />
                            </button>

                            {/* Decline + proceed */}
                            <button
                                onClick={handleDecline}
                                className="w-full flex items-center justify-center gap-2 py-3.5 px-6 rounded-2xl font-semibold text-slate-300 text-sm border border-slate-700/60 hover:bg-slate-800/40 transition-all active:scale-95"
                            >
                                <ShoppingCart className="w-4 h-4" />
                                Proceed without Insurance · {symbol}{Number(totalWithout).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </button>
                        </motion.div>
                    )}

                    {status === STATUS.ACCEPTED && (
                        <motion.div
                            key="accepted"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="space-y-3"
                        >
                            <div className="text-center py-2 space-y-1">
                                <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
                                <p className="text-sm font-bold text-emerald-300">Insurance Added!</p>
                                <p className="text-xs text-slate-500">Policy confirmation will be sent to your email.</p>
                            </div>
                            <button
                                className="w-full py-3.5 px-6 rounded-2xl font-bold text-white text-sm bg-gradient-to-r from-emerald-600 to-teal-500 hover:opacity-90 transition-all active:scale-95"
                            >
                                Complete Purchase
                            </button>
                            <button
                                onClick={() => setStatus(STATUS.IDLE)}
                                className="w-full text-xs text-slate-500 hover:text-slate-300 transition-colors py-1"
                            >
                                ← Change your choice
                            </button>
                        </motion.div>
                    )}

                    {status === STATUS.DECLINED && (
                        <motion.div
                            key="declined"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="space-y-3"
                        >
                            <div className="flex items-start gap-2.5 p-3 rounded-xl bg-amber-900/20 border border-amber-500/25">
                                <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                                <p className="text-xs text-amber-300 leading-relaxed">
                                    Proceeding without cover. Your {symbol}{Number(dealValue).toLocaleString()} purchase is unprotected.
                                </p>
                            </div>
                            <button className="w-full py-3.5 px-6 rounded-2xl font-bold text-slate-200 text-sm border border-slate-600 hover:bg-slate-800/60 transition-all active:scale-95 flex items-center justify-center gap-2">
                                <ShoppingCart className="w-4 h-4" />
                                Complete Purchase · {symbol}{Number(totalWithout).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </button>
                            <button
                                onClick={() => setStatus(STATUS.IDLE)}
                                className="w-full text-xs text-brand-400 hover:text-brand-300 transition-colors py-1"
                            >
                                ← Add insurance instead
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Trust bar */}
                <TrustBar />
            </div>
        </div>
    )
}
