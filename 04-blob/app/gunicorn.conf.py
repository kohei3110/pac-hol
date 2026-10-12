import os

port = int(os.environ.get("PORT", "8080"))
if not 1 <= port <= 65535:
    raise ValueError("PORT must be in the range 1-65535.")

bind = f"0.0.0.0:{port}"
workers = 1
worker_class = "gthread"
threads = 4
timeout = 45
graceful_timeout = 20
accesslog = None
errorlog = "-"
loglevel = "warning"
control_socket_disable = True
forwarded_allow_ips = "*"
secure_scheme_headers = {"X-FORWARDED-PROTO": "https"}
