# -*- coding: utf-8 -*-
"""
Email notifications module for price alerts.

Supports multiple email providers:
- SMTP (Gmail, Outlook, custom)
- Resend API
- SendGrid API
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Optional
import streamlit as st

from modules.logger import log_error, log_warning, log_info, log_user_action
from modules.i18n import t


# Email templates
EMAIL_TEMPLATES = {
    'alert_triggered': {
        'subject': {
            'en': '🔔 Price Alert Triggered: {ticker}',
            'pl': '🔔 Alert cenowy: {ticker}',
        },
        'body': {
            'en': '''
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #1a73e8;">🔔 Price Alert Triggered</h2>

    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
        <h3 style="margin: 0;">{ticker}</h3>
        <p style="color: #666; margin: 5px 0;">{alert_type}</p>
    </div>

    <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Target Price:</strong></td>
            <td style="padding: 10px; border-bottom: 1px solid #eee;">${target_value:.2f}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Current Price:</strong></td>
            <td style="padding: 10px; border-bottom: 1px solid #eee;">${current_price:.2f}</td>
        </tr>
        <tr>
            <td style="padding: 10px;"><strong>Triggered At:</strong></td>
            <td style="padding: 10px;">{triggered_at}</td>
        </tr>
    </table>

    <p style="margin-top: 20px; color: #666;">
        This alert was set up in <strong>fin.sankey</strong> - Financial Flow Visualizer.
    </p>

    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="font-size: 12px; color: #999;">
        You received this email because you set up a price alert.
        To manage your alerts, visit the Portfolio tab in the app.
    </p>
</body>
</html>
''',
            'pl': '''
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #1a73e8;">🔔 Alert cenowy wyzwolony</h2>

    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
        <h3 style="margin: 0;">{ticker}</h3>
        <p style="color: #666; margin: 5px 0;">{alert_type}</p>
    </div>

    <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Cena docelowa:</strong></td>
            <td style="padding: 10px; border-bottom: 1px solid #eee;">${target_value:.2f}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Aktualna cena:</strong></td>
            <td style="padding: 10px; border-bottom: 1px solid #eee;">${current_price:.2f}</td>
        </tr>
        <tr>
            <td style="padding: 10px;"><strong>Wyzwolony o:</strong></td>
            <td style="padding: 10px;">{triggered_at}</td>
        </tr>
    </table>

    <p style="margin-top: 20px; color: #666;">
        Ten alert został ustawiony w <strong>fin.sankey</strong> - Wizualizacja Przepływów Finansowych.
    </p>

    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="font-size: 12px; color: #999;">
        Otrzymujesz tę wiadomość, ponieważ ustawiłeś alert cenowy.
        Aby zarządzać alertami, odwiedź zakładkę Portfolio w aplikacji.
    </p>
</body>
</html>
''',
        }
    },
    'daily_summary': {
        'subject': {
            'en': '📊 Daily Portfolio Summary - {date}',
            'pl': '📊 Dzienne podsumowanie portfela - {date}',
        },
        'body': {
            'en': '''
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #1a73e8;">📊 Daily Portfolio Summary</h2>
    <p style="color: #666;">Summary for {date}</p>

    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
        <h3 style="margin: 0;">Portfolio Value: ${total_value:,.2f}</h3>
        <p style="color: {gain_color}; margin: 5px 0; font-size: 18px;">
            {gain_sign}${total_gain:,.2f} ({gain_pct:+.2f}%)
        </p>
    </div>

    <h3>Active Alerts: {alerts_count}</h3>
    {alerts_section}

    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="font-size: 12px; color: #999;">
        fin.sankey - Financial Flow Visualizer
    </p>
</body>
</html>
''',
            'pl': '''
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #1a73e8;">📊 Dzienne podsumowanie portfela</h2>
    <p style="color: #666;">Podsumowanie za {date}</p>

    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
        <h3 style="margin: 0;">Wartość portfela: ${total_value:,.2f}</h3>
        <p style="color: {gain_color}; margin: 5px 0; font-size: 18px;">
            {gain_sign}${total_gain:,.2f} ({gain_pct:+.2f}%)
        </p>
    </div>

    <h3>Aktywne alerty: {alerts_count}</h3>
    {alerts_section}

    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="font-size: 12px; color: #999;">
        fin.sankey - Wizualizacja Przepływów Finansowych
    </p>
</body>
</html>
''',
        }
    }
}


class EmailNotifier:
    """Email notification handler supporting multiple providers."""

    def __init__(self):
        self.provider = self._detect_provider()

    def _detect_provider(self) -> str:
        """Detect which email provider is configured."""
        try:
            if 'email' in st.secrets:
                if 'sendgrid_api_key' in st.secrets['email']:
                    return 'sendgrid'
                elif 'resend_api_key' in st.secrets['email']:
                    return 'resend'
                elif 'smtp_server' in st.secrets['email']:
                    return 'smtp'
        except Exception:
            pass
        return 'none'

    def is_configured(self) -> bool:
        """Check if email notifications are configured."""
        return self.provider != 'none'

    def send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """
        Send an email using the configured provider.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML body content

        Returns:
            True if sent successfully
        """
        if self.provider == 'smtp':
            return self._send_smtp(to_email, subject, html_body)
        elif self.provider == 'resend':
            return self._send_resend(to_email, subject, html_body)
        elif self.provider == 'sendgrid':
            return self._send_sendgrid(to_email, subject, html_body)
        else:
            log_warning("Email notifications not configured")
            return False

    def _send_smtp(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send email via SMTP."""
        try:
            config = st.secrets['email']
            smtp_server = config['smtp_server']
            smtp_port = config.get('smtp_port', 587)
            smtp_user = config['smtp_user']
            smtp_password = config['smtp_password']
            from_email = config.get('from_email', smtp_user)

            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = from_email
            message['To'] = to_email

            # Attach HTML content
            html_part = MIMEText(html_body, 'html')
            message.attach(html_part)

            # Create secure connection
            context = ssl.create_default_context()

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls(context=context)
                server.login(smtp_user, smtp_password)
                server.sendmail(from_email, to_email, message.as_string())

            log_info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            log_error(e, f"Failed to send SMTP email to {to_email}")
            return False

    def _send_resend(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send email via Resend API."""
        try:
            import requests

            config = st.secrets['email']
            api_key = config['resend_api_key']
            from_email = config.get('from_email', 'alerts@fin-sankey.com')

            response = requests.post(
                'https://api.resend.com/emails',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'from': from_email,
                    'to': [to_email],
                    'subject': subject,
                    'html': html_body
                }
            )

            if response.status_code == 200:
                log_info(f"Email sent to {to_email} via Resend")
                return True
            else:
                log_warning(f"Resend API error: {response.text}")
                return False

        except ImportError:
            log_warning("requests library required for Resend API")
            return False
        except Exception as e:
            log_error(e, f"Failed to send Resend email to {to_email}")
            return False

    def _send_sendgrid(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send email via SendGrid API."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content

            config = st.secrets['email']
            api_key = config['sendgrid_api_key']
            from_email = config.get('from_email', 'alerts@fin-sankey.com')
            from_name = config.get('from_name', 'fin.sankey Alerts')

            message = Mail(
                from_email=Email(from_email, from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_body)
            )

            sg = SendGridAPIClient(api_key)
            response = sg.send(message)

            if response.status_code in [200, 201, 202]:
                log_info(f"Email sent to {to_email} via SendGrid")
                return True
            else:
                log_warning(f"SendGrid API error: status {response.status_code}")
                return False

        except ImportError:
            log_warning("sendgrid library required for SendGrid API. Install with: pip install sendgrid")
            return False
        except Exception as e:
            log_error(e, f"Failed to send SendGrid email to {to_email}")
            return False


# Global notifier instance
_notifier = None


def get_notifier() -> EmailNotifier:
    """Get or create the global email notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = EmailNotifier()
    return _notifier


def send_alert_notification(
    to_email: str,
    ticker: str,
    alert_type: str,
    target_value: float,
    current_price: float,
    language: str = 'en'
) -> bool:
    """
    Send alert triggered notification email.

    Args:
        to_email: Recipient email
        ticker: Stock ticker
        alert_type: Type of alert
        target_value: Target price/percentage
        current_price: Current stock price
        language: Email language (en/pl)

    Returns:
        True if sent successfully
    """
    notifier = get_notifier()
    if not notifier.is_configured():
        return False

    template = EMAIL_TEMPLATES['alert_triggered']
    subject = template['subject'].get(language, template['subject']['en']).format(ticker=ticker)

    # Format alert type for display
    alert_type_display = {
        'price_above': 'Price Above Target',
        'price_below': 'Price Below Target',
        'percent_up': 'Percentage Increase',
        'percent_down': 'Percentage Decrease',
    }.get(alert_type, alert_type)

    body = template['body'].get(language, template['body']['en']).format(
        ticker=ticker,
        alert_type=alert_type_display,
        target_value=target_value,
        current_price=current_price,
        triggered_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

    success = notifier.send_email(to_email, subject, body)

    if success:
        log_user_action("alert_email_sent", details={"ticker": ticker, "to": to_email})

    return success


def send_daily_summary(
    to_email: str,
    portfolio_value: float,
    total_gain: float,
    gain_pct: float,
    alerts: List[Dict],
    language: str = 'en'
) -> bool:
    """
    Send daily portfolio summary email.

    Args:
        to_email: Recipient email
        portfolio_value: Total portfolio value
        total_gain: Total gain/loss
        gain_pct: Gain percentage
        alerts: List of active alerts
        language: Email language

    Returns:
        True if sent successfully
    """
    notifier = get_notifier()
    if not notifier.is_configured():
        return False

    template = EMAIL_TEMPLATES['daily_summary']
    today = datetime.now().strftime('%Y-%m-%d')
    subject = template['subject'].get(language, template['subject']['en']).format(date=today)

    # Build alerts section
    if alerts:
        alerts_html = '<ul>'
        for alert in alerts:
            alerts_html += f"<li>{alert.get('ticker')} - {alert.get('alert_type')}: ${alert.get('target_value', 0):.2f}</li>"
        alerts_html += '</ul>'
    else:
        alerts_html = '<p>No active alerts</p>'

    gain_color = '#0f9d58' if total_gain >= 0 else '#db4437'
    gain_sign = '+' if total_gain >= 0 else ''

    body = template['body'].get(language, template['body']['en']).format(
        date=today,
        total_value=portfolio_value,
        total_gain=abs(total_gain),
        gain_pct=gain_pct,
        gain_color=gain_color,
        gain_sign=gain_sign,
        alerts_count=len(alerts),
        alerts_section=alerts_html
    )

    return notifier.send_email(to_email, subject, body)


def check_and_notify_alerts(user_id: str, user_email: str, alerts: List[Dict], language: str = 'en') -> List[Dict]:
    """
    Check alerts and send notifications for triggered ones.

    Args:
        user_id: User ID
        user_email: User's email address
        alerts: List of user's alerts
        language: User's preferred language

    Returns:
        List of triggered alerts that were notified
    """
    from modules.alerts import check_alert_triggered, get_current_price

    notified = []

    for alert in alerts:
        if not alert.get('is_active', True):
            continue

        # Skip if already notified recently (check notification_sent flag)
        if alert.get('notification_sent'):
            continue

        ticker = alert.get('ticker')
        current_price = get_current_price(ticker)

        if current_price and check_alert_triggered(alert, current_price):
            # Send notification
            success = send_alert_notification(
                to_email=user_email,
                ticker=ticker,
                alert_type=alert.get('alert_type', ''),
                target_value=alert.get('target_value', 0),
                current_price=current_price,
                language=language
            )

            if success:
                notified.append({
                    **alert,
                    'current_price': current_price,
                    'notified_at': datetime.now().isoformat()
                })

    return notified


def render_email_settings():
    """Render email notification settings in Streamlit UI."""
    st.subheader(f"📧 {t('email_notifications')}")

    notifier = get_notifier()

    if not notifier.is_configured():
        st.warning(t('email_not_configured'))
        st.caption("Configure email in .streamlit/secrets.toml")
        return

    st.success(f"✅ {t('email_configured')} ({notifier.provider.upper()})")

    # Email preferences
    col1, col2 = st.columns(2)

    with col1:
        alert_emails = st.checkbox(
            t('receive_alert_emails'),
            value=st.session_state.get('email_alerts', True),
            key='email_alerts_toggle'
        )
        st.session_state['email_alerts'] = alert_emails

    with col2:
        daily_summary = st.checkbox(
            t('receive_daily_summary'),
            value=st.session_state.get('email_daily', False),
            key='email_daily_toggle'
        )
        st.session_state['email_daily'] = daily_summary

    # Test email button
    if st.button(t('send_test_email'), key='btn_test_email'):
        user = st.session_state.get('user')
        if user and user.email:
            success = send_alert_notification(
                to_email=user.email,
                ticker='TEST',
                alert_type='price_above',
                target_value=100.0,
                current_price=105.0,
                language=st.session_state.get('language', 'en')
            )
            if success:
                st.success(f"✅ Test email sent to {user.email}")
            else:
                st.error("Failed to send test email")
        else:
            st.warning("Please log in to send test email")
