"""FastAPI 主入口"""

from fastapi import FastAPI
from rich.console import Console

app = FastAPI(title="Oh My Coder", version="0.1.0")
console = Console()


@app.get("/")
async def root():
    return {"message": "Oh My Coder API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    console.print("[bold green]Oh My Coder[/bold green] 启动中...")
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
