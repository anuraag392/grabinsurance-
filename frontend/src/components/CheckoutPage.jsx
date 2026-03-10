/**
 * CheckoutPage.jsx
 * Main checkout UI demonstrating the GrabInsurance embedded insurance engine.
 *
 * Features:
 * - Deal selector (10 sample deals across 6 categories)
 * - Calls /api/recommend on deal selection
 * - Shows DealSummary sidebar + order total
 * - Insurance offer inline card with "See Details" modal trigger
 * - Accept / Decline flow with confirmation states
 * - Loading shimmer while fetching recommendation
 */

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    ShoppingCart, Shield, Loader2, CheckCircle, XCircle,
    ChevronDown, BarChart2, RefreshCw, Sparkles,
} from 'lucide-react'
import { getRecommendation } from '../api/client'
import InsuranceOfferModal from './InsuranceOfferModal'
import DealSummary from './DealSummary'
import ABBadge from './ABBadge'

const SAMPLE_DEALS = [
    { title: 'iPhone 16 Pro 256GB', category: 'mobiles', price: 1299, tags: ['apple', 'smartphone'], seller: 'Apple Store' },
    { title: 'Singapore Airlines SQ001 – BKK Return', category: 'flights', price: 680, tags: ['flight', 'airline', 'travel'], seller: 'Singapore Airlines' },
    { title: 'Dell XPS 15 Laptop 2024', category: 'laptops', price: 2499, tags: ['laptop', 'dell', 'ultrabook'], seller: 'Dell Official' },
    { title: 'Bali Escape 5D4N Package', category: 'packages', price: 1850, tags: ['vacation', 'resort', 'trip', 'bali'], seller: 'TravelGuru' },
    { title: 'Samsung 65" QLED 4K Smart TV', category: 'electronics', price: 1799, tags: ['tv', 'samsung', '4k'], seller: 'Samsung' },
    { title: 'Honda PCX 160 Electric Scooter', category: 'vehicles', price: 4200, tags: ['scooter', 'honda', 'ev'], seller: 'Honda Motors SG' },
    { title: 'IKEA MALM Queen Bed Frame + Mattress', category: 'furniture', price: 799, tags: ['bed', 'mattress', 'furniture'], seller: 'IKEA' },
    { title: 'Dyson V15 Detect Vacuum Cleaner', category: 'appliances', price: 899, tags: ['vacuum', 'dyson', 'appliance'], seller: 'Dyson' },
    { title: 'Sony WH-1000XM5 Headphones', category: 'gadgets', price: 349, tags: ['headphones', 'sony', 'audio'], seller: 'Sony SG' },
    { title: 'Sentosa Weekend Staycation 3N', category: 'hotels', price: 540, tags: ['hotel', 'staycation', 'travel'], seller: 'Sentosa Hotels' },
]

const STATUS = { IDLE: 'idle', LOADING: 'loading', DONE: 'done', ACCEPTED: 'accepted', DECLINED: 'declined', ERROR: 'error' }

function ShimmerBlock({ className = '' }) {
    return <div className={`shimmer ${className}`} />
}

function LoadingSkeleton() {
    return (
        <div className="glass rounded-2xl p-5 space-y-4 animate-pulse">
            <ShimmerBlock className="h-5 w-3/4 rounded" />
            <ShimmerBlock className="h-4 w-1/2 rounded" />
            <div className="border-t border-border/30 my-2" />
            <ShimmerBlock className="h-16 rounded-xl" />
            <div className="flex gap-3">
                <ShimmerBlock className="h-10 flex-1 rounded-xl" />
                <ShimmerBlock className="h-10 flex-1 rounded-xl" />
            </div>
        </div>
    )
}

export default function CheckoutPage() {
    const [selectedDeal, setSelectedDeal] = useState(SAMPLE_DEALS[0])
    const [recommendation, setRecommendation] = useState(null)
    const [status, setStatus] = useState(STATUS.IDLE)
    const [showModal, setShowModal] = useState(false)
    const [userId] = useState(() => `user_${Math.random().toString(36).slice(2, 10)}`)

    const fetchRecommendation = useCallback(async (deal) => {
        setStatus(STATUS.LOADING)
        setRecommendation(null)
        try {
            const data = await getRecommendation({ ...deal, user_id: userId })
            setRecommendation(data)
            setStatus(STATUS.DONE)
        } catch (err) {
            console.error(err)
            setStatus(STATUS.ERROR)
        }
    }, [userId])

    useEffect(() => {
        fetchRecommendation(selectedDeal)
    }, [selectedDeal])

    const handleAccept = (rec) => {
        setShowModal(false)
        setStatus(STATUS.ACCEPTED)
    }

    const handleDecline = () => {
        setShowModal(false)
        setStatus(STATUS.DECLINED)
    }

    const orderTotal = recommendation
        ? selectedDeal.price + (status === STATUS.ACCEPTED ? recommendation.quote.final_premium : 0)
        : selectedDeal.price

    return (
        <div className="min-h-screen bg-surface">
            {/* Top nav */}
            <header className="border-b border-border/50 px-6 py-4">
                <div className="max-w-5xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 flex items-center justify-center">
                            <Shield className="w-4 h-4 text-white" />
                        </div>
                        <span className="font-bold text-white text-lg tracking-tight">GrabInsurance</span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-brand-700/50 text-brand-400 border border-brand-600/30 font-medium">
                            Checkout Engine
                        </span>
                    </div>
                    <a
                        href="/dashboard/index.html"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-700/50"
                    >
                        <BarChart2 className="w-3.5 h-3.5" />
                        Analytics Dashboard
                    </a>
                </div>
            </header>

            <main className="max-w-5xl mx-auto px-6 py-10">
                <div className="mb-8 text-center">
                    <h1 className="text-3xl font-extrabold text-white mb-2">
                        Simulated <span className="gradient-text">Checkout</span>
                    </h1>
                    <p className="text-slate-400 text-sm">
                        Select a deal below to see the AI-powered insurance recommendation engine in action.
                    </p>
                </div>

                {/* Deal selector */}
                <div className="glass rounded-2xl p-4 mb-8">
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                        Choose a deal to simulate
                    </label>
                    <div className="relative">
                        <select
                            value={SAMPLE_DEALS.indexOf(selectedDeal)}
                            onChange={(e) => {
                                setStatus(STATUS.IDLE)
                                setSelectedDeal(SAMPLE_DEALS[+e.target.value])
                            }}
                            className="w-full appearance-none bg-slate-800 border border-border rounded-xl px-4 py-3 pr-10 text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50 cursor-pointer"
                        >
                            {SAMPLE_DEALS.map((d, i) => (
                                <option key={i} value={i}>
                                    {d.title} — SGD {d.price.toLocaleString()}
                                </option>
                            ))}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                    </div>
                </div>

                {/* Two-column checkout layout */}
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                    {/* Left: deal summary */}
                    <div className="lg:col-span-3 space-y-4">
                        <DealSummary deal={selectedDeal} />

                        {/* Shipping / payment placeholders */}
                        <div className="glass rounded-2xl p-5">
                            <h3 className="text-sm font-semibold text-white mb-3">Delivery</h3>
                            <div className="space-y-1.5">
                                {['Standard Delivery (3–5 days) – Free', 'Express Delivery (Next Day) – SGD 9.90'].map((opt) => (
                                    <label key={opt} className="flex items-center gap-2.5 cursor-pointer group">
                                        <span className="w-4 h-4 rounded-full border-2 border-brand-500 flex-shrink-0 group-first:bg-brand-500" />
                                        <span className="text-sm text-slate-300">{opt}</span>
                                    </label>
                                ))}
                            </div>
                        </div>

                        <div className="glass rounded-2xl p-5">
                            <h3 className="text-sm font-semibold text-white mb-3">Payment</h3>
                            <div className="flex items-center gap-2 text-sm text-slate-400">
                                <span className="px-2 py-0.5 rounded bg-slate-700 text-slate-300 text-xs font-mono">•••• •••• •••• 4242</span>
                                <span>GrabPay / Visa</span>
                            </div>
                        </div>
                    </div>

                    {/* Right: order summary + insurance offer */}
                    <div className="lg:col-span-2 space-y-4">
                        {/* Order total */}
                        <div className="glass rounded-2xl p-5 space-y-3">
                            <h3 className="text-sm font-semibold text-white">Order Summary</h3>
                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between text-slate-400">
                                    <span>Item total</span>
                                    <span>SGD {selectedDeal.price.toFixed(2)}</span>
                                </div>
                                {status === STATUS.ACCEPTED && recommendation && (
                                    <motion.div
                                        initial={{ opacity: 0, y: -4 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="flex justify-between text-emerald-400"
                                    >
                                        <span className="flex items-center gap-1.5">
                                            <Shield className="w-3.5 h-3.5" /> Insurance
                                        </span>
                                        <span>+ SGD {recommendation.quote.final_premium.toFixed(2)}</span>
                                    </motion.div>
                                )}
                                <div className="flex justify-between text-slate-400">
                                    <span>Delivery</span>
                                    <span>Free</span>
                                </div>
                                <div className="border-t border-border/50 pt-2 flex justify-between font-bold text-white text-base">
                                    <span>Total</span>
                                    <span>SGD {orderTotal.toFixed(2)}</span>
                                </div>
                            </div>
                        </div>

                        {/* Insurance offer card */}
                        <div className="glass rounded-2xl p-5">
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-sm font-semibold text-white flex items-center gap-1.5">
                                    <Sparkles className="w-4 h-4 text-brand-400" />
                                    AI Insurance Offer
                                </h3>
                                {recommendation && <ABBadge variant={recommendation.variant} />}
                            </div>

                            {status === STATUS.LOADING && <LoadingSkeleton />}

                            {status === STATUS.ERROR && (
                                <div className="text-center py-6 text-slate-500 text-sm">
                                    <p>Could not load insurance offer.</p>
                                    <button
                                        onClick={() => fetchRecommendation(selectedDeal)}
                                        className="mt-2 flex items-center gap-1 mx-auto text-brand-400 hover:text-brand-300 text-xs"
                                    >
                                        <RefreshCw className="w-3 h-3" /> Retry
                                    </button>
                                </div>
                            )}

                            {status === STATUS.DONE && recommendation && (
                                <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
                                    {/* Intent chip */}
                                    <div className="flex items-center gap-2 mb-3">
                                        <span className="text-xs px-2 py-0.5 rounded-full bg-brand-700/40 text-brand-300 border border-brand-600/30">
                                            Intent: {recommendation.intent.intent}
                                        </span>
                                        <span className="text-xs text-slate-500">
                                            {Math.round(recommendation.intent.confidence * 100)}% confidence
                                        </span>
                                    </div>

                                    {/* Mini offer card */}
                                    <div className="rounded-xl bg-slate-800/60 border border-border/40 p-4 mb-3">
                                        <p className="text-sm font-semibold text-white leading-snug mb-1">
                                            {recommendation.copy?.headline}
                                        </p>
                                        <p className="text-xs text-slate-400 mb-3">{recommendation.copy?.subheadline}</p>
                                        <div className="flex items-center justify-between text-xs text-slate-400">
                                            <span>Premium</span>
                                            <span className="text-white font-bold text-sm">
                                                SGD {recommendation.quote.final_premium.toFixed(2)}
                                            </span>
                                        </div>
                                        <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
                                            <span>Coverage</span>
                                            <span className="text-brand-400">
                                                Up to SGD {recommendation.quote.coverage_amount.toLocaleString('en-SG')}
                                            </span>
                                        </div>
                                    </div>

                                    <button
                                        onClick={() => setShowModal(true)}
                                        className="w-full py-3 rounded-xl bg-gradient-to-r from-brand-500 to-violet-500 text-white text-sm font-semibold hover:opacity-90 transition-opacity active:scale-95"
                                    >
                                        {recommendation.copy?.cta || 'View Offer Details'}
                                    </button>
                                </motion.div>
                            )}

                            {status === STATUS.ACCEPTED && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="text-center py-4 space-y-2"
                                >
                                    <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto" />
                                    <p className="text-sm font-semibold text-emerald-300">Insurance Added!</p>
                                    <p className="text-xs text-slate-500">Your digital policy will be emailed to you.</p>
                                </motion.div>
                            )}

                            {status === STATUS.DECLINED && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="text-center py-4 space-y-2"
                                >
                                    <XCircle className="w-8 h-8 text-slate-500 mx-auto" />
                                    <p className="text-xs text-slate-500">Insurance declined. No coverage added.</p>
                                    <button
                                        onClick={() => setStatus(STATUS.DONE)}
                                        className="text-xs text-brand-400 hover:underline"
                                    >
                                        Changed your mind?
                                    </button>
                                </motion.div>
                            )}
                        </div>

                        {/* Place order button */}
                        <button className="w-full py-4 rounded-2xl bg-gradient-to-r from-brand-600 to-brand-500 text-white font-bold text-base hover:opacity-90 transition-opacity shadow-lg shadow-brand-900/40 active:scale-95 flex items-center justify-center gap-2">
                            <ShoppingCart className="w-5 h-5" />
                            Place Order
                        </button>
                    </div>
                </div>
            </main>

            {/* Insurance offer modal */}
            {showModal && recommendation && (
                <InsuranceOfferModal
                    recommendation={recommendation}
                    onAccept={handleAccept}
                    onDecline={handleDecline}
                    onClose={() => setShowModal(false)}
                />
            )}
        </div>
    )
}
