#!/usr/bin/env python3
import os
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from groq import Groq

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(log_dir, 'controller.log'),
            maxBytes=1024*1024,
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConversationManager:
    def __init__(self):
        load_dotenv()
        self.use_llm = True  # FORCE Pure LLM mode - no rule-based fallback
        self.max_history = int(os.getenv('MAX_CHAT_HISTORY', 10))
        self.timeout = int(os.getenv('CONVERSATION_TIMEOUT', 300))
        self.conversations = {}
        self.groq_client = None

        # Force LLM mode - ignore .env setting
        logger.info("🤖 PURE LLM MODE - No rule-based parsing")

        try:
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                logger.error("❌ GROQ_API_KEY not set in .env")
                raise ValueError("GROQ_API_KEY not set in .env")
            
            self.groq_client = Groq(api_key=api_key)
            logger.info("✅ Groq LLM initialized successfully")
            
            # Test the connection
            self._test_groq_connection()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Groq: {e}")
            raise

        logger.info("✅ Conversation Manager initialized in PURE LLM-ONLY mode")

    def _test_groq_connection(self):
        """Test Groq API connection"""
        try:
            test_completion = self.groq_client.chat.completions.create(
                model=os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'),
                messages=[
                    {"role": "system", "content": "You are a test bot. Respond with 'OK'."},
                    {"role": "user", "content": "Test"}
                ],
                max_tokens=10
            )
            response = test_completion.choices[0].message.content
            logger.info(f"✅ Groq connection test successful: {response}")
        except Exception as e:
            logger.error(f"❌ Groq connection test failed: {e}")
            raise

    def process_message(self, user_id, message):
        """Process user message using Groq LLM ONLY"""
        try:
            if user_id not in self.conversations:
                self.conversations[user_id] = {
                    'history': [],
                    'last_active': time.time()
                }

            # Clean up old conversations
            self._cleanup_conversations()

            # Build conversation context
            context_messages = self._build_context(user_id, message)
            
            # Process with LLM
            response = self._process_with_llm(context_messages)
            
            # Parse and validate response
            parsed_response = self._parse_llm_response(response)
            
            # Update conversation history
            self.conversations[user_id]['history'].append({
                'user': message,
                'bot': parsed_response
            })
            
            # Trim history if needed
            if len(self.conversations[user_id]['history']) > self.max_history:
                self.conversations[user_id]['history'].pop(0)
            
            self.conversations[user_id]['last_active'] = time.time()
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}", exc_info=True)
            return json.dumps({
                "response": f"I apologize, but I encountered an error: {str(e)}. Please try again.",
                "action": "error"
            })

    def _build_context(self, user_id, message):
        """Build conversation context for LLM"""
        system_prompt = """You are an expert SDN (Software-Defined Networking) AI assistant. Your job is to translate natural language requests into network intents.

🎯 CRITICAL: You MUST respond with valid JSON. There are TWO phases:

**PHASE 1: PROPOSE (action: "propose")**
When user makes a request, PROPOSE the configuration and ask for confirmation:
{
  "response": "I'll configure [what]. This will [impact]. Should I proceed? (Reply 'yes' to confirm)",
  "action": "propose",
  "intent": {
    "name": "Descriptive name",
    "policy": "qos|security|gaming|bandwidth|routing|custom",
    "priority": 50-95,
    "protocol": "tcp|udp|both",
    "action": "prioritize|limit|block|allow",
    "bandwidth": "unlimited"
  }
}

**PHASE 2: APPLY (action: "apply")**
ONLY after user confirms with "yes", "proceed", "apply", "do it", etc:
{
  "response": "Applied! [What was configured]",
  "action": "apply",
  "intent": {... same intent object ...}
}

**SPECIAL ACTIONS:**
For "remove all intents", "clear all", "reset":
{
  "response": "I'll remove all network intents and reset to default. Should I proceed?",
  "action": "delete_all",
  "needs_confirmation": true
}

When confirmed:
{
  "response": "All intents removed. Network reset to default configuration.",
  "action": "delete_all_confirmed"
}

For information/questions:
{
  "response": "Your helpful response",
  "action": "info"
}

When need clarification:
{
  "response": "Your question",
  "action": "clarify"
}

📋 POLICY TYPES:
- "qos" → Video calls, streaming, VoIP
- "security" → Firewall, blocking, filtering
- "gaming" → Online gaming, low latency
- "bandwidth" → Limiting, capping, throttling
- "routing" → Path selection, load balancing
- "custom" → Other

🎚️ PRIORITY: 30-95 (higher = more important)

🔧 PROTOCOL:
- "udp" → Video, gaming, streaming
- "tcp" → Web, files, databases
- "both" → Security, general

⚡ ACTION:
- "prioritize" → Higher priority
- "limit" → Cap bandwidth
- "block" → Block traffic
- "allow" → Allow traffic

📝 EXAMPLES:

User: "Optimize for video calls"
{
  "response": "I'll configure a QoS policy to prioritize video call traffic (UDP). This ensures smooth video conferencing. Should I proceed? (Reply 'yes' to confirm)",
  "action": "propose",
  "intent": {
    "name": "Video Call Optimization",
    "policy": "qos",
    "priority": 85,
    "protocol": "udp",
    "action": "prioritize",
    "bandwidth": "unlimited"
  }
}

User: "yes"
{
  "response": "Applied! Video calls are now prioritized with QoS policy at priority 85.",
  "action": "apply",
  "intent": {
    "name": "Video Call Optimization",
    "policy": "qos",
    "priority": 85,
    "protocol": "udp",
    "action": "prioritize",
    "bandwidth": "unlimited"
  }
}

User: "remove all intents"
{
  "response": "I'll remove all existing network intents and reset to default configuration. Should I proceed?",
  "action": "delete_all",
  "needs_confirmation": true
}

User: "yes"
{
  "response": "All intents have been removed. Your network is now in its default state.",
  "action": "delete_all_confirmed"
}

🔒 CRITICAL RULES:
1. ALWAYS use "propose" first, NEVER "apply" immediately
2. ONLY use "apply" after user confirms
3. NEVER create intents for "remove/delete/clear" requests
4. Always ask "Should I proceed?" for configuration changes
5. Be conversational and explain impacts clearly

Remember: Users must confirm BEFORE applying any changes!"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 3 exchanges for context)
        if self.conversations[user_id]['history']:
            for hist in self.conversations[user_id]['history'][-3:]:
                messages.append({"role": "user", "content": hist['user']})
                # Extract just the text response for history
                bot_response = hist['bot']
                if isinstance(bot_response, str):
                    try:
                        bot_parsed = json.loads(bot_response)
                        bot_text = bot_parsed.get('response', bot_response)
                    except:
                        bot_text = bot_response
                else:
                    bot_text = bot_response.get('response', str(bot_response))
                messages.append({"role": "assistant", "content": bot_text})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        return messages

    def _process_with_llm(self, messages):
        """Process messages with Groq LLM"""
        try:
            logger.info(f"🤖 Sending to Groq with {len(messages)} messages")
            
            completion = self.groq_client.chat.completions.create(
                model=os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'),
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            
            response_content = completion.choices[0].message.content
            logger.info(f"✅ Received from Groq: {response_content[:150]}...")
            
            return response_content
            
        except Exception as e:
            logger.error(f"❌ Groq API error: {e}", exc_info=True)
            return json.dumps({
                "response": f"I'm having trouble connecting to the AI service. Error: {str(e)}",
                "action": "error"
            })

    def _parse_llm_response(self, response):
        """Parse and validate LLM response"""
        try:
            if not response or response.strip() == '':
                logger.error("❌ Empty response from LLM")
                return json.dumps({
                    "response": "I apologize, but I couldn't generate a response. Please try rephrasing.",
                    "action": "error"
                })
            
            # Parse JSON
            try:
                parsed = json.loads(response)
                
                # Validate structure
                if not isinstance(parsed, dict):
                    logger.error(f"❌ Response is not a dict: {type(parsed)}")
                    return json.dumps({
                        "response": str(parsed),
                        "action": "error"
                    })
                
                # Ensure 'response' field exists and is not empty
                if 'response' not in parsed or not parsed['response'] or parsed['response'] == 'undefined':
                    logger.warning("⚠️ Missing/invalid 'response' field")
                    parsed['response'] = "I received your message. How can I help you configure your network?"
                
                # Ensure 'action' field exists
                if 'action' not in parsed:
                    parsed['action'] = 'info'
                
                logger.info(f"✅ Parsed response - Action: {parsed['action']}, Policy: {parsed.get('intent', {}).get('policy', 'N/A')}")
                return json.dumps(parsed)
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parse error: {e}")
                logger.error(f"❌ Raw response: {response}")
                
                # Wrap raw text in proper JSON
                return json.dumps({
                    "response": response,
                    "action": "info"
                })
                
        except Exception as e:
            logger.error(f"❌ Error parsing LLM response: {e}", exc_info=True)
            return json.dumps({
                "response": "I encountered an error processing the response. Please try again.",
                "action": "error"
            })

    def _cleanup_conversations(self):
        """Remove expired conversations"""
        current_time = time.time()
        expired = [
            uid for uid, conv in self.conversations.items()
            if current_time - conv['last_active'] > self.timeout
        ]
        for uid in expired:
            del self.conversations[uid]
            logger.info(f"🧹 Cleaned up conversation for user {uid}")

    def get_conversation_history(self, user_id):
        """Return conversation history for a user"""
        return self.conversations.get(user_id, {}).get('history', [])

    def clear_conversation(self, user_id):
        """Clear conversation history for a user"""
        if user_id in self.conversations:
            del self.conversations[user_id]
            logger.info(f"🗑️ Cleared conversation for user {uid}")
            return True
        return False
