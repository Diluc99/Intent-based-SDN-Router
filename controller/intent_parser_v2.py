#!/usr/bin/env python3
"""
Intent Parser for SDN Controller
This module is kept for backward compatibility but is no longer used
since we're using pure LLM processing.
"""
import logging
import re

logger = logging.getLogger(__name__)

class IntentParser:
    """
    Legacy intent parser - kept for compatibility
    All actual parsing is now done by the LLM in ConversationManager
    """
    
    def __init__(self):
        logger.info("Intent Parser initialized (legacy mode)")
        
        # Legacy patterns for reference
        self.patterns = {
            'optimize_video': [
                r'optimize.*video',
                r'video.*call',
                r'zoom.*slow',
                r'teams.*lag'
            ],
            'security': [
                r'enhance.*security',
                r'secure.*network',
                r'block.*threat',
                r'protect.*network'
            ],
            'bandwidth': [
                r'limit.*bandwidth',
                r'restrict.*speed',
                r'cap.*traffic',
                r'guest.*wifi'
            ],
            'priority': [
                r'prioritize',
                r'important.*traffic',
                r'critical.*service',
                r'database.*priority'
            ]
        }
    
    def parse_intent(self, message):
        """
        Legacy parser - returns basic intent structure
        Actual parsing is done by LLM
        """
        message_lower = message.lower()
        
        # Default intent
        intent = {
            'name': 'Custom Intent',
            'policy': 'custom',
            'priority': 50,
            'bandwidth': 'unlimited',
            'action': 'custom',
            'protocol': 'all'
        }
        
        # Check for keywords (basic fallback)
        if any(re.search(p, message_lower) for p in self.patterns['optimize_video']):
            intent.update({
                'name': 'Video Optimization',
                'policy': 'qos',
                'priority': 85,
                'action': 'prioritize',
                'protocol': 'udp'
            })
        elif any(re.search(p, message_lower) for p in self.patterns['security']):
            intent.update({
                'name': 'Security Enhancement',
                'policy': 'security',
                'priority': 70,
                'action': 'filter'
            })
        elif any(re.search(p, message_lower) for p in self.patterns['bandwidth']):
            intent.update({
                'name': 'Bandwidth Limit',
                'policy': 'bandwidth',
                'priority': 40,
                'action': 'limit',
                'bandwidth': '10mbps'
            })
        elif any(re.search(p, message_lower) for p in self.patterns['priority']):
            intent.update({
                'name': 'Traffic Prioritization',
                'policy': 'qos',
                'priority': 90,
                'action': 'prioritize'
            })
        
        logger.info(f"Parsed intent: {intent}")
        return intent
