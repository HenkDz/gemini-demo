"""
Gradio Web UI for Browser Automation with Gemini.

This provides a user-friendly interface where you can:
- Start a browser and login to services (Gummy Search, etc.)
- Enter custom prompts for browser automation
- Watch the automation happen in real-time
- View results in a nicely formatted panel
- Copy/save results easily

VALIDATION FRAMEWORK:
For finding "super validated" SaaS ideas, the agent uses multiple validation signals:
1. Multiple mentions across different sources (Reddit, GummySearch, forums)
2. Clear pain point expression with emotional language
3. Willingness to pay indicators (budget mentions, "paid for", "subscribe")
4. Recency of discussions (last 6 months preferred)
5. Competition gap analysis (many complaints, few solutions)
6. Market size indicators (subscriber counts, upvote ratios)
"""

import asyncio
import random
from datetime import datetime
from pathlib import Path

import gradio as gr
from browser_use import Agent, Browser, ChatGoogle, Tools
from dotenv import load_dotenv

load_dotenv()

# Global state for browser session
browser_instance: Browser | None = None

# Persistent browser profile directory - saves cookies, localStorage, login sessions
BROWSER_PROFILE_DIR = Path(__file__).parent / ".browser_profile"
BROWSER_PROFILE_DIR.mkdir(exist_ok=True)

RESULTS_DIR = Path("results")


def extract_and_save_attachments(content: str, base_path: Path) -> list[str]:
    """Extract attachments from report content and save them as separate files.
    
    Looks for patterns like:
    Attachments:
    filename.md:
    # content...
    
    Returns list of saved attachment file paths.
    """
    import re

    attachments: list[str] = []

    # Robust parser:
    # - Find an "Attachments:" header
    # - Each attachment starts with a line like "filename.md:"
    # - Attachment content may contain blank lines, markdown tables, etc.
    lines = content.splitlines()

    start_idx: int | None = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*Attachments?\s*:\s*$", line, flags=re.IGNORECASE):
            start_idx = i + 1
            break

    if start_idx is None:
        return attachments

    filename_re = re.compile(r"^\s*([^\\/]+?\.md)\s*:\s*$", flags=re.IGNORECASE)

    current_name: str | None = None
    current_buf: list[str] = []

    def flush_current() -> None:
        nonlocal current_name, current_buf, attachments
        if not current_name:
            return

        file_content = "\n".join(current_buf).strip()
        if len(file_content) < 50:
            current_name = None
            current_buf = []
            return

        # Sanitize: keep basename only, strip odd characters
        safe_name = Path(current_name).name
        safe_name = re.sub(r"[^A-Za-z0-9._ -]", "_", safe_name)
        if not safe_name.lower().endswith(".md"):
            safe_name += ".md"

        attachment_path = base_path / safe_name
        if attachment_path.exists():
            stem = attachment_path.stem
            suffix = attachment_path.suffix
            n = 2
            while (base_path / f"{stem}_{n}{suffix}").exists():
                n += 1
            attachment_path = base_path / f"{stem}_{n}{suffix}"

        attachment_path.write_text(file_content, encoding="utf-8")
        attachments.append(str(attachment_path.resolve()))

        current_name = None
        current_buf = []

    for line in lines[start_idx:]:
        m = filename_re.match(line)
        if m:
            flush_current()
            current_name = m.group(1).strip()
            current_buf = []
            continue

        if current_name is not None:
            current_buf.append(line)

    flush_current()
    return attachments


def save_results_markdown(
    content: str, action_log: str, prompt: str, model_name: str
) -> tuple[str, list[str]]:
    """Save the combined results and action log to a markdown file.
    
    Also extracts and saves any attachments mentioned in the content.

    Returns the absolute path to the saved file.
    """
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt_slug = "".join(
        c if c.isalnum() or c in ("-", "_") else "_" for c in prompt.lower().strip()
    )[:50].strip("_")
    filename = f"result_{timestamp_slug}"
    if prompt_slug:
        filename += f"_{prompt_slug}"
    file_path = RESULTS_DIR / f"{filename}.md"
    
    # Save main report
    file_path.write_text(f"{content}\n\n{action_log}", encoding="utf-8")
    
    # Extract and save attachments
    saved_attachments = extract_and_save_attachments(content, RESULTS_DIR)
    if saved_attachments:
        print(f"📎 Saved {len(saved_attachments)} attachment(s)")

    return str(file_path.resolve()), saved_attachments


async def start_browser_instance():
    """Start a new browser instance with persistent profile (keeps logins!)."""
    global browser_instance

    if browser_instance is not None:
        return "ℹ️ Browser already running. Use 'Close Browser' to stop it first."

    try:
        # Create browser with persistent profile - this saves ALL login sessions!
        browser_instance = Browser(
            headless=False,
            keep_alive=True,
            user_data_dir=str(BROWSER_PROFILE_DIR),  # Persists cookies, localStorage, sessions
        )
        
        # Launch the browser
        await browser_instance.start()
        
        # Navigate to a start page
        page = await browser_instance.get_current_page()
        await page.goto("https://www.linkedin.com/sales", wait_until="domcontentloaded")
        
        return "✅ Browser started with PERSISTENT profile! Your logins (LinkedIn, Reddit, GummySearch) will be saved between sessions."
    except Exception as e:
        browser_instance = None
        return f"❌ Error starting browser: {str(e)}"


def start_browser_sync():
    """Sync wrapper for starting browser."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(start_browser_instance())


async def run_browser_automation(prompt: str, model_name: str, progress=gr.Progress()):
    """Run browser automation with the given prompt."""
    global browser_instance

    if not prompt.strip():
        return "❌ Please enter a prompt to get started.", ""

    progress(0, desc="Initializing...")

    # Use Gemini model
    llm = ChatGoogle(model=model_name, thinking_budget=1)

    # Check if browser was pre-started (user logged in)
    if browser_instance is None:
        progress(0.1, desc="Starting browser with persistent profile...")
        browser_instance = Browser(
            headless=False,
            keep_alive=True,
            user_data_dir=str(BROWSER_PROFILE_DIR),
        )
        await browser_instance.start()
    else:
        progress(0.1, desc="Using existing browser session with your logins!")

    tools = Tools()

    # ========== ENHANCED GUMMYSEARCH TOOLS ==========
    # Based on detailed analysis of GummySearch structure:
    # - Audiences: Collections of related subreddits
    # - Themes: AI-categorized posts (Solution Requests, Pain & Anger, etc.)
    # - Topics: AI-extracted keywords/concepts
    # - Patterns: AI-summarized common needs

    @tools.action(description="Login to GummySearch with credentials")
    async def login_gummy(
        browser_session,
        email: str = "noonou7@gmail.com",
        password: str = "HENKgumm1990",
    ):
        """Automated login to GummySearch."""
        page = await browser_session.get_current_page()
        await page.goto("https://go.gummysearch.com/login/", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        try:
            await page.fill('input[name="email"], input[type="email"]', email)
            await page.wait_for_timeout(500)
            await page.fill('input[name="password"], input[type="password"]', password)
            await page.wait_for_timeout(500)
            await page.click(
                'button[type="submit"], button:has-text("Login"), button:has-text("Sign in")'
            )
            await page.wait_for_timeout(3000)
            return f"Logged in to GummySearch as {email}"
        except Exception as e:
            return f"Login failed or already logged in: {str(e)}"

    @tools.action(description="Navigate to GummySearch curated audiences")
    async def navigate_gummy_audiences(browser_session):
        """Navigate to GummySearch curated audiences page to discover underserved markets."""
        page = await browser_session.get_current_page()
        await page.goto(
            "https://go.gummysearch.com/audiences/curated/", wait_until="networkidle"
        )
        await page.wait_for_timeout(3000)
        return "Navigated to GummySearch curated audiences. Look for audiences with high engagement but few solutions."

    @tools.action(description="Navigate to a specific GummySearch audience by ID")
    async def navigate_gummy_audience(browser_session, audience_id: str):
        """Navigate to a specific audience. Example IDs: 092b8570cd (AirBnB Hosts)"""
        page = await browser_session.get_current_page()
        await page.goto(
            f"https://go.gummysearch.com/audience/{audience_id}/", wait_until="networkidle"
        )
        await page.wait_for_timeout(3000)
        return f"Navigated to audience {audience_id}. Use navigate_gummy_theme() to explore themes."

    @tools.action(description="Navigate to a GummySearch theme for current audience")
    async def navigate_gummy_theme(
        browser_session,
        audience_id: str,
        theme: str = "solutions"
    ):
        """Navigate to a theme. Themes: solutions, pain, advice, self-promotion, ideas, money, hot, top"""
        theme_map = {
            "solutions": "solutions",
            "solution_requests": "solutions",
            "pain": "pain",
            "pain_anger": "pain",
            "advice": "advice",
            "advice_requests": "advice",
            "self-promotion": "self-promotion",
            "ideas": "ideas",
            "money": "money",
            "money_talk": "money",
            "hot": "hot",
            "top": "top",
        }
        theme_slug = theme_map.get(theme.lower(), theme)
        page = await browser_session.get_current_page()
        url = f"https://go.gummysearch.com/audience/{audience_id}/themes/{theme_slug}/"
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        return f"Navigated to {theme} theme. Use extract_gummy_theme_posts() to get posts."

    @tools.action(description="Extract posts from GummySearch theme results")
    async def extract_gummy_theme_posts(browser_session, max_posts: int = 50):
        """Extract structured post data from GummySearch theme results page."""
        page = await browser_session.get_current_page()
        
        # First click "Browse all" if visible to open results dialog
        try:
            browse_btn = await page.query_selector('a:has-text("Browse all"), button:has-text("Browse all")')
            if browse_btn:
                await browse_btn.click()
                await page.wait_for_timeout(2000)
        except Exception:
            pass
        
        posts = await page.evaluate(
            """
            (maxPosts) => {
                const results = [];
                // GummySearch uses listitem elements for posts
                const items = document.querySelectorAll('li[role="listitem"], [role="listitem"]');
                
                items.forEach((item, idx) => {
                    if (idx >= maxPosts) return;
                    
                    const text = item.textContent || '';
                    const links = item.querySelectorAll('a');
                    let title = '';
                    let body = '';
                    let subreddit = '';
                    let category = '';
                    let upvotes = '';
                    let comments = '';
                    let date = '';
                    let author = '';
                    
                    // Extract title from heading
                    const heading = item.querySelector('h1, h2, h3, h4, h5, h6');
                    if (heading) title = heading.textContent.trim();
                    
                    // Extract links for title and body
                    links.forEach(link => {
                        const href = link.getAttribute('href') || '';
                        const linkText = link.textContent.trim();
                        if (href.includes('reddit.com') && linkText.length > 20) {
                            if (!title) title = linkText;
                            else if (!body) body = linkText;
                        }
                        if (linkText.startsWith('r/')) subreddit = linkText;
                        if (linkText.startsWith('u/')) author = linkText;
                    });
                    
                    // Extract metadata from text patterns
                    const upvoteMatch = text.match(/↑\\s*(\\d+)/);
                    const commentMatch = text.match(/💬\\s*(\\d+)|○\\s*(\\d+)/);
                    const dateMatch = text.match(/(\\w{3}\\s+\\d{1,2}\\/\\d{1,2}\\/\\d{4}|\\d{1,2}\\/\\d{1,2}\\/\\d{4})/);
                    
                    if (upvoteMatch) upvotes = upvoteMatch[1];
                    if (commentMatch) comments = commentMatch[1] || commentMatch[2];
                    if (dateMatch) date = dateMatch[1];
                    
                    // Extract category tags
                    const categoryPatterns = ['Software Tool', 'Service', 'Physical Product', 'Website', 'API', 'Mobile App', 'Frustration', 'Disappointment', 'Advice'];
                    categoryPatterns.forEach(cat => {
                        if (text.includes(cat)) category = cat;
                    });
                    
                    if (title && title.length > 10) {
                        results.push({
                            title: title.substring(0, 200),
                            body: body.substring(0, 500),
                            subreddit,
                            category,
                            upvotes,
                            comments,
                            date,
                            author
                        });
                    }
                });
                
                return results;
            }
            """,
            max_posts
        )
        
        return f"Extracted {len(posts)} posts from GummySearch:\n{posts}"

    @tools.action(description="Extract GummySearch patterns (AI-summarized common needs)")
    async def extract_gummy_patterns(browser_session):
        """Navigate to Patterns tab and extract AI-grouped patterns. Must be on a theme page first."""
        page = await browser_session.get_current_page()
        
        # Click Patterns tab
        try:
            patterns_link = await page.query_selector('a:has-text("Patterns"), [href*="patterns"]')
            if patterns_link:
                await patterns_link.click()
                await page.wait_for_timeout(2000)
            
            # Click Find Patterns button if needed
            find_btn = await page.query_selector('button:has-text("Find Patterns")')
            if find_btn:
                await find_btn.click()
                await page.wait_for_timeout(5000)  # Patterns take time to generate
        except Exception:
            pass
        
        patterns = await page.evaluate(
            """
            () => {
                const results = [];
                // Look for pattern cards
                const patternElements = document.querySelectorAll('[class*="pattern"], [data-pattern]');
                
                // Fallback: look for structured content
                const headings = document.querySelectorAll('h3, h4');
                headings.forEach(h => {
                    const text = h.textContent || '';
                    const parent = h.closest('div, article, section');
                    if (parent && text.length > 5) {
                        const bullets = parent.querySelectorAll('li, p');
                        const examples = [];
                        bullets.forEach(b => {
                            const bText = b.textContent.trim();
                            if (bText.startsWith('-') || bText.length > 20) {
                                examples.push(bText.substring(0, 200));
                            }
                        });
                        
                        // Extract count from pattern header
                        const countMatch = text.match(/(\\d+)\\s*>/);
                        const count = countMatch ? countMatch[1] : '';
                        
                        if (examples.length > 0 || count) {
                            results.push({
                                pattern: text.trim(),
                                count,
                                examples: examples.slice(0, 5)
                            });
                        }
                    }
                });
                
                return results;
            }
            """
        )
        
        return f"Extracted {len(patterns)} patterns:\n{patterns}"

    @tools.action(description="Extract GummySearch topics for an audience")
    async def extract_gummy_topics(browser_session, audience_id: str):
        """Navigate to Topics tab and extract topic list with counts."""
        page = await browser_session.get_current_page()
        await page.goto(
            f"https://go.gummysearch.com/audience/{audience_id}/topics/", wait_until="networkidle"
        )
        await page.wait_for_timeout(3000)
        
        topics = await page.evaluate(
            """
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href*="/topics/"]');
                
                links.forEach(link => {
                    const text = link.textContent || '';
                    const parent = link.closest('div, li');
                    const fullText = parent ? parent.textContent : text;
                    
                    // Extract topic name and metadata
                    const topicMatch = text.match(/^([A-Za-z\\s-]+)/);
                    const growthMatch = fullText.match(/-?\\d+%/);
                    const subredditMatch = fullText.match(/r\\/[\\w_]+/g);
                    
                    if (topicMatch && topicMatch[1].trim().length > 2) {
                        results.push({
                            topic: topicMatch[1].trim(),
                            growth: growthMatch ? growthMatch[0] : '',
                            subreddits: subredditMatch || []
                        });
                    }
                });
                
                // Dedupe
                const seen = new Set();
                return results.filter(t => {
                    if (seen.has(t.topic)) return false;
                    seen.add(t.topic);
                    return true;
                });
            }
            """
        )
        
        return f"Extracted {len(topics)} topics:\n{topics}"

    @tools.action(description="Get GummySearch theme summary with counts")
    async def get_gummy_theme_summary(browser_session, audience_id: str):
        """Get summary of all themes with post counts for an audience."""
        page = await browser_session.get_current_page()
        await page.goto(
            f"https://go.gummysearch.com/audience/{audience_id}/themes/", wait_until="networkidle"
        )
        await page.wait_for_timeout(3000)
        
        themes = await page.evaluate(
            """
            () => {
                const results = [];
                const themeLinks = document.querySelectorAll('a[href*="/themes/"]');
                
                themeLinks.forEach(link => {
                    const text = link.textContent || '';
                    // Match patterns like "Solution Requests 211" or "Pain & Anger 168"
                    const match = text.match(/([A-Za-z&\\s]+)\\s+(\\d+)/);
                    if (match) {
                        results.push({
                            theme: match[1].trim(),
                            count: parseInt(match[2])
                        });
                    }
                });
                
                return results;
            }
            """
        )
        
        return f"Theme summary:\n{themes}"

    @tools.action(description="Search GummySearch within an audience")
    async def search_gummy_audience(browser_session, audience_id: str, query: str):
        """Search within a specific audience using keyword search."""
        page = await browser_session.get_current_page()
        await page.goto(
            f"https://go.gummysearch.com/audience/{audience_id}/", wait_until="networkidle"
        )
        await page.wait_for_timeout(2000)
        
        try:
            search_input = await page.query_selector(
                'input[placeholder*="Keyword" i], input[placeholder*="search" i]'
            )
            if search_input:
                await search_input.fill(query)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(3000)
                return f"Searched audience {audience_id} for: {query}"
            return "Could not find search input"
        except Exception as e:
            return f"Search error: {str(e)}"

    # ========== ENHANCED REDDIT TOOLS ==========
    # Improved Reddit scraping with intent classification (like GummySearch themes)

    @tools.action(description="Search Reddit for pain points and problems")
    async def search_reddit(
        browser_session, subreddit: str, query: str, sort: str = "relevance", time_filter: str = "year"
    ):
        """Search Reddit subreddit. sort: hot, new, top, relevance. time_filter: hour, day, week, month, year, all."""
        page = await browser_session.get_current_page()
        search_url = f"https://www.reddit.com/r/{subreddit}/search/?q={query}&sort={sort}&restrict_sr=1&t={time_filter}"
        await page.goto(search_url, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        return f"Searched r/{subreddit} for '{query}' sorted by {sort}, time={time_filter}"

    @tools.action(description="Search Reddit with SaaS intent queries")
    async def search_reddit_saas_intent(
        browser_session, subreddit: str, intent: str = "solution_request"
    ):
        """Search Reddit with pre-built SaaS discovery queries by intent type."""
        intent_queries = {
            "solution_request": "looking for tool OR looking for software OR anyone know of OR recommend a",
            "pain_point": "frustrated with OR hate when OR struggle with OR waste of time",
            "advice_request": "how do you OR what do you use OR best way to",
            "willingness_to_pay": "would pay for OR budget for OR worth paying OR subscription",
            "competition_gap": "alternative to OR better than OR replacement for",
        }
        query = intent_queries.get(intent, intent_queries["solution_request"])
        page = await browser_session.get_current_page()
        search_url = f"https://www.reddit.com/r/{subreddit}/search/?q={query}&sort=relevance&restrict_sr=1&t=year"
        await page.goto(search_url, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        return f"Searched r/{subreddit} for {intent} intent"

    @tools.action(description="Navigate to a specific subreddit")
    async def navigate_subreddit(browser_session, subreddit: str, sort: str = "hot"):
        """Navigate to subreddit. sort: hot, new, top, rising."""
        page = await browser_session.get_current_page()
        await page.goto(
            f"https://www.reddit.com/r/{subreddit}/{sort}/", wait_until="networkidle"
        )
        await page.wait_for_timeout(2000)
        return f"Navigated to r/{subreddit} ({sort})"

    @tools.action(description="Extract Reddit posts with full metadata and intent classification")
    async def extract_reddit_posts(browser_session, max_posts: int = 20):
        """Extract structured post data from Reddit with SaaS validation signals."""
        page = await browser_session.get_current_page()

        posts = await page.evaluate(
            """
            (maxPosts) => {
                const results = [];
                
                // Intent classification keywords
                const intents = {
                    solution_request: ['looking for', 'recommend', 'anyone know', 'tool for', 'software for', 'app for', 'what do you use'],
                    pain_point: ['frustrated', 'hate', 'annoying', 'struggle', 'waste of time', 'inefficient', 'broken', 'sucks'],
                    advice_request: ['how do you', 'how to', 'best way', 'tips for', 'advice on', 'help with'],
                    willingness_to_pay: ['would pay', 'pay for', 'budget', 'worth paying', 'subscription', 'pricing', 'cost'],
                    idea: ['idea', 'what if', 'suggestion', 'feature request', 'wish there was'],
                    self_promotion: ['built', 'created', 'launched', 'just released', 'my app', 'my tool', 'feedback on']
                };
                
                function classifyIntent(text) {
                    const lower = text.toLowerCase();
                    const detected = [];
                    for (const [intent, keywords] of Object.entries(intents)) {
                        for (const kw of keywords) {
                            if (lower.includes(kw)) {
                                detected.push(intent);
                                break;
                            }
                        }
                    }
                    return detected.length ? detected : ['general'];
                }
                
                // Try multiple selectors for Reddit posts
                const postSelectors = [
                    'shreddit-post',
                    '[data-testid="post-container"]',
                    'article',
                    '.Post',
                    '.thing.link'
                ];
                
                let posts = [];
                for (const selector of postSelectors) {
                    posts = document.querySelectorAll(selector);
                    if (posts.length > 0) break;
                }

                posts.forEach((post, idx) => {
                    if (idx >= maxPosts) return;
                    
                    let title = '';
                    let body = '';
                    let upvotes = '0';
                    let comments = '0';
                    let author = '';
                    let timestamp = '';
                    let url = '';
                    let subreddit = '';
                    
                    // shreddit-post (new Reddit)
                    if (post.tagName === 'SHREDDIT-POST') {
                        title = post.getAttribute('post-title') || '';
                        author = post.getAttribute('author') || '';
                        upvotes = post.getAttribute('score') || '0';
                        comments = post.getAttribute('comment-count') || '0';
                        url = post.getAttribute('permalink') || '';
                        subreddit = post.getAttribute('subreddit-prefixed-name') || '';
                    } else {
                        // Fallback selectors
                        title = post.querySelector('h3, h2, [slot="title"], a.title, .title')?.textContent?.trim() || '';
                        body = post.querySelector('[slot="text-body"], .md, .usertext-body, p')?.textContent?.trim() || '';
                        upvotes = post.querySelector('[data-testid="post-vote-score"], .score, faceplate-number')?.textContent || '0';
                        comments = post.querySelector('a[href*="comments"]')?.textContent?.match(/\\d+/)?.[0] || '0';
                        author = post.querySelector('a[href*="/user/"]')?.textContent || '';
                        const timeEl = post.querySelector('time, [datetime]');
                        timestamp = timeEl?.getAttribute('datetime') || timeEl?.textContent || '';
                    }
                    
                    if (title && title.length > 10) {
                        const fullText = title + ' ' + body;
                        const intentTypes = classifyIntent(fullText);
                        
                        // Calculate validation score
                        let validationScore = 0;
                        if (intentTypes.includes('solution_request')) validationScore += 3;
                        if (intentTypes.includes('pain_point')) validationScore += 2;
                        if (intentTypes.includes('willingness_to_pay')) validationScore += 4;
                        validationScore += Math.min(parseInt(upvotes) / 10, 3);
                        validationScore += Math.min(parseInt(comments) / 20, 2);
                        
                        results.push({
                            title: title.substring(0, 200),
                            body: body.substring(0, 500),
                            upvotes: upvotes,
                            comments: comments,
                            author: author,
                            timestamp: timestamp,
                            subreddit: subreddit,
                            url: url,
                            intents: intentTypes,
                            validation_score: Math.round(validationScore * 10) / 10
                        });
                    }
                });
                
                // Sort by validation score
                results.sort((a, b) => b.validation_score - a.validation_score);
                return results;
            }
            """,
            max_posts
        )

        return f"Extracted {len(posts)} posts with intent classification:\n{posts}"

    @tools.action(
        description="Check for willingness-to-pay signals in extracted content"
    )
    async def check_payment_signals(browser_session, content: str):
        """Analyze content for willingness-to-pay indicators."""
        payment_keywords = [
            "paid for",
            "pay for",
            "subscription",
            "subscribe",
            "monthly fee",
            "would pay",
            "willing to pay",
            "looking for paid",
            "budget",
            "paid tool",
            "paid service",
            "pricing",
            "cost",
            "expensive",
            "cheaper alternative",
            "paid version",
            "premium",
            "enterprise",
        ]

        pain_keywords = [
            "frustrated",
            "hate",
            "annoying",
            "problem",
            "issue",
            "struggle",
            "difficult",
            "time-consuming",
            "manual",
            "inefficient",
            "slow",
            "broken",
            "doesn't work",
            "wish there was",
            "need",
            "looking for",
        ]

        content_lower = content.lower()
        payment_signals = [kw for kw in payment_keywords if kw in content_lower]
        pain_signals = [kw for kw in pain_keywords if kw in content_lower]

        signal_summary = {
            "payment_signals_found": len(payment_signals),
            "payment_keywords": payment_signals[:10],
            "pain_signals_found": len(pain_signals),
            "pain_keywords": pain_signals[:10],
            "validation_score": (len(payment_signals) * 2) + len(pain_signals),
        }

        return f"Payment/Pain Analysis:\n{signal_summary}"

    @tools.action(description="Navigate to a specific URL")
    async def navigate_to(browser_session, url: str):
        page = await browser_session.get_current_page()
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        return f"Navigated to: {url}"

    @tools.action(description="Wait for the page to load")
    async def wait_for_load(browser_session, seconds: int = 3):
        await browser_session.get_current_page()
        await browser_session.get_current_page().wait_for_timeout(seconds * 1000)
        return f"Waited {seconds} seconds for page to load"

    @tools.action(description="Scroll down the page and extract new content")
    async def scroll_and_extract(browser_session, amount: int = 3):
        """Scroll down and return newly visible content."""
        page = await browser_session.get_current_page()

        for i in range(amount):
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(800)

        # Extract new content after scrolling
        content = await page.evaluate(
            """
        () => {
            const elements = document.querySelectorAll('[data-testid="post"], article, .Post, .thing');
            const texts = [];
            elements.forEach(el => {
                const text = el.textContent || el.innerText;
                if (text && text.length > 20 && text.length < 1000) {
                    texts.push(text.trim());
                }
            });
            return [...new Set(texts)].slice(0, 20).join('\\n---\\n');
        }
        """
        )

        return f"Scrolled {amount} times. New content:\n{content[:8000] if content else 'No content extracted'}"

    @tools.action(description="Click on a Reddit post to read full discussion")
    async def click_reddit_post(browser_session, post_index: int = 0):
        """Click on a Reddit post by index to read full discussion and comments."""
        page = await browser_session.get_current_page()

        try:
            posts = await page.query_selector_all(
                '[data-testid="post"], a[data-click-id="body"], .thing'
            )
            if posts and post_index < len(posts):
                await posts[post_index].click()
                await page.wait_for_timeout(2000)
                return f"Clicked post {post_index}. Reading full discussion for validation..."
            return f"Post {post_index} not found"
        except Exception as e:
            return f"Error clicking post: {str(e)}"

    @tools.action(description="Extract comments from current Reddit post")
    async def extract_comments(browser_session):
        """Extract top comments for additional validation signals."""
        page = await browser_session.get_current_page()

        comments = await page.evaluate(
            """
        () => {
            const commentElements = document.querySelectorAll('[data-testid="comment"], .comment, .usertext-body');
            const extracted = [];
            commentElements.forEach(el => {
                const text = el.textContent || el.innerText;
                if (text && text.length > 30 && text.length < 2000) {
                    extracted.push(text.trim());
                }
            });
            return extracted.slice(0, 20).join('\\n---\\n');
        }
        """
        )

        return f"Extracted comments:\n{comments[:10000] if comments else 'No comments found'}"

    @tools.action(description="Search Google for competition analysis")
    async def google_competition_check(browser_session, search_query: str):
        """Search Google to check existing solutions/competition for an idea."""
        page = await browser_session.get_current_page()
        await page.goto(
            f"https://www.google.com/search?q={search_query}", wait_until="networkidle"
        )
        await page.wait_for_timeout(2000)

        # Count ads and organic results
        results_info = await page.evaluate(
            """
        () => {
            const ads = document.querySelectorAll('[data-text-ad]').length;
            const organic = document.querySelectorAll('#search .g, .g').length;
            const related = document.querySelectorAll('#related searches, .related-search-pairs').length;
            return {ads, organic, related};
        }
        """
        )

        return f"Competition check for '{search_query}': Ads={results_info.get('ads', 0)}, Organic Results={results_info.get('organic', 0)}. High ads = established market."

    @tools.action(description="Go back to previous page")
    async def go_back(browser_session):
        page = await browser_session.get_current_page()
        await page.go_back()
        await page.wait_for_timeout(1000)
        return "Navigated back to previous page"

    # Build the task with user's prompt
    task = f"""
You are an expert SaaS Idea Discovery and Validation Agent. Your goal is to find "super validated hidden gems" - niche SaaS ideas with real market demand.

USER REQUEST: {prompt}

========== VALIDATION FRAMEWORK ==========
A "super validated" SaaS idea must have MULTIPLE of these signals:
1. PAIN SIGNALS: Emotional language (hate, frustrated, struggle, waste of time)
2. PAYMENT SIGNALS: Explicit willingness to pay (would pay, budget, looking for paid solution)
3. RECENCY: Discussions from the last 6 months (not archived problems)
4. FREQUENCY: Same problem mentioned across multiple sources/posts
5. ENGAGEMENT: High upvotes/comments on Reddit, indicating共鸣
6. COMPETITION GAP: Many complaints but few commercial solutions

========== AVAILABLE TOOLS ==========

GUMMYSEARCH TOOLS (for structured audience research):
- login_gummy(email, password): Auto-login to GummySearch
- navigate_gummy_audiences(): Browse curated audiences
- navigate_gummy_audience(audience_id): Go to specific audience (e.g., "092b8570cd")
- navigate_gummy_theme(audience_id, theme): Go to theme (solutions/pain/advice/ideas/money)
- extract_gummy_theme_posts(max_posts): Extract posts from current theme
- extract_gummy_patterns(): Get AI-summarized patterns (common needs)
- extract_gummy_topics(audience_id): Get topic list with counts
- get_gummy_theme_summary(audience_id): Get all themes with counts
- search_gummy_audience(audience_id, query): Search within audience

REDDIT TOOLS (direct scraping with intent classification):
- search_reddit(subreddit, query, sort, time_filter): Search subreddit
- search_reddit_saas_intent(subreddit, intent): Search by intent type (solution_request/pain_point/advice_request/willingness_to_pay/competition_gap)
- navigate_subreddit(subreddit, sort): Go to subreddit
- extract_reddit_posts(max_posts): Extract posts with intent classification & validation scores
- click_reddit_post(index): Click post for full discussion
- extract_comments(): Extract comments for deeper validation

UTILITY TOOLS:
- check_payment_signals(content): Analyze for willingness-to-pay keywords
- scroll_and_extract(amount): Scroll and extract content
- google_competition_check(query): Check competition on Google
- navigate_to(url): Navigate to any URL
- wait_for_load(seconds): Wait for page load
- go_back(): Go back to previous page

========== RESEARCH METHODOLOGY ==========
FOLLOW THIS SYSTEMATIC APPROACH:

PHASE 1: DISCOVERY
1. Start with GummySearch curated audiences: navigate_gummy_audiences()
2. Look for audiences that are:
   - Business/professional contexts (B2B willing to pay)
   - Niche/underserved (not general "startups" or "marketing")
   - Recent activity (not abandoned communities)
3. For each promising audience, search_gummy() to find discussions

PHASE 2: REDDIT VALIDATION (Cross-reference)
4. Pick relevant subreddits based on the audience:
   - r/SaaS, r/Entrepreneur, r/IndieHackers for business tools
   - Niche subreddits (r/freelance, r/consulting, r/realestateinvesting, etc.)
5. search_reddit() for problem phrases: "looking for tool", "how do you", "hate when", "struggle with"
6. extract_saas_signals() to get structured data with engagement metrics

PHASE 3: DEEP DIVE ON PROMISING IDEAS
7. For posts with high engagement: click_reddit_post() then extract_comments()
8. check_payment_signals() on both post and comments
9. Look for "I would pay for", "budget for", "currently using [expensive tool]"

PHASE 4: COMPETITION ANALYSIS
10. google_competition_check() with "[problem] software" or "[problem] tool"
11. Low ads + low organic results = OPPORTUNITY
12. High ads = Established market, needs differentiation

PHASE 5: SYNTHESIS & SCORING
For EACH SaaS idea found, provide:
- **Problem Statement**: Clear description of the pain point
- **Target Audience**: Specific, identifiable segment
- **Validation Score (1-10)**: Based on signals collected
- **Payment Signals**: Evidence of willingness to pay
- **Competition Level**: Low/Medium/High with reasoning
- **Estimated Market Size**: Based on subreddit size/engagement
- **Recommended Next Steps**: Specific validation actions

========== OUTPUT FORMAT ==========
When complete, present findings in this structure:

## VALIDATED SAAS IDEAS (Ranked by Validation Score)

### 1. [Idea Name] - Score: X/10
**Problem:** [Clear pain point]
**Target:** [Specific audience]
**Payment Signals:** [Direct quotes showing willingness to pay]
**Competition:** [Analysis]
**Market Size:** [Estimated]
**Sources:** [Number of mentions across platforms]

### 2. [Idea Name] - Score: Y/10
[Same format...]

## SUMMARY STATISTICS
- Ideas Discovered: X
- High-Validation Ideas (Score 7+): Y
- Primary Sources: [Reddit, GummySearch, etc.]

OPTIONAL ATTACHMENTS:
If you create research notes or detailed findings, you can include them as attachments:
```
Attachments:

filename.md:
# Title
[Full content here with actual research data, not just headers]
```

IMPORTANT: If you mention attachments, make sure they contain actual content (research notes, extracted data, etc.), not just empty headers. Use write_file tool to save detailed research notes if needed.

Be thorough. Cross-reference across platforms. Prioritize ideas with BOTH pain and payment signals.
"""

    progress(0.2, desc="Starting agent...")

    try:
        agent = Agent(
            task=task,
            llm=llm,
            demo_mode=True,
            browser=browser_instance,
            tools=tools,
        )

        progress(0.3, desc="Running automation...")
        history = await agent.run()

        progress(0.9, desc="Processing results...")

        result = history.final_result()

        # Format the result nicely
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        formatted_result = f"""## 🎯 Results

**Completed at:** {timestamp}

**Model:** {model_name}

---

{result if result else "No results returned from the agent."}

---

*Results generated by Browser Automation with Gemini*
"""

        # Generate a log of actions taken
        action_log = "## 📋 Action Log\n\n"
        try:
            actions = list(history.model_actions())
            for i, action in enumerate(actions, 1):
                action_log += f"{i}. {str(action)[:200]}\n"
        except Exception:
            action_log += "No actions recorded\n"

        # Save results to markdown file
        file_path, saved_attachments = save_results_markdown(
            formatted_result, action_log, prompt, model_name
        )

        # Append saved file info to the displayed results
        saved_note = f"\n\n> Saved to: `{file_path}`"
        if saved_attachments:
            # Show relative paths for easy clicking
            rels = []
            for p in saved_attachments:
                try:
                    rels.append(str(Path(p).relative_to(Path.cwd())))
                except Exception:
                    rels.append(p)
            saved_note += "\n> Attachments saved: " + ", ".join(f"`{r}`" for r in rels)

        progress(1.0, desc="Complete!")

        return formatted_result + saved_note, action_log

    except Exception as e:
        return f"❌ Error during automation: {str(e)}", ""
    finally:
        # Don't close browser - let user close it manually
        pass


def run_async_task(prompt: str, model_name: str):
    """Wrapper to run async task in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(run_browser_automation(prompt, model_name))


async def close_browser_instance():
    """Close the browser instance."""
    global browser_instance
    
    if browser_instance is not None:
        try:
            await browser_instance.stop()
        except Exception:
            pass
        try:
            await browser_instance.close()
        except Exception:
            pass
        browser_instance = None
        return "✅ Browser closed successfully."
    return "ℹ️ No browser instance to close."


def close_browser_sync():
    """Sync wrapper for closing browser."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(close_browser_instance())


# Example prompts for quick start - SaaS Idea Validation focused
EXAMPLE_PROMPTS = [
    "Find 5 super validated niche SaaS ideas. Start by logging into https://go.gummysearch.com/login/ (noonou7@gmail.com / HENKgumm1990), then browse curated audiences to find underserved B2B markets willing to pay. Cross-reference on Reddit subreddits for payment signals and competition gap analysis.",
    "Discover validated SaaS opportunities for freelance professionals. Research r/freelance and r/upwork, extract pain points with willingness-to-pay signals, and check competition levels.",
    "Find profitable micro-SaaS ideas in the real estate investing niche. Use GummySearch audiences and Reddit validation to identify underserved problems with payment signals.",
    "Research SaaS opportunities for content creators and YouTubers. Cross-reference pain points across Reddit communities and validate with competition analysis.",
    "Identify underserved markets in the healthcare/medical space that would pay for B2B SaaS tools. Use systematic validation across multiple sources.",
]


def load_example():
    """Load a random example prompt."""
    return random.choice(EXAMPLE_PROMPTS)


def get_existing_reports():
    """List all existing report files."""
    if not RESULTS_DIR.exists():
        return []
    reports = sorted(list(RESULTS_DIR.glob("*.md")), key=lambda p: p.stat().st_mtime, reverse=True)
    return [r.name for r in reports]


def load_report(filename):
    """Load content of a specific report."""
    if not filename:
        return ""
    try:
        file_path = RESULTS_DIR / filename
        if not file_path.exists():
            return f"❌ Report not found: {filename}"
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"❌ Error loading report: {str(e)}"


# Build the Gradio interface with dark theme
with gr.Blocks(
    title="SaaS Idea Discovery - Browser Automation",
    theme=gr.themes.Base(
        primary_hue="amber",
        secondary_hue="slate",
        neutral_hue="slate",
        font=["JetBrains Mono", "Fira Code", "monospace"],
    ).set(
        body_background_fill="#0f0f0f",
        body_background_fill_dark="#0f0f0f",
        body_text_color="#e0e0e0",
        body_text_color_dark="#e0e0e0",
        block_background_fill="#1a1a1a",
        block_background_fill_dark="#1a1a1a",
        block_border_color="#2a2a2a",
        block_border_color_dark="#2a2a2a",
        block_label_text_color="#ffb000",
        block_label_text_color_dark="#ffb000",
        block_title_text_color="#ffb000",
        block_title_text_color_dark="#ffb000",
        input_background_fill="#252525",
        input_background_fill_dark="#252525",
        input_border_color="#3a3a3a",
        input_border_color_dark="#3a3a3a",
        button_primary_background_fill="#ff8c00",
        button_primary_background_fill_dark="#ff8c00",
        button_primary_text_color="#000000",
        button_primary_text_color_dark="#000000",
        button_secondary_background_fill="#2a2a2a",
        button_secondary_background_fill_dark="#2a2a2a",
        button_secondary_text_color="#e0e0e0",
        button_secondary_text_color_dark="#e0e0e0",
    ),
    css="""
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    
    .gradio-container { 
        max-width: 1600px !important; 
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0f0f0f 100%) !important;
    }
    
    /* Report viewer styling */
    .report-viewer {
        min-height: 600px;
        max-height: 80vh;
        overflow-y: auto;
        padding: 24px;
        border-radius: 12px;
        background: linear-gradient(180deg, #1a1a1a 0%, #141414 100%);
        border: 1px solid #2a2a2a;
        color: #e0e0e0 !important;
    }
    
    .report-viewer h1, .report-viewer h2, .report-viewer h3 {
        color: #ffb000 !important;
        border-bottom: 1px solid #333;
        padding-bottom: 8px;
        margin-top: 20px;
    }
    
    .report-viewer h1 { font-size: 1.8em; }
    .report-viewer h2 { font-size: 1.4em; color: #ff8c00 !important; }
    .report-viewer h3 { font-size: 1.2em; color: #ffa500 !important; }
    
    .report-viewer a {
        color: #4da6ff !important;
        text-decoration: underline;
    }
    
    .report-viewer a:hover {
        color: #80c4ff !important;
    }
    
    .report-viewer code {
        background: #252525;
        padding: 2px 6px;
        border-radius: 4px;
        color: #7ee787;
        font-family: 'JetBrains Mono', monospace;
    }
    
    .report-viewer pre {
        background: #1e1e1e;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 16px;
        overflow-x: auto;
    }
    
    .report-viewer blockquote {
        border-left: 4px solid #ff8c00;
        padding-left: 16px;
        margin: 16px 0;
        background: #1e1e1e;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        color: #b0b0b0;
        font-style: italic;
    }
    
    .report-viewer ul, .report-viewer ol {
        padding-left: 24px;
    }
    
    .report-viewer li {
        margin: 8px 0;
        line-height: 1.6;
    }
    
    .report-viewer strong {
        color: #ffcc00;
    }
    
    .report-viewer em {
        color: #a0a0a0;
    }
    
    .report-viewer hr {
        border: none;
        border-top: 1px solid #333;
        margin: 24px 0;
    }
    
    /* Sidebar styling */
    .report-sidebar {
        background: #141414;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #2a2a2a;
    }
    
    /* Result box styling */
    .result-box {
        min-height: 400px;
        padding: 20px;
        border-radius: 12px;
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        color: #e0e0e0 !important;
    }
    
    /* Tab styling */
    .tabs { border-radius: 12px; }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1a1a1a;
    }
    ::-webkit-scrollbar-thumb {
        background: #444;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
    
    /* Report metadata card */
    .report-meta {
        background: linear-gradient(135deg, #1e1e1e 0%, #252525 100%);
        border: 1px solid #333;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 16px;
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }
    
    .report-meta-item {
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .report-meta-label {
        color: #888;
        font-size: 0.85em;
    }
    
    .report-meta-value {
        color: #ffb000;
        font-weight: 500;
    }
    """,
) as demo:
    gr.Markdown(
        """
    # 🔥 SaaS Idea Discovery Engine
    *Browser automation powered by Gemini AI*
    """
    )

    with gr.Tabs():
        with gr.Tab("🤖 Automation", id="automation"):
            gr.Markdown(
                """
            ### Launch browser automation to discover validated SaaS opportunities
            """
            )
            with gr.Row():
                with gr.Column(scale=2):
                    prompt_input = gr.Textbox(
                        label="📝 Research Prompt",
                        placeholder="Describe what you want to research... e.g., 'Find 5 validated SaaS ideas in the freelance niche'",
                        lines=5,
                        max_lines=12,
                    )

                    with gr.Row():
                        model_dropdown = gr.Dropdown(
                            choices=[
                                "gemini-3-flash-preview",
                                "gemini-3-pro-preview",
                            ],
                            value="gemini-3-flash-preview",
                            label="🤖 AI Model",
                        )
                        example_btn = gr.Button("🎲 Random Example", variant="secondary")

                    with gr.Row():
                        start_browser_btn = gr.Button(
                            "🚀 Start Browser", variant="primary", size="lg"
                        )
                        run_btn = gr.Button("▶️ Run Research", variant="primary", size="lg")
                        close_btn = gr.Button("🛑 Stop", variant="stop")

                    status_msg = gr.Textbox(
                        label="Status",
                        value="Ready. Click 'Start Browser' to begin.",
                        interactive=False,
                    )

                with gr.Column(scale=1):
                    gr.Markdown(
                        """
                    ### 💡 Quick Tips

                    1. **Start Browser** opens a Chromium window
                    2. Log into GummySearch if needed
                    3. Enter your research goal
                    4. **Run Research** starts the AI agent
                    5. Watch it work in real-time!

                    ### 🎯 Best Prompts

                    - *"Find 5 validated B2B SaaS ideas"*
                    - *"Research pain points in [niche]"*
                    - *"Discover underserved markets"*
                    """
                    )

            gr.Markdown("---")

            with gr.Row():
                with gr.Column():
                    results_output = gr.Markdown(
                        label="📊 Results",
                        value="*Research results will appear here...*",
                        elem_classes=["result-box"],
                    )

                with gr.Column():
                    action_log_output = gr.Markdown(
                        label="📋 Action Log",
                        value="*Agent actions logged here...*",
                        elem_classes=["result-box"],
                    )

        with gr.Tab("📚 Report Library", id="library"):
            gr.Markdown(
                """
            ### Browse & Validate Your Research Reports
            *Click any report to view details, quotes, and source links*
            """
            )
            with gr.Row():
                with gr.Column(scale=1, elem_classes=["report-sidebar"]):
                    gr.Markdown("#### 📂 Saved Reports")
                    report_list = gr.Dropdown(
                        label="Select Report",
                        choices=get_existing_reports(),
                        value=get_existing_reports()[0] if get_existing_reports() else None,
                        interactive=True,
                        allow_custom_value=False,
                    )
                    with gr.Row():
                        refresh_btn = gr.Button("🔄 Refresh", variant="secondary", size="sm")
                        delete_btn = gr.Button("🗑️ Delete", variant="stop", size="sm")
                    
                    gr.Markdown(
                        """
                    ---
                    #### 📊 Report Stats
                    *Select a report to see stats*
                    """
                    )
                    report_stats = gr.Markdown(
                        value="",
                        elem_classes=["report-meta"],
                    )
                    
                with gr.Column(scale=4):
                    report_viewer = gr.Markdown(
                        label="Report Content",
                        value="👈 Select a report from the sidebar to view its contents.\n\n*All links are clickable for manual validation.*",
                        elem_classes=["report-viewer"]
                    )

    # ========== EVENT HANDLERS ==========
    
    # --- Automation Tab ---
    start_browser_btn.click(
        fn=start_browser_sync,
        inputs=[],
        outputs=[status_msg],
    )

    run_btn.click(
        fn=run_async_task,
        inputs=[prompt_input, model_dropdown],
        outputs=[results_output, action_log_output],
    )

    close_btn.click(
        fn=close_browser_sync,
        inputs=[],
        outputs=[status_msg],
    )

    example_btn.click(
        fn=load_example,
        inputs=[],
        outputs=[prompt_input],
    )
    
    # --- Report Library Tab ---
    def get_report_stats(filename: str) -> str:
        """Extract statistics from a report."""
        if not filename:
            return ""
        try:
            content = load_report(filename)
            if content.startswith("❌"):
                return ""
            
            # Count various elements
            import re
            lines = content.split("\n")
            word_count = len(content.split())
            link_count = len(re.findall(r'https?://[^\s\)]+', content))
            idea_count = len(re.findall(r'###\s*\d+\.', content))
            quote_count = len(re.findall(r'["""]([^"""]+)["""]', content))
            
            # Extract date from filename
            date_match = re.search(r'(\d{8})_(\d{6})', filename)
            date_str = ""
            if date_match:
                d = date_match.group(1)
                t = date_match.group(2)
                date_str = f"{d[:4]}-{d[4:6]}-{d[6:]} {t[:2]}:{t[2:4]}"
            
            stats = f"""
**📅 Created:** {date_str}

**📝 Words:** {word_count:,}

**💡 Ideas Found:** {idea_count}

**🔗 Links:** {link_count}

**💬 Quotes:** {quote_count}
"""
            return stats
        except Exception:
            return ""
    
    def on_report_select(filename: str):
        """Handle report selection - load content and stats."""
        content = load_report(filename)
        stats = get_report_stats(filename)
        return content, stats
    
    report_list.change(
        fn=on_report_select,
        inputs=[report_list],
        outputs=[report_viewer, report_stats]
    )
    
    def refresh_reports():
        """Refresh the report list."""
        reports = get_existing_reports()
        return gr.Dropdown(choices=reports, value=reports[0] if reports else None)
        
    refresh_btn.click(
        fn=refresh_reports,
        inputs=[],
        outputs=[report_list]
    )
    
    def delete_report(filename: str):
        """Delete a report file."""
        if not filename:
            return gr.Dropdown(choices=get_existing_reports()), "No report selected", ""
        try:
            file_path = RESULTS_DIR / filename
            if file_path.exists():
                file_path.unlink()
            reports = get_existing_reports()
            new_value = reports[0] if reports else None
            new_content = load_report(new_value) if new_value else "Report deleted. Select another report."
            new_stats = get_report_stats(new_value) if new_value else ""
            return gr.Dropdown(choices=reports, value=new_value), new_content, new_stats
        except Exception as e:
            return gr.Dropdown(choices=get_existing_reports()), f"❌ Error deleting: {e}", ""
    
    delete_btn.click(
        fn=delete_report,
        inputs=[report_list],
        outputs=[report_list, report_viewer, report_stats]
    )
    
    # Auto-load first report on startup
    demo.load(
        fn=on_report_select,
        inputs=[report_list],
        outputs=[report_viewer, report_stats]
    )


def main():
    """Launch the Gradio UI."""
    print("\n" + "=" * 60)
    print("🌐 Browser Automation with Gemini - Web UI")
    print("=" * 60)
    print("\nStarting Gradio server...")
    print("Open the URL shown below in your browser to use the UI.\n")

    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=True,
    )


if __name__ == "__main__":
    main()
