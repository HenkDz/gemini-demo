# PaidBasis - Automated Commission Management

**Stop wrestling with spreadsheets. Start getting paid accurately.**

PaidBasis is the commission management platform that finally solves the nightmare of manual commission tracking. Built for growing sales teams that need accurate, automated commission calculations without the complexity and cost of enterprise solutions.

## 🎯 The Problem We Solve

Imagine running a medical device company with a growing sales team. Your commission structure is getting complex:

- **Different rates per product** - some items pay 5%, others 8%
- **Paid only on collected revenue** - not invoices, but actual payments received
- **One month in arrears** - commissions paid the month after collection
- **Manual spreadsheet hell** - rebuilding reports every month in Excel

Sound familiar? You're not alone. Thousands of businesses struggle with this every month, losing money to calculation errors and spending hours on manual processes that should be automated.

**PaidBasis eliminates this chaos.**

## ✨ What Makes PaidBasis Different

### 🔗 **Direct Xero Integration**
- Syncs payments and invoices automatically
- No manual data entry or CSV imports
- Real-time updates when payments are received

### 💰 **Calculates on Actual Payments**
- Ignores outstanding invoices
- Only pays commission on money you've actually collected
- Handles partial payments and overpayments correctly

### 📊 **Product-Specific Commission Rates**
- Different rates for different products/services
- Line-item level precision
- Automatic rate application based on Xero item codes

### ⏰ **Built-in Arrears Processing**
- Configurable delay periods (default: 1 month)
- Commissions earned in December → paid in January
- Automatic enforcement prevents premature payouts

### 👥 **Sales Team Management**
- Unlimited sales reps (no per-user licensing)
- Individual commission structures per rep
- Automatic rep assignment via Xero tracking categories

### 📈 **Clear Reporting & Export**
- Monthly statements for each rep
- CSV exports for payroll systems
- Comprehensive dashboards and analytics

## 🚀 Key Features

### ✅ **Payment-Based Calculations**
Commissions calculated only on actual payments received, not invoice values.

### ✅ **Line-Item Precision**
Split commission by product with different rates per item.

### ✅ **Partial Payment Handling**
Pro-rata calculations for partial payments and payment plans.

### ✅ **Arrears Automation**
Configurable "paid in arrears" rules automatically enforced.

### ✅ **Multi-Rep Support**
Different commission structures for different team members.

### ✅ **No Per-User Licensing**
Add unlimited sales reps without additional costs.

### ✅ **Xero Native Integration**
Direct connection - no manual data entry required.

### ✅ **Payroll-Ready Exports**
CSV files formatted for your payroll system.

## 🔧 How It Works

1. **Connect Your Xero Account** - One-click OAuth integration
2. **Map Your Sales Reps** - Link Xero tracking categories to team members
3. **Set Commission Rules** - Define rates by product, rep, or invoice level
4. **Configure Arrears** - Set your payout delay period
5. **Watch It Run** - Payments sync automatically, commissions calculate instantly
6. **Pay on Schedule** - Export payroll-ready batches when arrears period ends

## 🛠 Technology Stack

- **Frontend**: React + TanStack Router + TailwindCSS + shadcn/ui
- **Backend**: Hono + oRPC (end-to-end type safety)
- **Database**: PostgreSQL + Drizzle ORM
- **Runtime**: Bun
- **Authentication**: Better Auth
- **Xero Integration**: Official Xero API

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ or Bun
- PostgreSQL database
- Xero account with API access

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/paidbasis.git
   cd paidbasis
   ```

2. **Install dependencies**
   ```bash
   bun install
   ```

3. **Set up your database**
   ```bash
   # Update database connection in apps/server/.env
   bun run db:push
   ```

4. **Configure Xero**
   ```bash
   # Add your Xero OAuth credentials to apps/server/.env
   XERO_CLIENT_ID=your_client_id
   XERO_CLIENT_SECRET=your_client_secret
   ```

5. **Start the development server**
   ```bash
   bun run dev
   ```

6. **Open your browser**
   - Web app: [http://localhost:3001](http://localhost:3001)
   - API docs: [http://localhost:3000](http://localhost:3000)

## 📁 Project Structure

```
paidbasis/
├── apps/
│   ├── web/           # React frontend application
│   └── server/        # Hono API server
├── packages/
│   ├── api/          # Business logic & API routes
│   ├── auth/         # Authentication configuration
│   ├── db/           # Database schema & queries
│   ├── xero/         # Xero API integration
│   └── config/       # Shared configuration
└── docs/             # Documentation & analysis
```

## 🎯 Use Cases

**Perfect for:**
- Medical device companies
- Manufacturing with complex product lines
- Professional services firms
- Any business with product-specific commission rates
- Growing sales teams (5-50+ reps)
- Companies paying commissions in arrears

**Not for:**
- Businesses paying commission on invoiced amounts
- Companies with extremely simple flat-rate structures
- Businesses not using Xero

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check out our [docs](docs/) folder
- **Issues**: [GitHub Issues](https://github.com/yourusername/paidbasis/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/paidbasis/discussions)

## 🙏 Acknowledgments

Built to solve the exact problems described in [this Reddit thread](https://www.reddit.com/r/smallbusiness/comments/example/) about commission management nightmares.

---

**Ready to stop the spreadsheet madness?** [Get started with PaidBasis today.](https://paidbasis.com)