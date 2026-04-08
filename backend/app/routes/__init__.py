from app.routes.auth import router as auth_router
from app.routes.doctor_routes import router as doctor_router
from app.routes.patient_routes import router as patient_router
from app.routes.report_routes import router as report_router

__all__ = ["auth_router", "doctor_router", "patient_router", "report_router"]
