import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",  # Путь к вашему FastAPI приложению
        host="127.0.0.1",  # Локальный хост
        port=8000,         # Порт
        reload=True        # Автоперезагрузка при изменении кода
    )