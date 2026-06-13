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
