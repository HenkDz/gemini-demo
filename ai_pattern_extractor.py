"""
AI-Powered Pattern Extraction for SaaS Idea Discovery

This module uses Gemini AI to analyze Reddit posts and extract patterns
like GummySearch's "Patterns" feature.

Features:
1. Groups similar posts by semantic meaning (not just keywords)
2. Identifies common pain points and needs
3. Extracts product/tool mentions
4. Generates actionable SaaS opportunity summaries
5. Scores opportunities based on validation signals

Usage:
    from ai_pattern_extractor import AIPatternExtractor
    
    extractor = AIPatternExtractor()
    patterns = await extractor.extract_patterns(posts)
    summary = await extractor.generate_opportunity_summary(patterns)
"""

import json
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Try to import Google AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ google-generativeai not installed. AI features disabled.")


@dataclass
class AIPattern:
    """AI-identified pattern of common needs."""
    name: str
    description: str
    problem_statement: str
    target_audience: str
    post_count: int
    validation_signals: list
    example_quotes: list
    competition_notes: str
    opportunity_score: float  # 0-10
    recommended_features: list
    monetization_potential: str


@dataclass
class SaaSOpportunity:
    """Structured SaaS opportunity extracted by AI."""
    name: str
    tagline: str
    problem: str
    solution: str
    target_market: str
    market_size_indicator: str
    validation_score: float
    pain_evidence: list
    payment_evidence: list
    competition_analysis: str
    mvp_features: list
    pricing_suggestion: str


class AIPatternExtractor:
    """
    Uses Gemini AI to extract patterns and opportunities from Reddit posts.
    Replicates GummySearch's AI-powered pattern detection.
    """
    
    def __init__(self, model_name: str = "gemini-3-flash-preview"):
        self.model_name = model_name
        self.model = None
        
        if GEMINI_AVAILABLE:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(model_name)
            else:
                print("⚠️ No GOOGLE_API_KEY or GEMINI_API_KEY found. AI features disabled.")
    
    def _prepare_posts_for_analysis(self, posts: list, max_posts: int = 100) -> str:
        """Format posts for AI analysis."""
        formatted = []
        
        for i, post in enumerate(posts[:max_posts]):
            # Handle both dict and dataclass posts
            if hasattr(post, 'title'):
                title = post.title
                body = getattr(post, 'body', '')
                upvotes = getattr(post, 'upvotes', 0)
                comments = getattr(post, 'comments', 0)
                subreddit = getattr(post, 'subreddit', '')
                intents = getattr(post, 'intents', [])
                if hasattr(intents[0] if intents else None, 'value'):
                    intents = [i.value for i in intents]
            else:
                title = post.get('title', '')
                body = post.get('body', '')
                upvotes = post.get('upvotes', 0)
                comments = post.get('comments', 0)
                subreddit = post.get('subreddit', '')
                intents = post.get('intents', [])
            
            formatted.append(f"""
POST {i+1}:
Title: {title}
Body: {body[:500] if body else 'N/A'}
Subreddit: r/{subreddit}
Engagement: ↑{upvotes} comments:{comments}
Detected Intents: {', '.join(intents) if intents else 'general'}
---""")
        
        return "\n".join(formatted)
    
    async def extract_patterns(
        self,
        posts: list,
        audience_context: str = "",
        max_patterns: int = 10
    ) -> list[AIPattern]:
        """
        Extract common patterns from posts using AI.
        Like GummySearch's "Find Patterns" feature.
        """
        if not self.model:
            print("⚠️ AI model not available. Using fallback pattern extraction.")
            return self._fallback_pattern_extraction(posts)
        
        posts_text = self._prepare_posts_for_analysis(posts)
        
        prompt = f"""You are an expert at identifying SaaS product opportunities from online discussions.

CONTEXT: {audience_context if audience_context else 'General SaaS audience research'}

Analyze these Reddit posts and identify the TOP {max_patterns} PATTERNS of common needs, problems, or requests that could be solved with software.

POSTS TO ANALYZE:
{posts_text}

For each pattern, provide:
1. A clear, specific pattern name (e.g., "Seeking Property Management Software" not just "Software Requests")
2. A detailed description of what people are asking for
3. A clear problem statement
4. The target audience
5. Specific validation signals found (quotes showing pain or willingness to pay)
6. 2-3 example quotes from the posts
7. Competition notes (existing solutions mentioned, gaps identified)
8. Opportunity score (0-10) based on frequency, pain level, and payment signals
9. Recommended MVP features
10. Monetization potential (subscription tiers, pricing thoughts)

Respond in this exact JSON format:
{{
    "patterns": [
        {{
            "name": "Pattern Name",
            "description": "What people are looking for",
            "problem_statement": "Clear problem being solved",
            "target_audience": "Who has this problem",
            "post_count": 5,
            "validation_signals": ["signal 1", "signal 2"],
            "example_quotes": ["quote 1", "quote 2"],
            "competition_notes": "Existing solutions and gaps",
            "opportunity_score": 7.5,
            "recommended_features": ["feature 1", "feature 2"],
            "monetization_potential": "Pricing thoughts"
        }}
    ]
}}

Focus on actionable SaaS opportunities. Prioritize patterns where people explicitly mention:
- Looking for tools/software
- Frustration with current solutions
- Willingness to pay
- Specific feature requests

Return ONLY valid JSON, no other text."""

        try:
            response = await self.model.generate_content_async(prompt)
            result_text = response.text.strip()
            
            # Clean up response (remove markdown code blocks if present)
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            
            patterns = []
            for p in result.get("patterns", []):
                patterns.append(AIPattern(
                    name=p.get("name", "Unknown Pattern"),
                    description=p.get("description", ""),
                    problem_statement=p.get("problem_statement", ""),
                    target_audience=p.get("target_audience", ""),
                    post_count=p.get("post_count", 0),
                    validation_signals=p.get("validation_signals", []),
                    example_quotes=p.get("example_quotes", []),
                    competition_notes=p.get("competition_notes", ""),
                    opportunity_score=p.get("opportunity_score", 0.0),
                    recommended_features=p.get("recommended_features", []),
                    monetization_potential=p.get("monetization_potential", "")
                ))
            
            return sorted(patterns, key=lambda p: p.opportunity_score, reverse=True)
            
        except Exception as e:
            print(f"⚠️ AI pattern extraction failed: {e}")
            return self._fallback_pattern_extraction(posts)
    
    async def generate_opportunity_summary(
        self,
        posts: list,
        patterns: list[AIPattern] = None,
        audience_context: str = ""
    ) -> list[SaaSOpportunity]:
        """
        Generate structured SaaS opportunity summaries from posts and patterns.
        """
        if not self.model:
            print("⚠️ AI model not available.")
            return []
        
        posts_text = self._prepare_posts_for_analysis(posts, max_posts=50)
        
        patterns_text = ""
        if patterns:
            patterns_text = "\n\nIDENTIFIED PATTERNS:\n"
            for p in patterns[:5]:
                patterns_text += f"- {p.name}: {p.description} (Score: {p.opportunity_score})\n"
        
        prompt = f"""You are a SaaS product strategist. Based on this research data, identify the TOP 5 most promising SaaS product opportunities.

CONTEXT: {audience_context if audience_context else 'General audience'}

RESEARCH DATA:
{posts_text}
{patterns_text}

For each opportunity, provide a complete product concept:

{{
    "opportunities": [
        {{
            "name": "Product Name",
            "tagline": "One-line value proposition",
            "problem": "The specific problem being solved",
            "solution": "How the product solves it",
            "target_market": "Who buys this",
            "market_size_indicator": "Evidence of market size from the data",
            "validation_score": 8.5,
            "pain_evidence": ["Quote 1 showing pain", "Quote 2"],
            "payment_evidence": ["Quote showing willingness to pay"],
            "competition_analysis": "Existing solutions and how to differentiate",
            "mvp_features": ["Feature 1", "Feature 2", "Feature 3"],
            "pricing_suggestion": "$X/month for Y tier"
        }}
    ]
}}

Prioritize opportunities with:
1. Clear, specific pain points (not vague)
2. Evidence of willingness to pay
3. Identifiable target market
4. Gap in existing solutions
5. Feasible as a micro-SaaS or indie product

Return ONLY valid JSON."""

        try:
            response = await self.model.generate_content_async(prompt)
            result_text = response.text.strip()
            
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            
            opportunities = []
            for o in result.get("opportunities", []):
                opportunities.append(SaaSOpportunity(
                    name=o.get("name", ""),
                    tagline=o.get("tagline", ""),
                    problem=o.get("problem", ""),
                    solution=o.get("solution", ""),
                    target_market=o.get("target_market", ""),
                    market_size_indicator=o.get("market_size_indicator", ""),
                    validation_score=o.get("validation_score", 0.0),
                    pain_evidence=o.get("pain_evidence", []),
                    payment_evidence=o.get("payment_evidence", []),
                    competition_analysis=o.get("competition_analysis", ""),
                    mvp_features=o.get("mvp_features", []),
                    pricing_suggestion=o.get("pricing_suggestion", "")
                ))
            
            return sorted(opportunities, key=lambda o: o.validation_score, reverse=True)
            
        except Exception as e:
            print(f"⚠️ Opportunity generation failed: {e}")
            return []
    
    async def analyze_competition(self, product_idea: str, posts: list) -> str:
        """Analyze competition for a specific product idea."""
        if not self.model:
            return "AI analysis not available."
        
        posts_text = self._prepare_posts_for_analysis(posts, max_posts=30)
        
        prompt = f"""Analyze the competitive landscape for this product idea based on Reddit discussions:

PRODUCT IDEA: {product_idea}

RELEVANT DISCUSSIONS:
{posts_text}

Provide:
1. Existing solutions mentioned in discussions
2. Common complaints about existing solutions
3. Feature gaps people are asking for
4. Price points mentioned
5. Differentiation opportunities
6. Barriers to entry
7. Overall competition assessment (Low/Medium/High)

Be specific and cite evidence from the posts."""

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            return f"Analysis failed: {e}"
    
    def _fallback_pattern_extraction(self, posts: list) -> list[AIPattern]:
        """Fallback pattern extraction without AI (keyword-based)."""
        # Group by detected intents
        intent_groups = {}
        
        for post in posts:
            intents = getattr(post, 'intents', []) or post.get('intents', [])
            for intent in intents:
                intent_key = intent.value if hasattr(intent, 'value') else str(intent)
                if intent_key not in intent_groups:
                    intent_groups[intent_key] = []
                intent_groups[intent_key].append(post)
        
        patterns = []
        for intent, group_posts in intent_groups.items():
            if len(group_posts) < 2 or intent == 'general':
                continue
            
            titles = []
            for p in group_posts[:5]:
                title = getattr(p, 'title', None) or p.get('title', '')
                if title:
                    titles.append(title[:100])
            
            patterns.append(AIPattern(
                name=f"{intent.replace('_', ' ').title()}",
                description=f"Posts related to {intent.replace('_', ' ')}",
                problem_statement="",
                target_audience="",
                post_count=len(group_posts),
                validation_signals=[],
                example_quotes=titles,
                competition_notes="",
                opportunity_score=len(group_posts) / 2,
                recommended_features=[],
                monetization_potential=""
            ))
        
        return sorted(patterns, key=lambda p: p.post_count, reverse=True)


def format_opportunities_report(opportunities: list[SaaSOpportunity]) -> str:
    """Format opportunities as a markdown report."""
    report = "# 🚀 AI-Identified SaaS Opportunities\n\n"
    
    for i, opp in enumerate(opportunities, 1):
        report += f"""## {i}. {opp.name}

**{opp.tagline}**

### Problem
{opp.problem}

### Solution
{opp.solution}

### Target Market
{opp.target_market}

### Validation Score: {opp.validation_score}/10

**Market Size Indicator:** {opp.market_size_indicator}

### Evidence

**Pain Points:**
"""
        for pain in opp.pain_evidence:
            report += f"- \"{pain}\"\n"
        
        report += "\n**Payment Signals:**\n"
        for payment in opp.payment_evidence:
            report += f"- \"{payment}\"\n"
        
        report += f"""
### Competition Analysis
{opp.competition_analysis}

### MVP Features
"""
        for feature in opp.mvp_features:
            report += f"- {feature}\n"
        
        report += f"""
### Pricing Suggestion
{opp.pricing_suggestion}

---

"""
    
    return report


# Example usage
async def demo():
    """Demonstrate AI pattern extraction."""
    # Example posts (normally from RedditSaaSFinder)
    example_posts = [
        {
            "title": "Looking for a tool to manage multiple Airbnb listings",
            "body": "I have 5 properties and juggling between apps is killing me. Would pay for something that consolidates everything.",
            "subreddit": "airbnb_hosts",
            "upvotes": 45,
            "comments": 32,
            "intents": ["solution_request", "willingness_to_pay"]
        },
        {
            "title": "Frustrated with PriceLabs - need alternative",
            "body": "Their support is terrible and the UI is confusing. Looking for simpler dynamic pricing tool.",
            "subreddit": "ShortTermRentals",
            "upvotes": 23,
            "comments": 18,
            "intents": ["pain_point", "solution_request"]
        },
        {
            "title": "How do you handle guest communication at scale?",
            "body": "Managing messages across Airbnb, VRBO, and direct bookings is overwhelming. Any tips?",
            "subreddit": "airbnb_hosts",
            "upvotes": 67,
            "comments": 45,
            "intents": ["advice_request", "pain_point"]
        }
    ]
    
    extractor = AIPatternExtractor()
    
    if extractor.model:
        print("🔍 Extracting patterns with AI...")
        patterns = await extractor.extract_patterns(
            example_posts,
            audience_context="Short-term rental hosts (Airbnb, VRBO)"
        )
        
        print(f"\n📊 Found {len(patterns)} patterns:\n")
        for p in patterns:
            print(f"  {p.name} (Score: {p.opportunity_score})")
            print(f"    {p.description}")
            print()
        
        print("🚀 Generating opportunity summaries...")
        opportunities = await extractor.generate_opportunity_summary(
            example_posts,
            patterns,
            audience_context="Short-term rental hosts"
        )
        
        report = format_opportunities_report(opportunities)
        print(report)
    else:
        print("⚠️ AI model not available. Set GOOGLE_API_KEY or GEMINI_API_KEY.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())

