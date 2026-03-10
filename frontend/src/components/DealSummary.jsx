/**
 * DealSummary.jsx
 * Displays the deal the user is about to purchase in the checkout sidebar.
 */

import { Tag, Store, BadgeCheck } from 'lucide-react'

const CATEGORY_EMOJI = {
    mobiles: '📱', laptops: '💻', flights: '✈️', hotels: '🏨',
    packages: '🌴', electronics: '🔌', vehicles: '🚗', bike: '🏍️',
    furniture: '🛋️', appliances: '🧺', gadgets: '🎧',
    health: '💊', fitness: '🏋️', default: '🛒',
}

export default function DealSummary({ deal }) {
    if (!deal) return null

    const emoji = CATEGORY_EMOJI[deal.category?.toLowerCase()] || CATEGORY_EMOJI.default

    return (
        <div className="glass rounded-2xl p-5 space-y-4">
            {/* Header */}
            <div className="flex items-start gap-3">
                <span className="text-4xl leading-none">{emoji}</span>
                <div className="flex-1 min-w-0">
                    <h3 className="text-base font-semibold text-white leading-snug">{deal.title}</h3>
                    <p className="text-sm text-slate-400 mt-0.5 flex items-center gap-1">
                        <Tag className="w-3 h-3" />
                        {deal.category}
                    </p>
                </div>
                <BadgeCheck className="w-5 h-5 text-brand-400 flex-shrink-0" />
            </div>

            {/* Tags */}
            {deal.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                    {deal.tags.map((tag) => (
                        <span
                            key={tag}
                            className="px-2 py-0.5 text-xs rounded-full bg-slate-700/60 text-slate-300 border border-slate-600/50"
                        >
                            {tag}
                        </span>
                    ))}
                </div>
            )}

            {/* Divider */}
            <div className="border-t border-border/50" />

            {/* Price row */}
            <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Item total</span>
                <span className="text-xl font-bold text-white">
                    SGD {deal.price?.toLocaleString('en-SG', { minimumFractionDigits: 2 })}
                </span>
            </div>

            {deal.seller && (
                <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <Store className="w-3.5 h-3.5" />
                    Sold by {deal.seller}
                </div>
            )}
        </div>
    )
}
