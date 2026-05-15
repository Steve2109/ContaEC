"""
Aplicación principal FastAPI para ContaEC
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import SlowAPI, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from contextlib import asynccontextmanager
import logging
import os

from .core.config import settings
from .core.database import engine, Base, get_db
from .api import auth, admin, files
from .routes import facturacion
from .services.auth_service import UserService, LicenseService
from .models import User, License, LicenseType
from .models.facturacion import EmpresaConfiguracion, CertificadoDigital, Cliente, ProductoServicio, ComprobanteElectronico
from datetime import datetime, timedelta


# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación
    """
    # Startup
    logger.info("Iniciando ContaEC...")
    
    # Crear tablas de base de datos
    Base.metadata.create_all(bind=engine)
    logger.info("Base de datos inicializada")
    
    # Crear usuario administrador por defecto si no existe
    db_session = next(get_db())
    try:
        admin_user = db_session.query(User).filter(User.is_admin == True).first()
        
        if not admin_user:
            from .schemas import UserCreate
            
            admin_data = UserCreate(
                email=settings.ADMIN_EMAIL,
                password=settings.ADMIN_PASSWORD,
                full_name="Administrador Sistema"
            )
            
            admin_user = UserService.create_user(db_session, admin_data, is_admin=True)
            
            # Crear licencia perpetua para admin
            LicenseService.create_license(
                db=db_session,
                user_id=admin_user.id,
                license_type=LicenseType.ANUAL,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=365 * 10)  # 10 años
            )
            
            logger.info(f"Usuario administrador creado: {settings.ADMIN_EMAIL}")
    finally:
        db_session.close()
    
    yield
    
    # Shutdown
    logger.info("Cerrando ContaEC...")


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description=f"Sistema Contable y Facturación Electrónica - {settings.DEVELOPER}",
    version="1.0.0",
    contact={
        "name": settings.DEVELOPER,
        "email": settings.SUPPORT_EMAIL,
        "phone": settings.SUPPORT_PHONE
    },
    lifespan=lifespan
)

# Configurar rate limiting
limiter = SlowAPI(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - {response.status_code}")
    return response


# Manejador de errores global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error no manejado: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "type": type(exc).__name__}
    )


# Incluir routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(files.router)
app.include_router(facturacion.router)


# Rutas básicas
@app.get("/")
async def root():
    """
    Endpoint raíz - Información de la API
    """
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "developer": settings.DEVELOPER,
        "support": settings.SUPPORT_EMAIL,
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
@limiter.limit("10/minute")
async def health_check(request: Request):
    """
    Endpoint de verificación de salud
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


# Exportar app para uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
