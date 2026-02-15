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
from datetime import datetime

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

    async def send_verification_email(
        self, email: str, name: str, verification_link: str
    ) -> bool:
        """Send email verification link to new user."""
        subject = "Verify Your NAV Scoring Account"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Welcome to NAV Scoring!</h2>
                <p>Hi {name},</p>
                <p>Thank you for signing up for the NAV Scoring system. Please verify your email address by clicking the link below:</p>
                <p style="margin: 2rem 0;">
                    <a href="{verification_link}" style="background-color: #003366; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Verify Email Address</a>
                </p>
                <p>Or copy and paste this link in your browser:</p>
                <p style="word-break: break-all; background-color: #f0f0f0; padding: 10px; font-family: monospace; font-size: 12px;">
                    {verification_link}
                </p>
                <p style="color: #999; font-size: 12px;">This link expires in 24 hours.</p>
                <p style="color: #999; font-size: 12px;">If you didn't request this, please ignore this email.</p>
                <p>NAV Scoring System</p>
            </body>
        </html>
        """
        
        text_body = f"""
Welcome to NAV Scoring!

Hi {name},

Thank you for signing up for the NAV Scoring system. Please verify your email address by clicking the link below:

{verification_link}

This link expires in 24 hours.

If you didn't request this, please ignore this email.

NAV Scoring System
        """
        
        return await self._send_email(
            to_email=email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )

    async def send_prenav_confirmation(
        self, team_emails, team_name: str, nav_name: str, 
        submission_date: str, pilot_name: str = "", observer_name: str = "", 
        token: Optional[str] = None
    ) -> bool:
        """Send pre-flight confirmation email to team. v0.4.0: No token needed.
        Accepts single email (str) or list of emails."""
        # Handle both single email string and list of emails
        if isinstance(team_emails, str):
            team_emails = [team_emails]
        
        subject = f"Pre-NAV Confirmation: {nav_name}"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Pre-Flight Plan Received</h2>
                <p>Hi {team_name},</p>
                <p>Your pre-flight planning data has been received and recorded.</p>
                <h3>Submission Details:</h3>
                <ul style="background-color: #f0f0f0; padding: 15px; border-radius: 5px;">
                    <li><strong>NAV Route:</strong> {nav_name}</li>
                    <li><strong>Submitted:</strong> {submission_date}</li>
                    <li><strong>Pilot:</strong> {pilot_name}</li>
                    <li><strong>Observer:</strong> {observer_name}</li>
                </ul>
                <p>After you complete the flight, log in to the NAV Scoring portal and submit your post-flight data. You'll select this submission from your list of open plans.</p>
                <p>Good luck!</p>
                <p>NAV Scoring System</p>
            </body>
        </html>
        """
        
        text_body = f"""
Pre-Flight Plan Received

Hi {team_name},

Your pre-flight planning data has been received and recorded.

Submission Details:
NAV Route: {nav_name}
Submitted: {submission_date}
Pilot: {pilot_name}
Observer: {observer_name}

After you complete the flight, log in to the NAV Scoring portal and submit your post-flight data. You'll select this submission from your list of open plans.

Good luck!
NAV Scoring System
        """
        
        # Send to all emails
        all_success = True
        for email in team_emails:
            success = await self._send_email(
                to_email=email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            all_success = all_success and success
        
        return all_success

    async def send_results_notification(
        self,
        team_emails,
        team_name: str,
        nav_name: str,
        overall_score: float,
        pdf_filename: Optional[str] = None,
    ) -> bool:
        """Send flight results email to team and coach. Accepts single email (str) or list of emails."""
        # Handle both single email string and list of emails
        if isinstance(team_emails, str):
            team_emails = [team_emails]
        
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
        
        # Send to all team emails
        all_success = True
        for email in team_emails:
            success = await self._send_email(
                to_email=email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            all_success = all_success and success
        
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
        
        return all_success

    async def test_connection(self) -> tuple[bool, str]:
        """Test SMTP connection, authentication, and send a test email.
        
        Returns:
            tuple[bool, str]: (success, message)
        """
        try:
            # Test 1: Connection
            logger.info(f"Testing SMTP connection to {self.smtp_host}:{self.smtp_port}")
            async with aiosmtplib.SMTP(hostname=self.smtp_host, port=self.smtp_port) as smtp:
                # Test 2: Authentication
                logger.info(f"Testing authentication as {self.sender_email}")
                await smtp.login(self.sender_email, self.sender_password)
                
                # Test 3: Send test email
                logger.info(f"Sending test email to {self.sender_email}")
                
                test_subject = "NAV Scoring SMTP Test"
                test_body = "This is a test email from the NAV Scoring system. If you received this, SMTP is configured correctly."
                html_body = f"""
                <html>
                    <body style="font-family: Arial, sans-serif;">
                        <h2>NAV Scoring SMTP Test</h2>
                        <p>{test_body}</p>
                        <p style="color: #999; font-size: 12px;">Sent at {datetime.utcnow().isoformat()}</p>
                    </body>
                </html>
                """
                
                msg = MIMEMultipart("alternative")
                msg["Subject"] = test_subject
                msg["From"] = f"{self.sender_name} <{self.sender_email}>"
                msg["To"] = self.sender_email
                
                msg.attach(MIMEText(test_body, "plain"))
                msg.attach(MIMEText(html_body, "html"))
                
                await smtp.send_message(msg)
                
                logger.info("SMTP test successful - all checks passed")
                return (True, "SMTP connection successful! Test email sent to " + self.sender_email)
        
        except aiosmtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return (False, f"Authentication failed: {str(e)}")
        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return (False, f"SMTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to test SMTP connection: {e}")
            error_msg = str(e)
            if "Name or service not known" in error_msg or "nodename nor servname provided" in error_msg:
                return (False, f"Connection failed: Unable to reach SMTP host '{self.smtp_host}'")
            elif "Connection refused" in error_msg or "refused" in error_msg:
                return (False, f"Connection failed: SMTP host '{self.smtp_host}' refused connection on port {self.smtp_port}")
            else:
                return (False, f"Connection failed: {error_msg}")

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
