# api_server.py
from fastapi import FastAPI
from communication.api.routes import pumps
from fastapi.middleware.cors import CORSMiddleware

def create_app(core_manager):
    app = FastAPI(title="Pump Monitoring API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # In produzione metti l'IP specifico
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        )
    
    # Injection del CoreManager per renderlo accessibile alle route
    app.state.core_manager = core_manager
    
    # Includiamo i router
    app.include_router(pumps.router, prefix="/api/v1")
    
    return app