import os

import uvicorn

if __name__ == '__main__':
    uvicorn.run("webapp.app:app", host=os.getenv("WEBAPP_HOST", "0.0.0.0"), port=int(os.getenv("WEBAPP_PORT", "8080")),
                log_level="info")
