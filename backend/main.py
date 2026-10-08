from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.general import router as general_router
from backend.routes.auth import router as auth_router
from backend.routes import complaints
from backend.routes import admin
from backend.routes import student

app = FastAPI(
    title="Campus Complaint Auto-Categorization System API",
    description="Intelligent college complaint management platform with AI-driven categorization & urgency detection.",
    version="1.0.0"
)

# Enable CORS for frontend applications (localhost:3000, 5173, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoints
app.include_router(general_router)
app.include_router(auth_router)
app.include_router(complaints.router)
app.include_router(admin.router)
app.include_router(student.router)

# Aliases with /api prefix for frontend compatibility
app.include_router(auth_router, prefix="/api")
app.include_router(complaints.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(student.router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Campus Complaint System API"}
