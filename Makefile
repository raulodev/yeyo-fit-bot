server:
	uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1 --reload

tunnel:
	cloudflared tunnel --url http://localhost:8000

