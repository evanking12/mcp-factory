<#
.SYNOPSIS
    Contoso Customer Service PowerShell module.
.DESCRIPTION
    Provides cmdlets for interacting with the Contoso customer database,
    order management system, and support ticket platform.
#>

function Invoke-ContosoEchoSentinel {
    <#
    .SYNOPSIS
        Echo a deterministic sentinel for MCP E2E validation.
    #>
    param (
        [Parameter(Mandatory)]
        [string]$Sentinel
    )
    return $Sentinel
}

function Get-ContosoCustomer {
    <#
    .SYNOPSIS
        Retrieve a customer record by ID.
    .PARAMETER CustomerId
        The unique customer identifier (e.g. CUST-1234).
    #>
    param (
        [Parameter(Mandatory)]
        [string]$CustomerId
    )
}

function New-ContosoOrder {
    <#
    .SYNOPSIS
        Place a new sales order for a customer.
    .PARAMETER CustomerId
        The ordering customer.
    .PARAMETER Items
        Array of hashtables with keys Sku and Quantity.
    .PARAMETER ShippingAddress
        Delivery address string.
    .PARAMETER CouponCode
        Optional promotional code.
    #>
    param (
        [Parameter(Mandatory)][string]$CustomerId,
        [Parameter(Mandatory)][hashtable[]]$Items,
        [Parameter(Mandatory)][string]$ShippingAddress,
        [string]$CouponCode
    )
}

function Get-ContosoOrderStatus {
    <#
    .SYNOPSIS
        Get the current status of an order.
    .PARAMETER OrderId
        The order identifier.
    #>
    param (
        [Parameter(Mandatory)][string]$OrderId
    )
}

function New-ContosoSupportTicket {
    <#
    .SYNOPSIS
        Open a new support ticket on behalf of a customer.
    .PARAMETER CustomerId
        Affected customer.
    .PARAMETER Subject
        Brief description of the issue.
    .PARAMETER Description
        Full description of the problem.
    .PARAMETER Priority
        Priority level: Low, Normal, High, or Urgent.
    #>
    param (
        [Parameter(Mandatory)][string]$CustomerId,
        [Parameter(Mandatory)][string]$Subject,
        [Parameter(Mandatory)][string]$Description,
        [ValidateSet('Low','Normal','High','Urgent')]
        [string]$Priority = 'Normal'
    )
}

function Invoke-ContosoRefund {
    <#
    .SYNOPSIS
        Process a refund for an order.
    .PARAMETER OrderId
        The order to refund.
    .PARAMETER Reason
        Reason for the refund.
    .PARAMETER Amount
        Partial refund amount. Omit for a full refund.
    #>
    param (
        [Parameter(Mandatory)][string]$OrderId,
        [Parameter(Mandatory)][string]$Reason,
        [double]$Amount
    )
}

function Get-ContosoLoyaltyBalance {
    <#
    .SYNOPSIS
        Return the loyalty point balance for a customer.
    #>
    param (
        [Parameter(Mandatory)][string]$CustomerId
    )
}
