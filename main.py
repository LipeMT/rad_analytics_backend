import asyncio
from fastapi import FastAPI
from routers import router
from services.import_dataset import import_files_excel
from db.database import engine, Base
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Análise RAD API",
    version="1.0.0",
    description="API para análises estatísticas do RAD",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


async def main():
    print("Criando tabelas...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Importando arquivos Excel...")
    await import_files_excel("./dataset")


if __name__ == "__main__":
    # asyncio.run(main())
    import uvicorn

    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
