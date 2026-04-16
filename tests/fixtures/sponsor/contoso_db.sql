-- =============================================================
-- Contoso Customer Service Database
-- SQL Server T-SQL stored procedures and functions
-- =============================================================

-- Retrieve a customer record by ID
CREATE PROCEDURE GetCustomerInfo
    @customer_id    INT,
    @include_orders BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    SELECT id, name, email, phone, tier, loyalty_points, created_at
    FROM   Customers
    WHERE  id = @customer_id;

    IF @include_orders = 1
        SELECT id, status, total, created_at
        FROM   Orders
        WHERE  customer_id = @customer_id
        ORDER  BY created_at DESC;
END;
GO

-- Create a new support ticket
CREATE PROCEDURE CreateSupportTicket
    @customer_id INT,
    @subject     NVARCHAR(200),
    @description NVARCHAR(MAX),
    @priority    VARCHAR(20) = 'Normal'
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO Tickets (customer_id, subject, description, priority, status, created_at)
    VALUES (@customer_id, @subject, @description, @priority, 'Open', GETDATE());
    SELECT SCOPE_IDENTITY() AS ticket_id;
END;
GO

-- Escalate a ticket to a higher priority
CREATE PROCEDURE EscalateTicket
    @ticket_id    INT,
    @new_priority VARCHAR(20),
    @agent_id     INT
AS
BEGIN
    UPDATE Tickets
    SET    priority = @new_priority,
           escalated_by = @agent_id,
           escalated_at = GETDATE()
    WHERE  id = @ticket_id;
END;
GO

-- Place a new order
CREATE PROCEDURE CreateOrder
    @customer_id     INT,
    @shipping_address NVARCHAR(500),
    @coupon_code     NVARCHAR(50) = NULL
AS
BEGIN
    DECLARE @order_id INT;
    INSERT INTO Orders (customer_id, shipping_address, coupon_code, status, created_at)
    VALUES (@customer_id, @shipping_address, @coupon_code, 'Pending', GETDATE());
    SET @order_id = SCOPE_IDENTITY();
    SELECT @order_id AS order_id;
END;
GO

-- Calculate customer discount based on order total and loyalty
CREATE FUNCTION CalculateDiscount
(
    @order_total   DECIMAL(10,2),
    @loyalty_years INT
)
RETURNS DECIMAL(5,2)
AS
BEGIN
    RETURN CASE
        WHEN @loyalty_years > 5 THEN @order_total * 0.15
        WHEN @loyalty_years > 2 THEN @order_total * 0.10
        ELSE                         @order_total * 0.05
    END;
END;
GO

-- Lookup order details and line items
CREATE PROCEDURE GetOrderDetails
    @order_id INT
AS
BEGIN
    SELECT o.id, o.status, o.total, o.created_at,
           c.name AS customer_name, c.email
    FROM   Orders o
    JOIN   Customers c ON c.id = o.customer_id
    WHERE  o.id = @order_id;

    SELECT li.product_sku, li.quantity, li.unit_price
    FROM   OrderLineItems li
    WHERE  li.order_id = @order_id;
END;
GO

-- Summary view for customer service agents
CREATE VIEW CustomerOrderSummary AS
SELECT c.id,
       c.name,
       c.email,
       c.tier,
       COUNT(o.id)    AS total_orders,
       SUM(o.total)   AS lifetime_value,
       MAX(o.created_at) AS last_order_date
FROM   Customers c
LEFT   JOIN Orders o ON c.id = o.customer_id
GROUP  BY c.id, c.name, c.email, c.tier;
GO
