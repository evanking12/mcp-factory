/**
 * Contoso Customer Service — JavaScript Module
 * REST client wrapper for the Contoso CRM back-end.
 */

'use strict';

/**
 * Retrieve customer profile from Contoso CRM.
 * @param {string} customerId - Unique customer identifier.
 * @returns {Promise<Object>} Customer profile including name, email, tier.
 */
async function getCustomerProfile(customerId) {}

/**
 * Place a new sales order.
 * @param {string} customerId - Ordering customer.
 * @param {Array<{sku: string, qty: number}>} items - Line items.
 * @param {string} shippingAddress - Delivery address.
 * @param {string} [couponCode] - Optional promo code.
 * @returns {Promise<string>} New order ID.
 */
async function placeOrder(customerId, items, shippingAddress, couponCode) {}

/**
 * Cancel an existing order before it ships.
 * @param {string} orderId - Order to cancel.
 * @param {string} reason - Cancellation reason.
 * @returns {Promise<boolean>} True if cancelled successfully.
 */
async function cancelOrder(orderId, reason) {}

/**
 * Look up the live status of an order.
 * @param {string} orderId
 * @returns {Promise<string>} Status string: pending|processing|shipped|delivered|cancelled
 */
async function getOrderStatus(orderId) {}

/**
 * Send a promotional offer to a customer via their preferred channel.
 * @param {string} customerId
 * @param {string} offerId - Offer catalogue ID.
 * @param {string} channel - Delivery channel: email|sms|push
 */
function sendPromoOffer(customerId, offerId, channel) {}

/**
 * Retrieve the customer's current loyalty point balance.
 * @param {string} customerId
 * @returns {Promise<number>} Point balance.
 */
async function getLoyaltyBalance(customerId) {}

/**
 * Submit a support ticket on behalf of a customer.
 * @param {string} customerId
 * @param {string} subject
 * @param {string} description
 * @param {string} [priority='normal'] - low|normal|high|urgent
 * @returns {Promise<number>} New ticket ID.
 */
async function submitTicket(customerId, subject, description, priority = 'normal') {}

module.exports = {
    getCustomerProfile,
    placeOrder,
    cancelOrder,
    getOrderStatus,
    sendPromoOffer,
    getLoyaltyBalance,
    submitTicket,
};
