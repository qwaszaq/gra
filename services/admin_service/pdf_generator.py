"""
PDF report generation for Admin Service.
"""
import os
from datetime import datetime, timedelta
from io import BytesIO
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import HRFlowable
from models import AdminLog, GameSession, GameTurn


class PDFReportGenerator:
    """Generate PDF reports for admin dashboard."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.darkblue
        ))
        
        # Heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue
        ))
        
        # Subheading style
        self.styles.add(ParagraphStyle(
            name='CustomSubHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            textColor=colors.darkgreen
        ))
        
        # Normal text style
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
        
        # Small text style
        self.styles.add(ParagraphStyle(
            name='CustomSmall',
            parent=self.styles['Normal'],
            fontSize=8,
            spaceAfter=4
        ))
    
    def generate_session_report(self, db: Session, session_id: Optional[str] = None) -> BytesIO:
        """Generate a comprehensive session report."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
        story = []
        
        # Title
        title = "RAPORT SESJI GRY"
        if session_id:
            title += f" - {session_id}"
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Report metadata
        story.append(Paragraph(f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.styles['CustomSmall']))
        story.append(Spacer(1, 20))
        
        # Get data
        if session_id:
            sessions = db.query(GameSession).filter(GameSession.session_id == session_id).all()
        else:
            sessions = db.query(GameSession).order_by(desc(GameSession.created_at)).limit(10).all()
        
        for session in sessions:
            # Session header
            story.append(Paragraph(f"Sesja: {session.session_id}", self.styles['CustomHeading']))
            story.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.grey))
            
            # Session details
            session_data = [
                ['ID Sesji', session.session_id],
                ['Utworzona', session.created_at.strftime('%Y-%m-%d %H:%M:%S')],
                ['Ostatnia aktywność', session.last_activity.strftime('%Y-%m-%d %H:%M:%S')],
                ['Status', session.status],
                ['Liczba graczy', str(session.player_count)],
                ['Scenariusz', session.scenario or 'N/A']
            ]
            
            session_table = Table(session_data, colWidths=[2*inch, 3*inch])
            session_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (1, 0), (1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(session_table)
            story.append(Spacer(1, 20))
            
            # Turns for this session
            turns = db.query(GameTurn).filter(GameTurn.session_id == session.session_id).order_by(GameTurn.turn_number).all()
            
            if turns:
                story.append(Paragraph("Tury gry:", self.styles['CustomSubHeading']))
                
                turn_data = [['Nr', 'ID Tury', 'Rozpoczęta', 'Zakończona', 'Status', 'Akcje', 'Narracja']]
                for turn in turns:
                    turn_data.append([
                        str(turn.turn_number),
                        turn.turn_id,
                        turn.started_at.strftime('%H:%M:%S'),
                        turn.completed_at.strftime('%H:%M:%S') if turn.completed_at else 'N/A',
                        turn.status,
                        str(turn.actions_count),
                        'Tak' if turn.narrative_generated == 'true' else 'Nie'
                    ])
                
                turn_table = Table(turn_data, colWidths=[0.5*inch, 1*inch, 1*inch, 1*inch, 0.8*inch, 0.5*inch, 0.5*inch])
                turn_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(turn_table)
                story.append(Spacer(1, 20))
            
            # Logs for this session
            logs = db.query(AdminLog).filter(AdminLog.session_id == session.session_id).order_by(desc(AdminLog.timestamp)).limit(20).all()
            
            if logs:
                story.append(Paragraph("Logi sesji:", self.styles['CustomSubHeading']))
                
                for log in logs:
                    log_text = f"<b>{log.timestamp.strftime('%H:%M:%S')}</b> [{log.level.upper()}] {log.service}: {log.message}"
                    if log.player:
                        log_text += f" (Gracz: {log.player})"
                    if log.action:
                        log_text += f" (Akcja: {log.action})"
                    
                    story.append(Paragraph(log_text, self.styles['CustomSmall']))
                    story.append(Spacer(1, 4))
            
            story.append(PageBreak())
        
        # Summary statistics
        story.append(Paragraph("PODSUMOWANIE STATYSTYK", self.styles['CustomHeading']))
        story.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.grey))
        
        # Get summary stats
        total_sessions = db.query(GameSession).count()
        active_sessions = db.query(GameSession).filter(GameSession.status == 'active').count()
        total_turns = db.query(GameTurn).count()
        total_actions = db.query(func.sum(GameTurn.actions_count)).scalar() or 0
        total_logs = db.query(AdminLog).count()
        
        summary_data = [
            ['Metryka', 'Wartość'],
            ['Łączna liczba sesji', str(total_sessions)],
            ['Aktywne sesje', str(active_sessions)],
            ['Łączna liczba tur', str(total_turns)],
            ['Łączna liczba akcji', str(total_actions)],
            ['Łączna liczba logów', str(total_logs)]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def generate_logs_report(self, db: Session, hours: int = 24) -> BytesIO:
        """Generate a logs report for the last N hours."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
        story = []
        
        # Title
        story.append(Paragraph("RAPORT LOGÓW", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Report metadata
        since_time = datetime.now() - timedelta(hours=hours)
        story.append(Paragraph(f"Okres: ostatnie {hours} godzin (od {since_time.strftime('%Y-%m-%d %H:%M:%S')})", self.styles['CustomSmall']))
        story.append(Paragraph(f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.styles['CustomSmall']))
        story.append(Spacer(1, 20))
        
        # Get logs
        logs = db.query(AdminLog).filter(AdminLog.timestamp >= since_time).order_by(desc(AdminLog.timestamp)).all()
        
        if logs:
            # Logs table
            log_data = [['Czas', 'Poziom', 'Serwis', 'Wiadomość', 'Sesja', 'Gracz']]
            for log in logs:
                log_data.append([
                    log.timestamp.strftime('%H:%M:%S'),
                    log.level.upper(),
                    log.service,
                    log.message[:50] + '...' if len(log.message) > 50 else log.message,
                    log.session_id[:8] + '...' if log.session_id else 'N/A',
                    log.player or 'N/A'
                ])
            
            log_table = Table(log_data, colWidths=[0.8*inch, 0.6*inch, 1*inch, 2.5*inch, 0.8*inch, 0.8*inch])
            log_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            story.append(log_table)
        else:
            story.append(Paragraph("Brak logów w wybranym okresie.", self.styles['CustomNormal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
