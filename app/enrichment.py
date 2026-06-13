import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"  # Free, fast, good at classification

# Legal categories for NyayaSetu
LEGAL_CATEGORIES = [
    "Tenant Rights", "Property Law", "Family Law", "Consumer Rights",
    "Criminal Law", "Employment", "Women Safety", "RTI", "Civil Litigation",
    "Corporate Law", "Tax Law", "Constitutional Rights", "General"
]

CLASSIFICATION_PROMPT = """You are a legal content classifier for an Indian legal platform.
Analyze the post below and return ONLY a JSON object. No preamble, no explanation.

Post: "{content}"

Return this exact JSON structure:
{{
    "primary_topic": "one of the legal categories",
    "secondary_topics": ["topic1", "topic2"],
    "legal_acts": ["any Indian laws or acts referenced, empty array if none"],
    "urgency": "low or medium or high or critical",
    "target_audience": ["tenant", "employee", "consumer", "general", etc],
    "enriched_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "is_professional_advice": true or false
}}

Legal categories to choose from: {categories}
"""


class EnrichmentService:

    async def classify_post(self, content: str) -> dict:
        """
        Use Groq (free LLM API) to auto-detect legal category and tags.
        Falls back to keyword matching if API fails.
        """
        if GROQ_API_KEY:
            try:
                result = await self._classify_with_groq(content)
                if result:
                    return result
            except Exception as e:
                print(f"Groq classification failed: {e}. Using fallback.")

        # Fallback — keyword based classification (works offline, no API needed)
        return self._classify_with_keywords(content)

    async def _classify_with_groq(self, content: str) -> dict | None:
        """Call Groq free API for LLM classification."""
        prompt = CLASSIFICATION_PROMPT.format(
            content=content[:500],  # Limit to 500 chars to save tokens
            categories=", ".join(LEGAL_CATEGORIES)
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.1  # Low temperature for consistent classification
                }
            )

            if response.status_code != 200:
                return None

            data = response.json()
            raw_text = data["choices"][0]["message"]["content"].strip()

            # Clean up response and parse JSON
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            return json.loads(raw_text)

    def _classify_with_keywords(self, content: str) -> dict:
        """
        Fallback keyword classifier — works offline, no API needed.
        Not as smart as LLM but good enough for basic categorization.
        """
        content_lower = content.lower()

        # Keyword to category mapping
        keyword_map = {
            "Tenant Rights": ["rent", "landlord", "tenant", "deposit", "eviction", "lease", "flat", "house rent"],
            "Consumer Rights": ["consumer", "refund", "product", "defective", "complaint", "amazon", "flipkart", "service"],
            "Family Law": ["divorce", "marriage", "custody", "maintenance", "alimony", "child", "spouse"],
            "Property Law": ["property", "land", "registration", "deed", "ownership", "encroachment", "builder"],
            "Criminal Law": ["fir", "police", "arrest", "bail", "crime", "accused", "court", "judge"],
            "Employment": ["salary", "job", "employer", "termination", "pf", "esi", "gratuity", "labour"],
            "Women Safety": ["harassment", "dowry", "domestic violence", "assault", "women", "molestation"],
            "RTI": ["rti", "right to information", "government", "public authority", "transparency"],
            "Constitutional Rights": ["fundamental rights", "article 21", "article 19", "constitution", "high court", "supreme court"],
        }

        scores = {}
        for category, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                scores[category] = score

        primary = max(scores, key=scores.get) if scores else "General"

        # Generate simple tags
        words = [w for w in content_lower.split() if len(w) > 4]
        tags = list(set(words[:5]))

        return {
            "primary_topic": primary,
            "secondary_topics": [k for k in sorted(scores, key=scores.get, reverse=True)[1:3]],
            "legal_acts": [],
            "urgency": "medium",
            "target_audience": ["general"],
            "enriched_tags": tags,
            "is_professional_advice": False
        }
