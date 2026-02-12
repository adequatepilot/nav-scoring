"""
Email service for NAV Scoring system.
Sends results notifications via Zoho SMTP.
"""

import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, config: dict):
        """
        config: Dict with keys:
          - smtp_host, smtp_port, sender_email, sender_password, sender_name, recipients_coach
        """
        self.config = config
        self.smtp_host = config.get("smtp_host")
        self.smtp_port = config.get("smtp_port", 587)
        self.sender_email = config.get("sender_email")
        self.sender_password = config.get("sender_password")
        self.sender_name = config.get("sender_name", "NAV Scoring")
        self.coach_email = config.get("recipients_coach")

    async def send_prenav_confirmation(
        self, team_email: str, team_name: str, nav_name: str, token: str
    ) -> bool:
        """Send pre-flight confirmation email to team."""
        subject = f"Pre-NAV Confirmation: {nav_name}"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Pre-Flight Plan Received</h2>
                <p>Hi {team_name},</p>
                <p>Your pre-flight planning data for <strong>{nav_name}</strong> has been received and recorded.</p>
                <h3>Your Submission Token:</h3>
                <p style="background-color: #f0f0f0; padding: 10px; font-family: monospace; font-size: 14px;">
                    {token}
                </p>
                <p>After you complete the flight, go to the flight form and paste this token to submit your GPX file and receive your score.</p>
                <p><strong>Token expires in 48 hours.</strong></p>
                <p>Good luck!</p>
                <p>NAV Scoring System</p>
            </body>
        </html>
        """
        
        text_body = f"""
Pre-Flight Plan Received

Hi {team_name},

Your pre-flight planning data for {nav_name} has been received and recorded.

Your Submission Token:
{token}

After you complete the flight, go to the flight form and paste this token to submit your GPX file and receive your score.

Token expires in 48 hours.

Good luck!
NAV Scoring System
        """
        
        return await self._send_email(
            to_email=team_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )

    async def send_results_notification(
        self,
        team_email: str,
        team_name: str,
        nav_name: str,
        overall_score: float,
        pdf_filename: Optional[str] = None,
    ) -> bool:
        """Send flight results email to team and coach."""
        subject = f"Flight Scored: {nav_name} - Score: {overall_score:.0f}"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Flight Results</h2>
                <p>Hi {team_name},</p>
                <p>Your flight for <strong>{nav_name}</strong> has been scored!</p>
                <h3>Overall Score: <span style="color: #d9534f; font-size: 24px;">{overall_score:.0f} points</span></h3>
                <p style="color: #999; font-size: 12px;">(Lower score is better)</p>
                <p>Log in to the NAV Scoring portal to view detailed results and download your PDF report.</p>
                <p>Questions? Contact your coach.</p>
                <p>NAV Scoring System</p>
            </body>
        </html>
        """
        
        text_body = f"""
Flight Results

Hi {team_name},

Your flight for {nav_name} has been scored!

Overall Score: {overall_score:.0f} points
(Lower score is better)

Log in to the NAV Scoring portal to view detailed results and download your PDF report.

Questions? Contact your coach.

NAV Scoring System
        """
        
        # Send to team
        await self._send_email(
            to_email=team_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
        
        # Send to coach
        await self._send_email(
            to_email=self.coach_email,
            subject=f"[RESULTS] {team_name} - {nav_name} - Score: {overall_score:.0f}",
            html_body=f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Team Flight Results</h2>
                    <p><strong>Team:</strong> {team_name}</p>
                    <p><strong>NAV:</strong> {nav_name}</p>
                    <h3>Score: {overall_score:.0f} points</h3>
                    <p>Log in to review detailed results.</p>
                </body>
            </html>
            """,
            text_body=f"""
Team Flight Results

Team: {team_name}
NAV: {nav_name}
Score: {overall_score:.0f} points

Log in to review detailed results.
            """
        )
        
        return True

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """Internal method to send email via Zoho SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.sender_name} <{self.sender_email}>"
            msg["To"] = to_email

            # Attach both text and HTML versions
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            async with aiosmtplib.SMTP(hostname=self.smtp_host, port=self.smtp_port) as smtp:
                await smtp.login(self.sender_email, self.sender_password)
                await smtp.send_message(msg)

            logger.info(f"Email sent to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
