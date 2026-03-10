/**
 * App.jsx – GrabInsurance Checkout Demo
 *
 * Layout: two-column fintech checkout
 *   Left  – Deal picker + DealCard
 *   Right – InsuranceRecommendationCard + VariantCopyComponent + CheckoutCTA
 *
 * Data flow:
 *   1. User selects a deal from mock_deals                (client-side)
 *   2. POST /api/recommend   → recommendation + pricing   (backend)
 *   3. POST /api/copy-variants → 3 offer variants         (backend)
 *   4. User picks a variant, accepts or declines
 */

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, ChevronRight, Zap, BarChart2 } from 'lucide-react'
import axios from 'axios'

import DealCard from './components/DealCard'
import InsuranceRecommendationCard from './components/InsuranceRecommendationCard'
import VariantCopyComponent from './components/VariantCopyComponent'
import CheckoutCTA from './components/CheckoutCTA'

import mockDeals from '@data/mock_deals.json'

// ------------------------------------------------------------------
// API helpers
// ------------------------------------------------------------------

const API = axios.create({ baseURL: 'http://localhost:8000' })

async function fetchRecommendation(deal) {
    const { data } = await API.post('/api/recommend', {
        title: deal.deal_title,
        category: deal.category,
        price: deal.deal_value,
        tags: deal.tags || [],
        user_id: `demo_${deal.id}`,
        seller: deal.merchant,
    })
    return data
}

async function fetchCopyVariants(deal, recommendation) {
    const premium = recommendation?.quote?.final_premium
        ?? recommendation?.quote?.premium_price
        ?? 0

    const coverage = recommendation?.quote?.coverage_amount ?? 0

    const { data } = await API.post('/api/copy-variants', {
        deal_name: deal.deal_title,
        merchant: deal.merchant,
        deal_value: deal.deal_value,
        product_name: recommendation?.product?.name || '',
        premium: premium,
        category: deal.category,
        coverage: coverage,
        currency: deal.currency || 'INR',
    })
    return data.variants || []
}

async function trackEvent({ user_id, recommendation_id, event_type, variant, category, premium }) {
    try {
        await API.post('/api/event', {
            user_id,
            recommendation_id,
            event_type,
            variant: variant || 'A',
            category: category || '',
            premium: premium ?? null,
        })
    } catch (e) {
        console.warn('[trackEvent] failed:', e.message)
    }
}


// ------------------------------------------------------------------
// Deal picker component
// ------------------------------------------------------------------

function DealPicker({ deals, currentIndex, onPrev, onNext }) {
    return (
        <div className="flex items-center justify-between mb-4">
            <div>
                <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Select Deal</h2>
                <p className="text-xs text-slate-600 mt-0.5">{currentIndex + 1} of {deals.length}</p>
            </div>
            <div className="flex items-center gap-1">
                <button
                    onClick={onPrev}
                    disabled={currentIndex === 0}
                    className="w-8 h-8 rounded-xl border border-slate-700 flex items-center justify-center text-slate-400 hover:text-white hover:border-slate-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                    <ChevronLeft className="w-4 h-4" />
                </button>
                <div className="flex gap-1 px-2">
                    {deals.map((_, i) => (
                        <div
                            key={i}
                            className={`rounded-full transition-all ${i === currentIndex
                                ? 'w-4 h-1.5 bg-brand-400'
                                : 'w-1.5 h-1.5 bg-slate-700'
                                }`}
                        />
                    ))}
                </div>
                <button
                    onClick={onNext}
                    disabled={currentIndex === deals.length - 1}
                    className="w-8 h-8 rounded-xl border border-slate-700 flex items-center justify-center text-slate-400 hover:text-white hover:border-slate-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                    <ChevronRight className="w-4 h-4" />
                </button>
            </div>
        </div>
    )
}

// ------------------------------------------------------------------
// Main App
// ------------------------------------------------------------------

export default function App() {
    const [dealIndex, setDealIndex] = useState(0)
    const [recommendation, setRecommendation] = useState(null)
    const [sessionId, setSessionId] = useState(null)        // A/B session correlation ID
    const [variants, setVariants] = useState([])
    const [selectedVariant, setSelectedVariant] = useState(null)
    const [loadingRec, setLoadingRec] = useState(false)
    const [loadingCopy, setLoadingCopy] = useState(false)
    const [error, setError] = useState(null)

    const deal = mockDeals[dealIndex]

    // Fetch recommendation whenever deal changes
    const loadData = useCallback(async () => {
        setLoadingRec(true)
        setLoadingCopy(true)
        setError(null)
        setRecommendation(null)
        setVariants([])
        setSelectedVariant(null)

        try {
            const rec = await fetchRecommendation(deal)
            setRecommendation(rec)
            setSessionId(rec.session_id || null)
            setLoadingRec(false)

            // Fire impression event with session_id
            trackEvent({
                user_id: `demo_${deal.id}`,
                recommendation_id: rec.recommendation_id,
                session_id: rec.session_id,
                event_type: 'impression',
                variant: rec.variant,
                category: rec.product?.category || deal.category,
            })

            const vars = await fetchCopyVariants(deal, rec)
            setVariants(vars)
            if (vars.length) setSelectedVariant(vars[0].variant)
        } catch (e) {
            console.error(e)
            setError('Backend unavailable — start the server on port 8000')
            setLoadingRec(false)
        } finally {
            setLoadingCopy(false)
        }
    }, [dealIndex])  // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { loadData() }, [loadData])

    return (
        <div className="min-h-screen bg-[#060d17] text-white" style={{ fontFamily: "'Inter', sans-serif" }}>
            {/* Ambient glow blobs */}
            <div className="pointer-events-none fixed inset-0 overflow-hidden">
                <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-brand-600/5 blur-3xl" />
                <div className="absolute bottom-0 right-0 w-[500px] h-[500px] rounded-full bg-teal-600/5 blur-3xl" />
            </div>

            {/* Top nav */}
            <header className="relative z-10 border-b border-slate-800/60 bg-slate-950/80 backdrop-blur-md">
                <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-teal-400 flex items-center justify-center">
                            <Zap className="w-4 h-4 text-white" />
                        </div>
                        <div>
                            <span className="font-extrabold text-white tracking-tight">Grab</span>
                            <span className="font-extrabold text-brand-400 tracking-tight">Insurance</span>
                        </div>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-brand-900/40 border border-brand-700/40 text-brand-400 ml-2">Demo</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <a
                            href="http://localhost:8000/dashboard/index.html"
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center gap-1.5 text-xs text-brand-400 font-semibold hover:text-brand-300 transition-colors bg-brand-900/40 px-3 py-1.5 rounded-lg border border-brand-700/40"
                        >
                            <BarChart2 className="w-3.5 h-3.5" />
                            Live Dashboard
                        </a>
                        <a
                            href="http://localhost:8000/docs"
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                        >
                            <BarChart2 className="w-3.5 h-3.5" />
                            API Docs
                        </a>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="relative z-10 max-w-6xl mx-auto px-6 py-10">
                {/* Page title */}
                <div className="mb-8">
                    <h1 className="text-2xl font-extrabold text-white tracking-tight">
                        Checkout{' '}
                        <span className="bg-gradient-to-r from-brand-400 to-teal-400 bg-clip-text text-transparent">
                            + Insurance
                        </span>
                    </h1>
                    <p className="text-sm text-slate-500 mt-1">
                        AI-powered micro-insurance recommendations — contextual to your purchase.
                    </p>
                </div>

                {/* Error banner */}
                <AnimatePresence>
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className="mb-6 flex items-center gap-3 px-4 py-3 rounded-xl bg-red-900/20 border border-red-500/30 text-red-300 text-sm"
                        >
                            <span className="font-semibold">⚠</span> {error}
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Two-column checkout layout */}
                <div className="grid lg:grid-cols-[1fr_420px] gap-6 items-start">

                    {/* ── Left column: Deal picker + DealCard ── */}
                    <div className="space-y-1">
                        <DealPicker
                            deals={mockDeals}
                            currentIndex={dealIndex}
                            onPrev={() => setDealIndex(i => Math.max(0, i - 1))}
                            onNext={() => setDealIndex(i => Math.min(mockDeals.length - 1, i + 1))}
                        />
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={deal.id}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 10 }}
                                transition={{ duration: 0.25 }}
                            >
                                <DealCard deal={deal} isLoading={loadingRec} />
                            </motion.div>
                        </AnimatePresence>

                        {/* Intent chip */}
                        <AnimatePresence>
                            {recommendation?.intent && !loadingRec && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="flex items-center gap-2 mt-3"
                                >
                                    <span className="text-xs text-slate-600">Detected intent:</span>
                                    <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300 font-medium capitalize">
                                        {recommendation.intent.intent}
                                    </span>
                                    <span className="text-xs text-slate-600">
                                        {Math.round((recommendation.intent.confidence || 0) * 100)}% confidence
                                    </span>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    {/* ── Right column: Insurance cards ── */}
                    <div className="space-y-4">
                        <InsuranceRecommendationCard
                            recommendation={recommendation}
                            deal={deal}
                            onTierChange={(tier) => {
                                // Could re-fetch price with new tier here
                                console.log('Tier changed:', tier)
                            }}
                        />

                        <AnimatePresence>
                            {(variants.length > 0 || loadingCopy) && (
                                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                                    <VariantCopyComponent
                                        variants={variants}
                                        isLoading={loadingCopy}
                                        selectedVariant={selectedVariant}
                                        onSelect={setSelectedVariant}
                                        onRefresh={() => {
                                            if (recommendation) {
                                                setLoadingCopy(true)
                                                fetchCopyVariants(deal, recommendation)
                                                    .then(v => {
                                                        setVariants(v)
                                                        if (v.length) setSelectedVariant(v[0].variant)
                                                    })
                                                    .finally(() => setLoadingCopy(false))
                                            }
                                        }}
                                    />
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <AnimatePresence>
                            {recommendation && !loadingRec && (
                                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                                    <CheckoutCTA
                                        deal={deal}
                                        recommendation={recommendation}
                                        selectedVariant={selectedVariant}
                                        onAccept={() => {
                                            trackEvent({
                                                user_id: `demo_${deal.id}`,
                                                recommendation_id: recommendation.recommendation_id,
                                                session_id: sessionId,
                                                event_type: 'accept',
                                                variant: recommendation.variant,
                                                category: recommendation.product?.category || deal.category,
                                                premium: recommendation.quote?.final_premium,
                                            })
                                        }}
                                        onDecline={() => {
                                            trackEvent({
                                                user_id: `demo_${deal.id}`,
                                                recommendation_id: recommendation.recommendation_id,
                                                session_id: sessionId,
                                                event_type: 'decline',
                                                variant: recommendation.variant,
                                                category: recommendation.product?.category || deal.category,
                                            })
                                        }}
                                    />
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </main>
        </div>
    )
}
