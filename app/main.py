from fastapi import FastAPI
from fastapi.responses import HTMLResponse


app = FastAPI(
    title="AutoDocX",
    description="Automatic software documentation generator",
    version="0.1.0",
)


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>AutoDocX</title>

        <style>
            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #f3f5f8;
                color: #1f2937;
                font-family: Arial, sans-serif;
            }

            .card {
                width: min(700px, 90%);
                padding: 40px;
                background: white;
                border-radius: 16px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
            }

            h1 {
                margin-top: 0;
                margin-bottom: 12px;
            }

            .success {
                color: #16803c;
                font-weight: bold;
            }

            .description {
                color: #596473;
                line-height: 1.6;
            }
        </style>
    </head>

    <body>
        <main class="card">
            <h1>AutoDocX</h1>

            <p class="success">
                AutoDocX is running successfully.
            </p>

            <p class="description">
                The basic FastAPI development application is working.
            </p>
        </main>
    </body>
    </html>
    """


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "application": "AutoDocX",
        "version": "0.1.0",
    }