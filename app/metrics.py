from prometheus_client import Counter

REQUEST_COUNT = Counter(
    "request_count",
    "Total API requests"
)
