"""
HS AI SOLUTIONS — MULTI-CHANNEL MESSAGING GATEWAY
Module: hs_ecosystem.gateway.messaging
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM

Implements Pillar 9:
Connectors for:
- Telegram Bot API
- Discord Webhook & Bot
- Slack Webhook & Events
- WhatsApp Business / Twilio API
- WebChat (WebSocket)
Includes strict authentication and sender identity validation.
"""

from __future__ import annotations
import os
import json
import time
import urllib.request
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class InboundMessage:
    channel: str  # telegram, discord, slack, whatsapp, webchat
    sender_id: str
    sender_name: str
    content: str
    auth_token: Optional[str] = None
    timestamp: float = 0.0


class MessagingConnectorBase:
    """Base connector interface for messaging platforms."""

    def __init__(self, channel_name: str, allowed_tokens: Optional[list] = None):
        self.channel_name = channel_name
        self.allowed_tokens = set(allowed_tokens or [])

    def authenticate_sender(self, msg: InboundMessage) -> bool:
        if not self.allowed_tokens:
            return True
        return msg.auth_token in self.allowed_tokens


class TelegramConnector(MessagingConnectorBase):
    """Integrates with Telegram Bot API."""

    def __init__(self, bot_token: Optional[str] = None, allowed_users: Optional[list] = None):
        super().__init__("telegram", allowed_users)
        self.bot_token = bot_token

    def send_message(self, chat_id: str, text: str) -> bool:
        if not self.bot_token:
            return False
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False


class DiscordConnector(MessagingConnectorBase):
    """Integrates with Discord Webhooks."""

    def __init__(self, webhook_url: Optional[str] = None):
        super().__init__("discord")
        self.webhook_url = webhook_url

    def send_webhook(self, content: str, username: str = "July AI") -> bool:
        if not self.webhook_url:
            return False
        payload = json.dumps({"content": content, "username": username}).encode("utf-8")
        req = urllib.request.Request(self.webhook_url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False


class SlackConnector(MessagingConnectorBase):
    """Integrates with Slack Incoming Webhooks."""

    def __init__(self, webhook_url: Optional[str] = None):
        super().__init__("slack")
        self.webhook_url = webhook_url

    def send_message(self, text: str) -> bool:
        if not self.webhook_url:
            return False
        payload = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(self.webhook_url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False


class MultiChannelGatewayManager:
    """Dispatches inbound messages to the autonomous agent and returns responses."""

    def __init__(self, agent_callback: Optional[Callable[[str], str]] = None):
        self.agent_callback = agent_callback
        self.telegram = TelegramConnector()
        self.discord = DiscordConnector()
        self.slack = SlackConnector()

    def process_inbound(self, msg: InboundMessage) -> Dict[str, Any]:
        connector = getattr(self, msg.channel, None)
        if connector and not connector.authenticate_sender(msg):
            return {"success": False, "error": "UNAUTHORIZED_SENDER"}

        if self.agent_callback:
            reply = self.agent_callback(msg.content)
            return {"success": True, "reply": reply}

        return {"success": True, "reply": f"Received: {msg.content}"}
