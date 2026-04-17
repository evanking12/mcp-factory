function repoDescribeOrder(orderId) {
  return `order:${orderId}:ready`;
}

module.exports = { repoDescribeOrder };
