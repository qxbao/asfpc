import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from packages.database.database import Database
from routers import account

load_dotenv()

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("Main")

@asynccontextmanager
async def lifespan(_: FastAPI):
    is_db_connected: bool = await Database.init(
        username=os.getenv("PG_USER") or "postgres",
        password=os.getenv("PG_PASSWORD") or "password",
        host=os.getenv("PG_HOST") or "localhost:5432",
        db=os.getenv("PG_DB") or "asfpc"
    )
    if not is_db_connected:
      logger.error("Failed to connect to the database. Exiting...")
      raise Exception("Failed to connect to the database.")
    else:
      logging.info("Database connected successfully.")
    yield
    await Database.close()
    logging.info("Application shutdown complete.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
      os.getenv("FRONTEND_URL") or "http://localhost:3000",
      os.getenv("N8N_URL") or "http://localhost:5678"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
  account.router
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
  import uvicorn
  port = int(os.getenv("PORT", "8000"))
  host = os.getenv("HOST", "0.0.0.0")
  uvicorn.run(app, host=host, port=port, log_level="info")