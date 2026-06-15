import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
LEXFEED_ENV = os.getenv("LEXFEED_ENV", "development")

# Embedding model — runs locally, no API needed
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

# Feed settings
MAX_CANDIDATES = 200
FEED_SIZE = 20
MAX_POSTS_PER_TOPIC = 3
RECENCY_DECAY_HOURS = 48

# Hide posts a user already saw in the last N hours. Good for high-traffic
# platforms, but on a small/new platform it empties the feed — so default OFF.
# Set SEEN_FILTER_HOURS=24 once there's enough post volume.
SEEN_FILTER_HOURS = int(os.getenv("SEEN_FILTER_HOURS", "0"))

# Legal categories for classification
LEGAL_CATEGORIES = [
    "Property Law",
    "Family Law",
    "Consumer Rights",
    "Criminal Law",
    "Employment",
    "Tenant Rights",
    "Women Safety",
    "RTI",
    "Civil Litigation",
    "Tax Law",
    "Corporate Law",
    "General Legal",
]

# Post types
POST_TYPES = ["Short Update", "Article", "Legal News", "Help Request"]

# Urgency levels
URGENCY_LEVELS = ["low", "medium", "high", "critical"]
