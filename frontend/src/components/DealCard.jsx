/**
 * DealCard.jsx
 * Displays detailed information about the deal being purchased.
 * Shows merchant, category badge, deal title, value, and tags.
 */

import { motion } from 'framer-motion'
import { Tag, Store, TrendingUp, ArrowRight } from 'lucide-react'

const CATEGORY_CONFIG = {
    travel: { emoji: '✈️', label: 'Travel', color: 'from-sky-500/20 to-blue-600/20', border: 'border-sky-500/30', text: 'text-sky-300' },
    flights: { emoji: '🛫', label: 'Travel', color: 'from-sky-500/20 to-blue-600/20', border: 'border-sky-500/30', text: 'text-sky-300' },
    electronics: { emoji: '📱', label: 'Electronics', color: 'from-violet-500/20 to-purple-600/20', border: 'border-violet-500/30', text: 'text-violet-300' },
    laptops: { emoji: '💻', label: 'Electronics', color: 'from-violet-500/20 to-purple-600/20', border: 'border-violet-500/30', text: 'text-violet-300' },
    food: { emoji: '🍔', label: 'Food', color: 'from-orange-500/20 to-red-500/20', border: 'border-orange-500/30', text: 'text-orange-300' },
    food_delivery: { emoji: '🛵', label: 'Food Delivery', color: 'from-orange-500/20 to-red-500/20', border: 'border-orange-500/30', text: 'text-orange-300' },
    health: { emoji: '💊', label: 'Health', color: 'from-emerald-500/20 to-teal-600/20', border: 'border-emerald-500/30', text: 'text-emerald-300' },
    wellness: { emoji: '🌿', label: 'Health', color: 'from-emerald-500/20 to-teal-600/20', border: 'border-emerald-500/30', text: 'text-emerald-300' },
    fashion: { emoji: '👗', label: 'Fashion', color: 'from-pink-500/20 to-rose-600/20', border: 'border-pink-500/30', text: 'text-pink-300' },
}


const DEFAULT_CAT = { emoji: '🛒', label: 'Deal', color: 'from-slate-500/20 to-slate-600/20', border: 'border-slate-500/30', text: 'text-slate-300' }

function formatValue(value, currency = 'INR') {
    const symbol = currency === 'INR' ? '₹' : currency === 'SGD' ? 'S$' : currency
    return `${symbol}${Number(value).toLocaleString()}`
}

export default function DealCard({ deal, isLoading }) {
    if (!deal) return null

    const cat = CATEGORY_CONFIG[deal.category?.toLowerCase()] || DEFAULT_CAT
    const symbol = deal.currency === 'INR' ? '₹' : 'S$'

    return (
        <motion.div
            key={deal.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="rounded-2xl overflow-hidden border border-slate-700/50"
            style={{ background: 'linear-gradient(135deg, #111827 0%, #0f172a 100%)' }}
        >
            {/* Category colour bar */}
            <div className={`h-1 w-full bg-gradient-to-r ${cat.color.replace('/20', '')}`} />

            <div className="p-6">
                {/* Header row */}
                <div className="flex items-start justify-between gap-4 mb-5">
                    {/* Emoji badge */}
                    <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${cat.color} border ${cat.border} flex items-center justify-center text-2xl flex-shrink-0`}>
                        {cat.emoji}
                    </div>

                    {/* Title block */}
                    <div className="flex-1 min-w-0">
                        <h2 className="text-base font-bold text-white leading-snug line-clamp-2">
                            {deal.deal_title}
                        </h2>
                        <div className="flex items-center gap-2 mt-1.5">
                            <Store className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                            <span className="text-sm text-slate-400">{deal.merchant}</span>
                        </div>
                    </div>

                    {/* Category badge */}
                    <span className={`flex-shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full border ${cat.border} ${cat.text} bg-transparent`}>
                        {cat.label}
                    </span>
                </div>

                {/* Subcategory + Tags */}
                <div className="flex flex-wrap gap-1.5 mb-5">
                    {deal.subcategory && (
                        <span className="flex items-center gap-1 text-xs text-slate-400 px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700">
                            <Tag className="w-2.5 h-2.5" /> {deal.subcategory}
                        </span>
                    )}
                    {deal.tags?.slice(0, 4).map(tag => (
                        <span key={tag} className="text-xs text-slate-500 px-2.5 py-1 rounded-full bg-slate-800/60 border border-slate-700/50">
                            {tag}
                        </span>
                    ))}
                </div>

                {/* Divider */}
                <div className="h-px bg-gradient-to-r from-transparent via-slate-700 to-transparent mb-5" />

                {/* Deal value */}
                <div className="flex items-end justify-between">
                    <div>
                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Deal Value</p>
                        <div className="flex items-baseline gap-1.5">
                            <span className="text-3xl font-extrabold text-white tracking-tight">
                                {symbol}{Number(deal.deal_value).toLocaleString()}
                            </span>
                            <span className="text-sm text-slate-500">{deal.currency}</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-emerald-400">
                        <TrendingUp className="w-3.5 h-3.5" />
                        Best available rate
                    </div>
                </div>
            </div>

            {/* Loading overlay */}
            {isLoading && (
                <div className="absolute inset-0 rounded-2xl bg-slate-900/60 backdrop-blur-sm flex items-center justify-center">
                    <div className="w-6 h-6 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
                </div>
            )}
        </motion.div>
    )
}
