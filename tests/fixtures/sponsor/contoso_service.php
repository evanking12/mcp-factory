<?php
/**
 * Contoso Customer Service — PHP Module
 * Provides functions for customer, order, and support operations.
 */

function echo_sentinel(string $sentinel): string {
    return $sentinel;
}

/**
 * Look up a customer account by ID.
 *
 * @param string $customerId The unique customer identifier.
 * @return array|null Customer data array, or null if not found.
 */
function lookupCustomer(string $customerId): ?array {}

/**
 * Update a customer's billing information.
 *
 * @param string $customerId
 * @param array  $billingInfo Associative array with keys: card_number, expiry, cvv.
 * @return bool True on success.
 */
function updateBilling(string $customerId, array $billingInfo): bool {}

/**
 * Check product availability in warehouse.
 *
 * @param string $productSku  SKU of the product.
 * @param int    $quantity     Requested quantity.
 * @return bool True if stock is available.
 */
function checkInventory(string $productSku, int $quantity): bool {}

/**
 * Place an order for a customer.
 *
 * @param string $customerId
 * @param array  $items        Array of ['sku' => ..., 'qty' => ...].
 * @param string $shipAddress  Destination address.
 * @return string New order ID.
 */
function createOrder(string $customerId, array $items, string $shipAddress): string {}

/**
 * Retrieve order details.
 *
 * @param string $orderId
 * @return array Order details including status and line items.
 */
function getOrder(string $orderId): array {}

/**
 * Process a full or partial refund.
 *
 * @param string $orderId
 * @param string $reason
 * @param float|null $amount Null for full refund.
 * @return bool True if gateway accepted the refund.
 */
function processRefund(string $orderId, string $reason, ?float $amount = null): bool {}

/**
 * Open a customer support ticket.
 *
 * @param string $customerId
 * @param string $subject
 * @param string $description
 * @param string $priority One of: low, normal, high, urgent.
 * @return int New ticket ID.
 */
function openSupportTicket(string $customerId, string $subject, string $description, string $priority = 'normal'): int {}
