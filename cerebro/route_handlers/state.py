# Shared state initialized by server.py during startup
cache = None          # _Cache instance
metrics = None        # _metrics dict
metrics_lock = None   # threading.Lock for metrics
demo_counters = None  # _demo_counters dict
sse_clients = None    # list of (client_id, queue)
sse_lock = None       # threading.Lock for SSE
