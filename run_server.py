import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("⚡ Starting Resume Screener SaaS Production Server...")
    print("👉 Web Dashboard:  http://localhost:8000")
    print("👉 Swagger API:    http://localhost:8000/docs")
    print("👉 Health Status:  http://localhost:8000/api/v1/health")
    print("=" * 60)
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=False)
