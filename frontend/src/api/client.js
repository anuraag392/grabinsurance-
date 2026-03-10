/**
 * api/client.js
 * Axios instance and typed API call helpers for the GrabInsurance backend.
 */

import axios from 'axios'

const api = axios.create({
    baseURL: '/api',
    headers: { 'Content-Type': 'application/json' },
    timeout: 15000,
})

/**
 * POST /api/recommend
 * Runs the full pipeline for a deal object and returns recommendation.
 *
 * @param {Object} deal – { title, category, price, tags[], user_id }
 */
export async function getRecommendation(deal) {
    const { data } = await api.post('/recommend', deal)
    return data
}

/**
 * POST /api/event
 * Track a user interaction event (impression / click / accept / decline).
 *
 * @param {Object} payload – { user_id, recommendation_id, event_type, variant, category, premium? }
 */
export async function trackEvent(payload) {
    const { data } = await api.post('/event', payload)
    return data
}

/** GET /api/analytics/summary */
export async function getAnalyticsSummary() {
    const { data } = await api.get('/analytics/summary')
    return data
}

/** GET /api/analytics/ab */
export async function getABMetrics() {
    const { data } = await api.get('/analytics/ab')
    return data
}

/** GET /api/analytics/revenue */
export async function getRevenue() {
    const { data } = await api.get('/analytics/revenue')
    return data
}

/** GET /api/analytics/products */
export async function getTopProducts() {
    const { data } = await api.get('/analytics/products')
    return data
}

export default api
