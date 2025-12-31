# Browser Automation with Gemini

Automate browser tasks using Browser-Use and Google's Gemini models with AI-powered automation.

## Features

- **Web UI**: User-friendly Gradio interface to enter prompts and view results
- **Application Form Filling**: Automated form submission with document upload
- **SaaS Research**: Discover niche SaaS ideas through market research
- **Results Overlay**: Results displayed directly in the browser sidebar

## Setup

### 1. Get Your API Key

You'll need a Google API key to use the Gemini model:
1. Go to [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Create a new API key
3. Copy the key

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key:
```bash
GOOGLE_API_KEY=your-google-api-key-here
```

### 3. Install Dependencies

```bash
uv sync
```

## Usage

### 🌐 Web UI (Recommended)

Launch the Gradio web interface for the best experience:

```bash
uv run ui.py
```

This opens a web UI where you can:
- Enter custom prompts for browser automation
- Select different Gemini models
- Watch the browser perform tasks in real-time
- View formatted results in a nice panel
- Copy results easily

### 📊 SaaS Ideas Research (CLI)

Discover niche SaaS opportunities with results displayed in a browser sidebar:

```bash
uv run main.py --mode saas
```

The browser will:
1. Research market trends and pain points
2. Analyze gaps in existing solutions
3. Generate unique SaaS concepts
4. Display results in a **sidebar overlay** (stays open for you to review!)

### 📝 Application Form Filling (CLI)

Automate form submission with the included example data:

```bash
uv run main.py --mode apply --document example_document.pdf
```

Or with your own data:

```bash
uv run main.py --mode apply --data my_info.json --document my_document.pdf
```

## Data Format

For application mode, create a JSON file with your information:

```json
{
	"first_name": "Your",
	"last_name": "Name",
	"email": "your.email@example.com",
	"phone": "5551234567",
	"age": "21",
	"US_citizen": true,
	"sponsorship_needed": false,
	"postal_code": "12345",
	"country": "United States",
	"city": "YourCity",
	"address": "123 Your Street",
	"gender": "Your Gender",
	"race": "Your Race/Ethnicity",
	"Veteran_status": "I am not a veteran",
	"disability_status": "No, I do not have a disability"
}
```

## Available Models

| Model | Description |
|-------|-------------|
| `gemini-3-flash-preview` | Fast, good for most tasks (default) |
| `gemini-2.5-flash-preview-05-20` | Balanced speed and quality |
| `gemini-2.5-pro-preview-05-06` | Best quality, slower |

## Tips

- **Web UI**: Best for interactive research and custom prompts
- **CLI with overlay**: Results stay visible in browser; press Enter to close
- **Headless mode**: Not supported - browser must be visible for interaction

## Support

For issues specific to Browser-Use, see:
- Documentation: [https://docs.browser-use.com](https://docs.browser-use.com)
- GitHub: [https://github.com/browser-use/browser-use](https://github.com/browser-use/browser-use)