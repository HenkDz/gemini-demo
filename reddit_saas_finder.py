"""
Reddit SaaS Idea Finder - Standalone Tool

This tool replicates GummySearch's core functionality for finding SaaS ideas directly from Reddit:
1. Searches multiple subreddits with intent-based queries
2. Classifies posts by intent (Solution Request, Pain Point, etc.)
3. Extracts structured data with validation scores
4. Uses AI to find patterns and summarize opportunities
5. Generates reports with actionable insights

THEMES (like GummySearch):
- Solution Requests: People looking for tools/software
- Pain & Anger: Frustrations and complaints
- Advice Requests: People asking how to do things
- Willingness to Pay: Budget/pricing discussions
- Ideas: Feature requests and suggestions
- Self-Promotion: People launching products

Usage:
    python reddit_saas_finder.py --subreddits "SaaS,Entrepreneur" --themes "solution,pain"
    python reddit_saas_finder.py --audience "airbnb_hosts" --full-analysis
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from browser_use import Browser
from dotenv import load_dotenv

load_dotenv()

# Try to import AI pattern extractor
try:
    from ai_pattern_extractor import AIPatternExtractor, format_opportunities_report
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class PostIntent(Enum):
    """Post intent classification (like GummySearch themes)."""
    SOLUTION_REQUEST = "solution_request"
    PAIN_POINT = "pain_point"
    ADVICE_REQUEST = "advice_request"
    WILLINGNESS_TO_PAY = "willingness_to_pay"
    IDEA = "idea"
    SELF_PROMOTION = "self_promotion"
    MONEY_TALK = "money_talk"
    GENERAL = "general"


@dataclass
class RedditPost:
    """Structured Reddit post with SaaS validation metadata."""
    title: str
    body: str = ""
    subreddit: str = ""
    author: str = ""
    upvotes: int = 0
    comments: int = 0
    url: str = ""
    timestamp: str = ""
    intents: list = field(default_factory=list)
    validation_score: float = 0.0
    payment_signals: list = field(default_factory=list)
    pain_signals: list = field(default_factory=list)


@dataclass
class SaaSPattern:
    """AI-identified pattern of common needs."""
    name: str
    description: str
    post_count: int
    total_upvotes: int
    total_comments: int
    example_posts: list
    validation_score: float
    category: str = ""


# Intent classification keywords (like GummySearch's AI tagging)
INTENT_KEYWORDS = {
    PostIntent.SOLUTION_REQUEST: [
        "looking for", "recommend", "anyone know", "tool for", "software for",
        "app for", "what do you use", "best tool", "need a tool", "suggest",
        "alternative to", "replacement for", "what's the best", "which tool",
        "any recommendations", "help me find"
    ],
    PostIntent.PAIN_POINT: [
        "frustrated", "hate", "annoying", "struggle", "waste of time",
        "inefficient", "broken", "sucks", "terrible", "awful", "nightmare",
        "drives me crazy", "fed up", "tired of", "sick of", "problem with",
        "doesn't work", "failing", "unreliable"
    ],
    PostIntent.ADVICE_REQUEST: [
        "how do you", "how to", "best way", "tips for", "advice on",
        "help with", "guide", "tutorial", "explain", "what's your process",
        "how does everyone", "workflow for"
    ],
    PostIntent.WILLINGNESS_TO_PAY: [
        "would pay", "pay for", "budget", "worth paying", "subscription",
        "pricing", "cost", "expensive", "cheap", "affordable", "investment",
        "roi", "return on", "value for money", "premium", "enterprise"
    ],
    PostIntent.IDEA: [
        "idea", "what if", "suggestion", "feature request", "wish there was",
        "would be cool", "imagine if", "dream tool", "wouldn't it be great"
    ],
    PostIntent.SELF_PROMOTION: [
        "i built", "i created", "just launched", "just released", "my app",
        "my tool", "feedback on", "check out my", "introducing", "announcing",
        "we built", "our new"
    ],
    PostIntent.MONEY_TALK: [
        "revenue", "mrr", "arr", "profit", "income", "earnings", "charge",
        "pricing model", "monetize", "make money", "business model"
    ],
}

# Payment signal keywords for validation scoring
PAYMENT_KEYWORDS = [
    "paid for", "pay for", "subscription", "subscribe", "monthly fee",
    "would pay", "willing to pay", "looking for paid", "budget",
    "paid tool", "paid service", "pricing", "cost", "expensive",
    "cheaper alternative", "paid version", "premium", "enterprise",
    "currently paying", "spent on", "investment in"
]

# Pain signal keywords for validation scoring
PAIN_KEYWORDS = [
    "frustrated", "hate", "annoying", "problem", "issue", "struggle",
    "difficult", "time-consuming", "manual", "inefficient", "slow",
    "broken", "doesn't work", "wish there was", "need", "looking for",
    "waste of time", "tedious", "painful", "nightmare", "headache"
]


def classify_intents(text: str) -> list[PostIntent]:
    """Classify post intent based on keywords (like GummySearch's AI tagging)."""
    text_lower = text.lower()
    detected = []
    
    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                detected.append(intent)
                break
    
    return detected if detected else [PostIntent.GENERAL]


def extract_signals(text: str) -> tuple[list[str], list[str]]:
    """Extract payment and pain signals from text."""
    text_lower = text.lower()
    
    payment_found = [kw for kw in PAYMENT_KEYWORDS if kw in text_lower]
    pain_found = [kw for kw in PAIN_KEYWORDS if kw in text_lower]
    
    return payment_found, pain_found


def calculate_validation_score(post: RedditPost) -> float:
    """Calculate SaaS validation score (0-10) based on multiple signals."""
    score = 0.0
    
    # Intent scoring
    if PostIntent.SOLUTION_REQUEST in post.intents:
        score += 3.0
    if PostIntent.PAIN_POINT in post.intents:
        score += 2.0
    if PostIntent.WILLINGNESS_TO_PAY in post.intents:
        score += 4.0
    if PostIntent.ADVICE_REQUEST in post.intents:
        score += 1.0
    
    # Engagement scoring (capped)
    score += min(post.upvotes / 50, 2.0)
    score += min(post.comments / 25, 2.0)
    
    # Signal scoring
    score += min(len(post.payment_signals) * 0.5, 2.0)
    score += min(len(post.pain_signals) * 0.3, 1.5)
    
    return min(round(score, 1), 10.0)


class RedditSaaSFinder:
    """
    Standalone Reddit SaaS idea discovery tool.
    Replicates GummySearch functionality with direct Reddit scraping.
    """
    
    # Pre-defined audience subreddit collections (like GummySearch curated audiences)
    CURATED_AUDIENCES = {
        "airbnb_hosts": {
            "name": "AirBnB Hosts",
            "subreddits": ["airbnb_hosts", "AirBnBHosts", "ShortTermRentals", "vrbo", "vacation_rentals"],
            "keywords": ["airbnb", "host", "guest", "property", "listing", "booking"]
        },
        "saas_founders": {
            "name": "SaaS Founders",
            "subreddits": ["SaaS", "startups", "Entrepreneur", "indiehackers", "microsaas"],
            "keywords": ["saas", "startup", "mrr", "churn", "pricing", "customers"]
        },
        "freelancers": {
            "name": "Freelancers & Consultants",
            "subreddits": ["freelance", "Upwork", "fiverr", "consulting", "digitalnomad"],
            "keywords": ["client", "rate", "project", "contract", "invoice"]
        },
        "ecommerce": {
            "name": "E-commerce Sellers",
            "subreddits": ["ecommerce", "FulfillmentByAmazon", "shopify", "dropship", "AmazonSeller"],
            "keywords": ["store", "product", "inventory", "shipping", "sales"]
        },
        "content_creators": {
            "name": "Content Creators",
            "subreddits": ["NewTubers", "youtubegaming", "Twitch", "podcasting", "content_creators"],
            "keywords": ["video", "content", "audience", "monetize", "sponsor"]
        },
        "real_estate": {
            "name": "Real Estate Investors",
            "subreddits": ["realestateinvesting", "RealEstate", "Landlord", "CommercialRealEstate"],
            "keywords": ["property", "tenant", "rent", "investment", "roi"]
        },
        "agencies": {
            "name": "Marketing Agencies",
            "subreddits": ["marketing", "digital_marketing", "SEO", "PPC", "socialmedia"],
            "keywords": ["client", "campaign", "report", "agency", "lead"]
        },
        "developers": {
            "name": "Software Developers",
            "subreddits": ["webdev", "programming", "cscareerquestions", "devops", "sysadmin"],
            "keywords": ["code", "deploy", "api", "tool", "workflow"]
        }
    }
    
    # Intent-based search queries (like GummySearch themes)
    INTENT_QUERIES = {
        "solution_request": [
            "looking for tool",
            "looking for software", 
            "anyone recommend",
            "best tool for",
            "what do you use for",
            "alternative to"
        ],
        "pain_point": [
            "frustrated with",
            "hate when",
            "struggle with",
            "waste of time",
            "problem with",
            "tired of"
        ],
        "advice_request": [
            "how do you",
            "best way to",
            "tips for",
            "advice on",
            "help with"
        ],
        "willingness_to_pay": [
            "would pay for",
            "worth paying",
            "budget for",
            "looking for paid",
            "subscription for"
        ]
    }
    
    def __init__(self, headless: bool = False):
        self.browser: Optional[Browser] = None
        self.headless = headless
        self.posts: list[RedditPost] = []
        self.patterns: list[SaaSPattern] = []
    
    async def start(self):
        """Start the browser instance."""
        self.browser = Browser(headless=self.headless)
        print("🌐 Browser started")
    
    async def stop(self):
        """Stop the browser instance."""
        if self.browser:
            await self.browser.close()
            print("🛑 Browser stopped")
    
    async def search_subreddit(
        self,
        subreddit: str,
        query: str,
        sort: str = "relevance",
        time_filter: str = "year",
        max_posts: int = 25
    ) -> list[RedditPost]:
        """Search a subreddit and extract posts with metadata."""
        if not self.browser:
            await self.start()
        
        context = await self.browser.new_context()
        page = await context.get_current_page()
        
        # Build search URL
        search_url = f"https://www.reddit.com/r/{subreddit}/search/?q={query}&sort={sort}&restrict_sr=1&t={time_filter}"
        
        print(f"🔍 Searching r/{subreddit} for: {query}")
        await page.goto(search_url, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        # Scroll to load more posts
        for _ in range(3):
            await page.keyboard.press("PageDown")
            await page.wait_for_timeout(1000)
        
        # Extract posts using JavaScript
        raw_posts = await page.evaluate(
            """
            (maxPosts) => {
                const results = [];
                
                // Try multiple selectors for different Reddit layouts
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
                    
                    // shreddit-post (new Reddit)
                    if (post.tagName === 'SHREDDIT-POST') {
                        title = post.getAttribute('post-title') || '';
                        author = post.getAttribute('author') || '';
                        upvotes = post.getAttribute('score') || '0';
                        comments = post.getAttribute('comment-count') || '0';
                        url = post.getAttribute('permalink') || '';
                    } else {
                        title = post.querySelector('h3, h2, [slot="title"], a.title')?.textContent?.trim() || '';
                        body = post.querySelector('[slot="text-body"], .md, .usertext-body')?.textContent?.trim() || '';
                        upvotes = post.querySelector('[data-testid="post-vote-score"], .score')?.textContent || '0';
                        const commentLink = post.querySelector('a[href*="comments"]');
                        comments = commentLink?.textContent?.match(/\\d+/)?.[0] || '0';
                        author = post.querySelector('a[href*="/user/"]')?.textContent || '';
                        const timeEl = post.querySelector('time, [datetime]');
                        timestamp = timeEl?.getAttribute('datetime') || timeEl?.textContent || '';
                    }
                    
                    if (title && title.length > 10) {
                        results.push({
                            title: title.substring(0, 300),
                            body: body.substring(0, 1000),
                            upvotes: parseInt(upvotes.replace(/[^0-9-]/g, '')) || 0,
                            comments: parseInt(comments.replace(/[^0-9]/g, '')) || 0,
                            author,
                            timestamp,
                            url
                        });
                    }
                });
                
                return results;
            }
            """,
            max_posts
        )
        
        await context.close()
        
        # Process posts
        posts = []
        for raw in raw_posts:
            full_text = raw["title"] + " " + raw.get("body", "")
            intents = classify_intents(full_text)
            payment_signals, pain_signals = extract_signals(full_text)
            
            post = RedditPost(
                title=raw["title"],
                body=raw.get("body", ""),
                subreddit=subreddit,
                author=raw.get("author", ""),
                upvotes=raw.get("upvotes", 0),
                comments=raw.get("comments", 0),
                url=raw.get("url", ""),
                timestamp=raw.get("timestamp", ""),
                intents=intents,
                payment_signals=payment_signals,
                pain_signals=pain_signals,
            )
            post.validation_score = calculate_validation_score(post)
            posts.append(post)
        
        print(f"   ✅ Found {len(posts)} posts")
        return posts
    
    async def search_by_intent(
        self,
        subreddit: str,
        intent: str = "solution_request",
        max_posts: int = 25
    ) -> list[RedditPost]:
        """Search subreddit using pre-built intent queries."""
        queries = self.INTENT_QUERIES.get(intent, self.INTENT_QUERIES["solution_request"])
        
        all_posts = []
        for query in queries[:3]:  # Use top 3 queries per intent
            posts = await self.search_subreddit(subreddit, query, max_posts=max_posts // 3)
            all_posts.extend(posts)
        
        # Dedupe by title
        seen = set()
        unique_posts = []
        for post in all_posts:
            if post.title not in seen:
                seen.add(post.title)
                unique_posts.append(post)
        
        return sorted(unique_posts, key=lambda p: p.validation_score, reverse=True)
    
    async def analyze_audience(
        self,
        audience_key: str,
        intents: list[str] = None,
        max_posts_per_sub: int = 20
    ) -> list[RedditPost]:
        """
        Analyze a curated audience (like GummySearch audiences).
        Searches all subreddits in the audience with intent-based queries.
        """
        if audience_key not in self.CURATED_AUDIENCES:
            print(f"❌ Unknown audience: {audience_key}")
            print(f"   Available: {list(self.CURATED_AUDIENCES.keys())}")
            return []
        
        audience = self.CURATED_AUDIENCES[audience_key]
        print(f"\n📊 Analyzing audience: {audience['name']}")
        print(f"   Subreddits: {', '.join(audience['subreddits'])}")
        
        intents = intents or ["solution_request", "pain_point", "willingness_to_pay"]
        
        all_posts = []
        for subreddit in audience["subreddits"]:
            for intent in intents:
                try:
                    posts = await self.search_by_intent(
                        subreddit, intent, max_posts=max_posts_per_sub // len(intents)
                    )
                    all_posts.extend(posts)
                except Exception as e:
                    print(f"   ⚠️ Error searching r/{subreddit}: {e}")
        
        # Dedupe and sort
        seen = set()
        unique_posts = []
        for post in all_posts:
            if post.title not in seen:
                seen.add(post.title)
                unique_posts.append(post)
        
        self.posts = sorted(unique_posts, key=lambda p: p.validation_score, reverse=True)
        print(f"\n✅ Total unique posts: {len(self.posts)}")
        return self.posts
    
    def find_patterns(self, min_posts: int = 2) -> list[SaaSPattern]:
        """
        Find common patterns in posts (like GummySearch Patterns).
        Groups similar posts and identifies common themes.
        """
        if not self.posts:
            print("⚠️ No posts to analyze. Run search first.")
            return []
        
        print("\n🔍 Finding patterns...")
        
        # Group by intent
        intent_groups = {}
        for post in self.posts:
            for intent in post.intents:
                if intent not in intent_groups:
                    intent_groups[intent] = []
                intent_groups[intent].append(post)
        
        patterns = []
        
        # Create patterns from intent groups
        for intent, posts in intent_groups.items():
            if len(posts) < min_posts or intent == PostIntent.GENERAL:
                continue
            
            # Calculate aggregates
            total_upvotes = sum(p.upvotes for p in posts)
            total_comments = sum(p.comments for p in posts)
            avg_score = sum(p.validation_score for p in posts) / len(posts)
            
            # Get top examples
            top_posts = sorted(posts, key=lambda p: p.validation_score, reverse=True)[:5]
            
            pattern = SaaSPattern(
                name=f"{intent.value.replace('_', ' ').title()}s",
                description=f"Posts expressing {intent.value.replace('_', ' ')}",
                post_count=len(posts),
                total_upvotes=total_upvotes,
                total_comments=total_comments,
                example_posts=[p.title for p in top_posts],
                validation_score=round(avg_score, 1),
                category=intent.value
            )
            patterns.append(pattern)
        
        # Sort by post count
        self.patterns = sorted(patterns, key=lambda p: p.post_count, reverse=True)
        
        print(f"   Found {len(self.patterns)} patterns")
        return self.patterns
    
    def get_theme_summary(self) -> dict:
        """Get summary of posts by theme (like GummySearch theme tabs)."""
        if not self.posts:
            return {}
        
        summary = {intent.value: 0 for intent in PostIntent}
        
        for post in self.posts:
            for intent in post.intents:
                summary[intent.value] += 1
        
        # Remove zero counts
        return {k: v for k, v in summary.items() if v > 0}
    
    def get_top_validated_ideas(self, min_score: float = 5.0, limit: int = 10) -> list[RedditPost]:
        """Get top validated SaaS ideas based on validation score."""
        return [p for p in self.posts if p.validation_score >= min_score][:limit]
    
    async def analyze_with_ai(self, audience_context: str = "") -> tuple:
        """
        Use AI to extract patterns and generate opportunities (like GummySearch).
        Returns (patterns, opportunities).
        """
        if not AI_AVAILABLE:
            print("⚠️ AI pattern extractor not available.")
            return [], []
        
        if not self.posts:
            print("⚠️ No posts to analyze. Run search first.")
            return [], []
        
        print("\n🤖 Running AI analysis...")
        extractor = AIPatternExtractor()
        
        # Extract patterns
        ai_patterns = await extractor.extract_patterns(
            self.posts,
            audience_context=audience_context
        )
        print(f"   Found {len(ai_patterns)} AI patterns")
        
        # Generate opportunities
        opportunities = await extractor.generate_opportunity_summary(
            self.posts,
            ai_patterns,
            audience_context=audience_context
        )
        print(f"   Generated {len(opportunities)} opportunity summaries")
        
        return ai_patterns, opportunities
    
    def generate_report(self, output_path: str = None, ai_patterns=None, ai_opportunities=None) -> str:
        """Generate a markdown report of findings."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# 🎯 Reddit SaaS Idea Discovery Report

**Generated:** {timestamp}
**Total Posts Analyzed:** {len(self.posts)}
**Patterns Found:** {len(self.patterns)}

---

## 📊 Theme Summary

| Theme | Post Count |
|-------|------------|
"""
        
        for theme, count in self.get_theme_summary().items():
            report += f"| {theme.replace('_', ' ').title()} | {count} |\n"
        
        report += """

---

## 🔥 Top Validated SaaS Opportunities

"""
        
        for i, post in enumerate(self.get_top_validated_ideas(min_score=4.0, limit=15), 1):
            intents_str = ", ".join([i.value for i in post.intents])
            payment_str = ", ".join(post.payment_signals[:3]) if post.payment_signals else "None"
            pain_str = ", ".join(post.pain_signals[:3]) if post.pain_signals else "None"
            
            report += f"""### {i}. {post.title[:80]}{'...' if len(post.title) > 80 else ''}

- **Validation Score:** {post.validation_score}/10
- **Subreddit:** r/{post.subreddit}
- **Engagement:** ↑{post.upvotes} | 💬{post.comments}
- **Intents:** {intents_str}
- **Payment Signals:** {payment_str}
- **Pain Signals:** {pain_str}
- **URL:** https://reddit.com{post.url}

"""
        
        report += """
---

## 🎯 Identified Patterns

"""
        
        for pattern in self.patterns:
            report += f"""### {pattern.name} ({pattern.post_count} posts)

- **Total Engagement:** ↑{pattern.total_upvotes} | 💬{pattern.total_comments}
- **Avg Validation Score:** {pattern.validation_score}/10

**Example Posts:**
"""
            for example in pattern.example_posts[:3]:
                report += f"- {example[:100]}{'...' if len(example) > 100 else ''}\n"
            
            report += "\n"
        
        # Add AI-generated sections if available
        if ai_patterns:
            report += """
---

## 🤖 AI-Identified Patterns

"""
            for p in ai_patterns[:5]:
                report += f"""### {p.name} (Score: {p.opportunity_score}/10)

**{p.description}**

- **Problem:** {p.problem_statement}
- **Target:** {p.target_audience}
- **Posts:** {p.post_count}

**Validation Signals:**
"""
                for signal in p.validation_signals[:3]:
                    report += f"- {signal}\n"
                
                report += "\n**Recommended Features:**\n"
                for feature in p.recommended_features[:3]:
                    report += f"- {feature}\n"
                
                report += f"\n**Monetization:** {p.monetization_potential}\n\n"
        
        if ai_opportunities:
            report += """
---

## 🚀 AI-Generated SaaS Opportunities

"""
            for i, opp in enumerate(ai_opportunities[:5], 1):
                report += f"""### {i}. {opp.name}

**{opp.tagline}**

| Aspect | Details |
|--------|---------|
| Problem | {opp.problem} |
| Solution | {opp.solution} |
| Target Market | {opp.target_market} |
| Validation Score | {opp.validation_score}/10 |
| Pricing | {opp.pricing_suggestion} |

**MVP Features:**
"""
                for feature in opp.mvp_features:
                    report += f"- {feature}\n"
                
                report += f"\n**Competition:** {opp.competition_analysis}\n\n"
        
        report += """
---

## 💡 Recommended Next Steps

1. **Deep Dive:** Click through to high-scoring posts to read full discussions
2. **Competition Check:** Search Google for "[problem] software" to assess competition
3. **Validate Further:** Look for posts with explicit willingness-to-pay signals
4. **Cross-Reference:** Check if same problems appear in multiple subreddits
5. **Build MVP:** Focus on problems with score 7+ and payment signals

---

*Generated by Reddit SaaS Finder with AI Analysis*
"""
        
        if output_path:
            Path(output_path).write_text(report, encoding="utf-8")
            print(f"\n📄 Report saved to: {output_path}")
        
        return report


async def main():
    """Example usage of Reddit SaaS Finder."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reddit SaaS Idea Finder")
    parser.add_argument("--audience", type=str, help="Curated audience key (e.g., airbnb_hosts)")
    parser.add_argument("--subreddits", type=str, help="Comma-separated subreddits")
    parser.add_argument("--themes", type=str, default="solution_request,pain_point", 
                        help="Comma-separated intents to search")
    parser.add_argument("--max-posts", type=int, default=20, help="Max posts per subreddit")
    parser.add_argument("--output", type=str, help="Output report path")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--list-audiences", action="store_true", help="List available audiences")
    parser.add_argument("--ai-analysis", action="store_true", help="Run AI pattern extraction")
    
    args = parser.parse_args()
    
    finder = RedditSaaSFinder(headless=args.headless)
    
    if args.list_audiences:
        print("\n📚 Available Curated Audiences:\n")
        for key, audience in finder.CURATED_AUDIENCES.items():
            print(f"  {key}:")
            print(f"    Name: {audience['name']}")
            print(f"    Subreddits: {', '.join(audience['subreddits'])}")
            print()
        return
    
    try:
        await finder.start()
        
        if args.audience:
            # Analyze curated audience
            intents = args.themes.split(",") if args.themes else None
            await finder.analyze_audience(args.audience, intents, args.max_posts)
        
        elif args.subreddits:
            # Search specific subreddits
            subreddits = [s.strip() for s in args.subreddits.split(",")]
            intents = args.themes.split(",") if args.themes else ["solution_request"]
            
            for subreddit in subreddits:
                for intent in intents:
                    posts = await finder.search_by_intent(subreddit, intent, args.max_posts)
                    finder.posts.extend(posts)
            
            # Dedupe
            seen = set()
            finder.posts = [p for p in finder.posts if not (p.title in seen or seen.add(p.title))]
            finder.posts.sort(key=lambda p: p.validation_score, reverse=True)
        
        else:
            # Default: analyze SaaS founders audience
            print("No audience or subreddits specified. Using default: saas_founders")
            await finder.analyze_audience("saas_founders", max_posts_per_sub=15)
        
        # Find patterns (keyword-based)
        finder.find_patterns()
        
        # AI analysis (optional)
        ai_patterns = None
        ai_opportunities = None
        audience_context = ""
        
        if args.ai_analysis and AI_AVAILABLE:
            if args.audience and args.audience in finder.CURATED_AUDIENCES:
                audience_context = finder.CURATED_AUDIENCES[args.audience]["name"]
            ai_patterns, ai_opportunities = await finder.analyze_with_ai(audience_context)
        
        # Generate report
        output_path = args.output or f"results/reddit_saas_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        Path("results").mkdir(exist_ok=True)
        report = finder.generate_report(output_path, ai_patterns, ai_opportunities)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        print(f"Total posts: {len(finder.posts)}")
        print(f"Patterns found: {len(finder.patterns)}")
        print(f"\nTheme breakdown:")
        for theme, count in finder.get_theme_summary().items():
            print(f"  - {theme.replace('_', ' ').title()}: {count}")
        
        print(f"\n🔥 Top 5 Validated Ideas:")
        for i, post in enumerate(finder.get_top_validated_ideas(limit=5), 1):
            print(f"  {i}. [{post.validation_score}/10] {post.title[:60]}...")
        
        print(f"\n📄 Full report: {output_path}")
        
    finally:
        await finder.stop()


if __name__ == "__main__":
    asyncio.run(main())

