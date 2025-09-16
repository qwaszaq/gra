"""
Admin Service - FastAPI application for game administration and logging.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Request, status, Form
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from pydantic import BaseModel
import httpx

from database import get_db, init_database
from models import AdminLog, GameSession, GameTurn, LogEntryRequest, LogEntryResponse, SessionSummary, DashboardStats
from pdf_generator import PDFReportGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Admin Service",
    description="Administration panel and logging service for Partnerzy w Zbrodni",
    version="1.0.0"
)

# CORS
origins = [os.getenv("WEB_CLIENT_ORIGIN", "http://localhost:5173")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize PDF generator
pdf_generator = PDFReportGenerator()

# Admin token for authentication
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev_admin_token_123")

# Admin Basic Auth (dla UI)
ADMIN_BASIC_USER = os.getenv("ADMIN_BASIC_USER", "")
ADMIN_BASIC_PASS = os.getenv("ADMIN_BASIC_PASS", "")
security = HTTPBasic()

def require_basic(creds: HTTPBasicCredentials = Depends(security)):
    if not ADMIN_BASIC_USER or not ADMIN_BASIC_PASS:
        return
    ok_user = secrets.compare_digest(creds.username, ADMIN_BASIC_USER)
    ok_pass = secrets.compare_digest(creds.password, ADMIN_BASIC_PASS)
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized",
                            headers={"WWW-Authenticate":"Basic"})

# Environment variables for external services
VISION_PUBLIC_BASE = os.getenv("VISION_PUBLIC_BASE", "http://localhost:8004")
GAME_SERVER_INTERNAL_BASE = os.getenv("GAME_SERVER_INTERNAL_BASE", "http://game_server:65432")


def verify_admin_token(request: Request):
    """Verify admin token from request headers."""
    token = request.headers.get("X-Admin-Token")
    if token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token"
        )
    return token


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_database()
    logger.info("Admin Service started")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db), _: None = Depends(require_basic)):
    """Main dashboard page."""
    try:
        # Get statistics
        total_sessions = db.query(GameSession).count()
        active_sessions = db.query(GameSession).filter(GameSession.status == 'active').count()
        total_turns = db.query(GameTurn).count()
        total_actions = db.query(func.sum(GameTurn.actions_count)).scalar() or 0
        
        # Get recent sessions
        recent_sessions = db.query(GameSession).order_by(desc(GameSession.last_activity)).limit(5).all()
        
        # Get recent logs
        recent_logs = db.query(AdminLog).order_by(desc(AdminLog.timestamp)).limit(10).all()
        recent_logs_response = [
            LogEntryResponse(
                id=log.id,
                timestamp=log.timestamp,
                level=log.level,
                service=log.service,
                message=log.message,
                session_id=log.session_id,
                turn_id=log.turn_id,
                player=log.player,
                action=log.action,
                extra_data=log.extra_data
            ) for log in recent_logs
        ]
        
        stats = DashboardStats(
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            total_turns=total_turns,
            total_actions=total_actions,
            recent_logs=recent_logs_response
        )
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "stats": stats,
            "recent_sessions": recent_sessions
        })
    
    except Exception as e:
        logger.error(f"Error in dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/sessions", response_class=HTMLResponse)
async def sessions_list(request: Request, db: Session = Depends(get_db), _: None = Depends(require_basic)):
    """List all game sessions."""
    try:
        sessions = db.query(GameSession).order_by(desc(GameSession.created_at)).all()
        
        # Convert to session summaries
        session_summaries = []
        for session in sessions:
            turn_count = db.query(GameTurn).filter(GameTurn.session_id == session.session_id).count()
            total_actions = db.query(func.sum(GameTurn.actions_count)).filter(
                GameTurn.session_id == session.session_id
            ).scalar() or 0
            
            session_summaries.append(SessionSummary(
                session_id=session.session_id,
                created_at=session.created_at,
                last_activity=session.last_activity,
                status=session.status,
                player_count=session.player_count,
                scenario=session.scenario,
                turn_count=turn_count,
                total_actions=total_actions
            ))
        
        return templates.TemplateResponse("sessions.html", {
            "request": request,
            "sessions": session_summaries
        })
    
    except Exception as e:
        logger.error(f"Error in sessions list: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/sessions/{session_id}", response_class=HTMLResponse)
async def session_detail(session_id: str, request: Request, db: Session = Depends(get_db), _: None = Depends(require_basic)):
    """Detailed view of a specific session."""
    try:
        session = db.query(GameSession).filter(GameSession.session_id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get turns for this session
        turns = db.query(GameTurn).filter(GameTurn.session_id == session_id).order_by(GameTurn.turn_number).all()
        
        # Get logs for this session
        logs = db.query(AdminLog).filter(AdminLog.session_id == session_id).order_by(desc(AdminLog.timestamp)).all()
        
        return templates.TemplateResponse("session_detail.html", {
            "request": request,
            "session": session,
            "turns": turns,
            "logs": logs
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in session detail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/logs", response_class=HTMLResponse)
async def logs_list(request: Request, db: Session = Depends(get_db), _: None = Depends(require_basic)):
    """List all logs with filtering."""
    try:
        # Get query parameters
        level = request.query_params.get("level")
        service = request.query_params.get("service")
        session_id = request.query_params.get("session_id")
        hours = int(request.query_params.get("hours", 24))
        
        # Build query
        query = db.query(AdminLog)
        
        if level:
            query = query.filter(AdminLog.level == level)
        if service:
            query = query.filter(AdminLog.service == service)
        if session_id:
            query = query.filter(AdminLog.session_id == session_id)
        
        # Filter by time
        since_time = datetime.now() - timedelta(hours=hours)
        query = query.filter(AdminLog.timestamp >= since_time)
        
        logs = query.order_by(desc(AdminLog.timestamp)).limit(100).all()
        
        # Convert to response format
        logs_response = [
            LogEntryResponse(
                id=log.id,
                timestamp=log.timestamp,
                level=log.level,
                service=log.service,
                message=log.message,
                session_id=log.session_id,
                turn_id=log.turn_id,
                player=log.player,
                action=log.action,
                extra_data=log.extra_data
            ) for log in logs
        ]
        
        return templates.TemplateResponse("logs.html", {
            "request": request,
            "logs": logs_response,
            "filters": {
                "level": level,
                "service": service,
                "session_id": session_id,
                "hours": hours
            }
        })
    
    except Exception as e:
        logger.error(f"Error in logs list: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/log", response_model=dict)
async def create_log_entry(
    log_entry: LogEntryRequest,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin_token)
):
    """Create a new log entry."""
    try:
        # Create log entry
        db_log = AdminLog(
            level=log_entry.level,
            message=log_entry.message,
            service=log_entry.service,
            session_id=log_entry.session_id,
            turn_id=log_entry.turn_id,
            player=log_entry.player,
            action=log_entry.action,
            extra_data=log_entry.extra_data
        )
        
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        
        logger.info(f"Log entry created: {db_log.id}")
        
        return {"status": "logged", "id": db_log.id}
    
    except Exception as e:
        logger.error(f"Error creating log entry: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/report/pdf")
async def generate_pdf_report(
    session_id: Optional[str] = None,
    hours: int = 24,
    db: Session = Depends(get_db),
    _: str = Depends(verify_admin_token)
):
    """Generate PDF report."""
    try:
        if session_id:
            # Generate session-specific report
            pdf_buffer = pdf_generator.generate_session_report(db, session_id)
            filename = f"session_report_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        else:
            # Generate general report
            pdf_buffer = pdf_generator.generate_session_report(db)
            filename = f"admin_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "admin_service", "timestamp": datetime.now().isoformat()}


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get statistics as JSON API."""
    try:
        total_sessions = db.query(GameSession).count()
        active_sessions = db.query(GameSession).filter(GameSession.status == 'active').count()
        total_turns = db.query(GameTurn).count()
        total_actions = db.query(func.sum(GameTurn.actions_count)).scalar() or 0
        total_logs = db.query(AdminLog).count()
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_turns": total_turns,
            "total_actions": total_actions,
            "total_logs": total_logs,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/vision/suggest")
def suggest_images(text: str, k: int = 3, collection: str | None = None):
    """
    Proxy do Vision Selector /match_topk
    """
    try:
        payload = {"text": text, "k": k, "collection": collection}
        r = httpx.post(f"{VISION_PUBLIC_BASE}/match_topk", json=payload, timeout=10)
        return JSONResponse(r.json())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vision unavailable: {e}")


@app.post("/override")
async def post_override(request: Request):
    """
    Przyjmuje JSON:
    { "session_id":"demo-1", "turn":1, "image":"http://.../assets/images/..."}
    Wysyła do GameServer /override z X-Admin-Token.
    """
    if ADMIN_TOKEN:
        tok = request.headers.get("X-Admin-Token","")
        if tok != ADMIN_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    headers = {"X-Admin-Token": ADMIN_TOKEN} if ADMIN_TOKEN else {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(f"{GAME_SERVER_INTERNAL_BASE}/override", headers=headers, json=body)
            return JSONResponse(r.json())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GameServer override failed: {e}")


@app.get("/ui/override", response_class=HTMLResponse)
async def ui_override(request: Request, session_id: str, turn: int, text: str = "", k: int = 3, _: None = Depends(require_basic)):
    """UI for Suggest & Override functionality."""
    # pobierz podpowiedzi z Vision (użyj istniejącego /api/vision/suggest lub bezpośrednio Vision)
    suggestions = None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(f"{VISION_PUBLIC_BASE}/match_topk", json={"text": text or "noir scene", "k": k})
            suggestions = r.json()
    except Exception as e:
        suggestions = {"error": str(e), "images": []}

    return templates.TemplateResponse("override.html", {
        "request": request,
        "session_id": session_id,
        "turn": turn,
        "text": text,
        "k": k,
        "suggestions": suggestions,
        "vision_base": VISION_PUBLIC_BASE,
        "status": request.query_params.get("status")
    })


@app.post("/ui/override/apply")
async def ui_override_apply(request: Request,
                            session_id: str = Form(...),
                            turn: int = Form(...),
                            image: str = Form(None)):
    """Apply override with selected image."""
    # wyślij override do Game Servera przez istniejący endpoint /override
    headers = {"X-Admin-Token": ADMIN_TOKEN} if ADMIN_TOKEN else {}
    payload = {"session_id": session_id, "turn": int(turn)}
    if image:
        payload["image"] = image
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{GAME_SERVER_INTERNAL_BASE}/override", headers=headers, json=payload)
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=r.text)
        # redirect z komunikatem
        url = f"/ui/override?session_id={session_id}&turn={turn}&status=OK"
        return RedirectResponse(url, status_code=303)
    except Exception as e:
        url = f"/ui/override?session_id={session_id}&turn={turn}&status=ERROR:{str(e)}"
        return RedirectResponse(url, status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
