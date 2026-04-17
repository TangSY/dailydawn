from .base import BaseFetcher, Signal
from .hackernews import HackerNewsFetcher
from .github_trending import GitHubTrendingFetcher
from .product_hunt import ProductHuntFetcher
from .reddit import RedditFetcher
from .huggingface import HuggingFaceFetcher
from .v2ex import V2EXFetcher
from .juejin import JuejinFetcher
from .google_trends import GoogleTrendsFetcher

ALL_FETCHERS = [
    HackerNewsFetcher,
    GitHubTrendingFetcher,
    ProductHuntFetcher,
    RedditFetcher,
    HuggingFaceFetcher,
    V2EXFetcher,
    JuejinFetcher,
    GoogleTrendsFetcher,
]
