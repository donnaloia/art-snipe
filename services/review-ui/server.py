from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os

os.chdir(Path('/app'))
print('Review UI placeholder running at http://localhost:3000')
print('Generated assets are mounted at /app/workspace/generated')
ThreadingHTTPServer(('0.0.0.0', 3000), SimpleHTTPRequestHandler).serve_forever()
