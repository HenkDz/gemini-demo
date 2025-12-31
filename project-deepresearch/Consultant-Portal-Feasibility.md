# Technical Feasibility Study: The Consultant Portal

**Date:** December 24, 2025  
**Subject:** Feasibility of Multi-Tenant Access for Independent Sales Consultants

---

## 1. The Core Question
**Can a Sales Consultant link their clients' Xero accounts to PaidBasis directly?**

### The Answer: **Yes, but with a specific permission hurdle.**

Our research into the Xero API & OAuth 2.0 architecture confirms that a single user *can* authorize multiple distinct Xero organizations (Tenants) in a single session. However, Xero enforces strict role-based access control on *who* can authorize an API connection.

---

## 2. The Permission Hurdle

| Xero User Role | Can Connect PaidBasis? | Vulnerability |
| :--- | :--- | :--- |
| **Adviser** | ✅ **YES** | None. (Typical for Fractional CFOs/Bookkeepers) |
| **Standard** | ✅ **YES** | None. (Typical for Trusted Ops Managers) |
| **Invoice Only** | ❌ **NO** | **High Risk.** Many external consultants are only given this restricted role to "just send invoices" without seeing the bank feed. |

### Implication
If your target "Consultant" is a **Fractional Sales Director** or **Head of Growth**, they likely have "Standard" access and can use the seamless "Direct Connect" flow.
If your target is a **Junior Sales Rep**, they likely have "Invoice Only" access and *cannot* connect the data themselves.

---

## 3. Proposed Solution: The "Hybrid Access" Model

To capture the entire market, PaidBasis must support two distinct connection workflows.

### Workflow A: "The Super-User Connect" (Direct)
*   **Target:** Agencies, Fractional Heads of Sales, Bookkeepers.
*   **Flow:**
    1.  Consultant logs into PaidBasis.
    2.  Clicks "Connect Xero".
    3.  Xero OAuth screen says: *"Select organizations to allow access:"*
    4.  Consultant ticks: ☑️ Client A, ☑️ Client B, ☑️ Client C.
    5.  **Result:** PaidBasis creates a unified dashboard showing commissions receivable from all 3 clients.

### Workflow B: "The Client Invite" (Indirect)
*   **Target:** Individual Sales Contractors with restricted access.
*   **Flow:**
    1.  **Client** (Business Owner) installs PaidBasis.
    2.  Client goes to "Settings > Sales Team".
    3.  Client enters Consultant's email: `tom@consulting.com`.
    4.  **Result:** Tom logs into his own PaidBasis portal and sees "Client A" appear as a read-only commission feed, without needing API permissions himself.

---

## 4. Operational Comparison

| Feature | Direct Connect (Consultant-Led) | Client Invite (Business-Led) |
| :--- | :--- | :--- |
| **Setup Speed** | **Fastest.** 1 person connects 10 orgs. | **Slow.** Requires 10 clients to act. |
| **Privacy** | **Lower.** App effectively has admin access to client FinData. | **Higher.** Client controls the scope explicitly. |
| **Invoicing** | **Automated.** Consultant clicks "Send Invoice" -> POST to Xero. | **Manual.** Consultant sends PDF to Client. |
| **Verdict** | **Winner for MVP.** Focus on the "Power User" Consultant. | **Long-term necessity.** |

---

## 5. Technical Recommendation

**We should build "Workflow A" (Direct Connect) first.**

**Why?**
1.  **Least Resistance:** It requires zero action from the Client. The Consultant already has the keys; they just need the tool.
2.  **High-Value User:** Consultants with "Standard" access are usually senior decision-makers (Fractional CFOs/CROs) with higher willingness to pay.
3.  **Xero Native:** Leverages Xero's native multi-tenant architecture (`tenantId` switching) without building complex internal invitation logic immediately.

**Implementation Note:**
When the Consultant acts as the "Vendor" (sending the invoice), the system needs to reverse the logic:
*   *Normal Mode:* Create Bill (Payable) in User's Xero.
*   *Consultant Mode:* Create Invoice (Receivable) in User's Xero, targeted at the "Client Contact".

---
**Next Steps:**
Update `paidbasis-saas.md` to include a "Consultant Portal" feature section targeting Fractional Executives.
