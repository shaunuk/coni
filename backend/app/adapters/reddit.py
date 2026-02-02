import math
import re

import httpx

from app.adapters.base import BaseAdapter
from app.schemas.source import Claim, SourceResponse


# Subreddits known for quality educational/scientific content
RELEVANT_SUBREDDITS = [
    "askscience",
    "explainlikeimfive",
    "eli5",
    "science",
    "physics",
    "chemistry",
    "biology",
    "astronomy",
    "space",
    "askhistorians",
    "history",
    "philosophy",
    "math",
    "learnprogramming",
    "programming",
    "technology",
    "futurology",
    "todayilearned",
    "nostupidquestions",
    "answers",
    "askreddit",
]

# Minimum score threshold for quality filtering
MIN_SCORE_THRESHOLD = 10


class RedditAdapter(BaseAdapter):
    def __init__(self):
        self.base_url = "https://www.reddit.com/search.json"

    @property
    def source_name(self) -> str:
        return "Reddit"

    def _extract_keywords(self, question: str) -> set[str]:
        """Extract meaningful keywords from the question."""
        # Remove common stop words and short words
        stop_words = {
            "what", "is", "a", "an", "the", "how", "why", "when", "where", "who",
            "which", "are", "was", "were", "be", "been", "being", "have", "has",
            "had", "do", "does", "did", "will", "would", "could", "should", "may",
            "might", "must", "can", "to", "of", "in", "for", "on", "with", "at",
            "by", "from", "as", "into", "through", "during", "before", "after",
            "above", "below", "between", "under", "again", "further", "then",
            "once", "here", "there", "all", "each", "few", "more", "most", "other",
            "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than",
            "too", "very", "just", "about", "also", "and", "but", "or", "if", "it",
            "its", "this", "that", "these", "those", "i", "me", "my", "myself",
            "we", "our", "you", "your", "he", "him", "his", "she", "her", "they",
            "them", "their",
        }
        # Extract words, lowercase, filter out stop words and short words
        words = re.findall(r'\b[a-zA-Z]+\b', question.lower())
        return {w for w in words if w not in stop_words and len(w) > 2}

    def _calculate_relevance_score(
        self, title: str, selftext: str, keywords: set[str], reddit_score: int
    ) -> float:
        """
        Calculate a relevance score based on keyword matches and Reddit score.
        Returns a score between 0 and 1.
        """
        if not keywords:
            return 0.0

        # Combine title and selftext for matching
        content = f"{title} {selftext}".lower()

        # Count keyword matches
        matches = sum(1 for kw in keywords if kw in content)
        keyword_ratio = matches / len(keywords) if keywords else 0

        # Normalize Reddit score (logarithmic scale to handle high scores)
        score_factor = min(math.log10(max(reddit_score, 1) + 1) / 4, 1.0)

        # Weight: 60% keyword relevance, 40% Reddit score
        return (keyword_ratio * 0.6) + (score_factor * 0.4)

    def _is_relevant_subreddit(self, subreddit: str) -> bool:
        """Check if the subreddit is in our list of relevant subreddits."""
        return subreddit.lower() in RELEVANT_SUBREDDITS

    async def _call_api(self, question: str) -> dict:
        async with httpx.AsyncClient() as client:
            # Build a subreddit-restricted search query
            subreddit_filter = " OR ".join(
                f"subreddit:{sr}" for sr in RELEVANT_SUBREDDITS[:10]
            )
            query = f"({question}) ({subreddit_filter})"

            response = await client.get(
                self.base_url,
                params={"q": query, "sort": "relevance", "limit": 25},
                headers={"User-Agent": "ConsensusEngine/0.1"},
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()

    async def query(self, question: str) -> SourceResponse | None:
        try:
            data = await self._call_api(question)
            posts = data.get("data", {}).get("children", [])
            keywords = self._extract_keywords(question)

            # Score and filter posts
            scored_posts = []
            for post in posts:
                p = post["data"]
                title = p.get("title", "")
                selftext = p.get("selftext", "")
                reddit_score = p.get("score", 0)
                subreddit = p.get("subreddit", "")

                # Skip posts below minimum score threshold
                if reddit_score < MIN_SCORE_THRESHOLD:
                    continue

                # Prioritize posts from relevant subreddits
                is_relevant_sub = self._is_relevant_subreddit(subreddit)

                # Calculate relevance score
                relevance = self._calculate_relevance_score(
                    title, selftext, keywords, reddit_score
                )

                # Require at least some keyword match
                content = f"{title} {selftext}".lower()
                has_keyword_match = any(kw in content for kw in keywords)

                if not has_keyword_match:
                    continue

                # Boost score for relevant subreddits
                if is_relevant_sub:
                    relevance *= 1.5

                scored_posts.append({
                    "data": p,
                    "relevance": relevance,
                    "is_relevant_sub": is_relevant_sub,
                })

            # Sort by relevance score and take the best one
            scored_posts.sort(key=lambda x: x["relevance"], reverse=True)

            if not scored_posts:
                return SourceResponse(
                    source_name="reddit",
                    raw_response="No relevant results found",
                    claims=[],
                    confidence=0.0,
                    source_url=f"https://www.reddit.com/search?q={question.replace(' ', '+')}",
                )

            # Return only the most relevant result
            best_post = scored_posts[0]["data"]
            title = best_post.get("title", "")
            selftext = best_post.get("selftext", "")
            text = selftext if selftext.strip() else title
            reddit_score = best_post.get("score", 0)
            permalink = best_post.get("permalink", "")
            subreddit = best_post.get("subreddit", "")

            # Confidence based on relevance score and Reddit score
            confidence = min(scored_posts[0]["relevance"], 1.0)

            claim = Claim(
                text=text[:500],
                confidence=confidence,
                evidence=f"https://reddit.com{permalink}" if permalink else None,
            )

            raw_response = (
                f"[r/{subreddit}] [score:{reddit_score}] {title}\n{selftext[:500]}"
            )

            return SourceResponse(
                source_name="reddit",
                raw_response=raw_response,
                claims=[claim],
                confidence=confidence,
                source_url=f"https://reddit.com{permalink}" if permalink else None,
            )
        except Exception:
            return None
