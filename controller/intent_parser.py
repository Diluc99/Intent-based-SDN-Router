"""
Intent Parser - Natural Language to Network Policy
Converts human-readable intents to technical configurations
"""

import re
import json
from typing import Dict, List, Tuple
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from fuzzywuzzy import fuzz
from textblob import TextBlob
import logging

logger = logging.getLogger(__name__)

class IntentParser:
    def __init__(self):
        """Initialize the intent parser with knowledge base"""
        
        # Intent categories and their keywords
        self.intent_categories = {
            'performance': {
                'keywords': ['fast', 'speed', 'quick', 'priority', 'accelerate', 
                            'optimize', 'boost', 'improve', 'enhance', 'faster',
                            'prioritize', 'expedite', 'urgent', 'important'],
                'policy': 'QoS Priority',
                'priority': 100,
                'bandwidth': '5000 Mbps'
            },
            'security': {
                'keywords': ['secure', 'protect', 'safe', 'encrypt', 'block',
                            'prevent', 'guard', 'defend', 'shield', 'firewall',
                            'deny', 'restrict', 'control', 'authenticate'],
                'policy': 'SSL Inspection',
                'priority': 90,
                'bandwidth': 'unlimited'
            },
            'limit': {
                'keywords': ['limit', 'restrict', 'slow', 'reduce', 'throttle',
                            'cap', 'constraint', 'guest', 'minimal', 'conserve',
                            'save', 'bandwidth'],
                'policy': 'Traffic Shaping',
                'priority': 10,
                'bandwidth': '100 Mbps'
            },
            'balance': {
                'keywords': ['balance', 'distribute', 'share', 'spread',
                            'load', 'equal', 'fair', 'divide', 'allocate'],
                'policy': 'Load Balance',
                'priority': 50,
                'bandwidth': '10000 Mbps'
            },
            'reliability': {
                'keywords': ['reliable', 'stable', 'consistent', 'backup',
                            'failover', 'redundant', 'always', 'available',
                            'uptime', 'resilient'],
                'policy': 'QoS Priority',
                'priority': 80,
                'bandwidth': '3000 Mbps'
            }
        }
        
        # Application patterns
        self.applications = {
            'video': {
                'keywords': ['video', 'streaming', 'youtube', 'netflix', 
                            'zoom', 'teams', 'meet', 'webex', 'conference',
                            'call', 'facetime'],
                'protocols': ['TCP/443', 'UDP/3478-3497', 'TCP/5060-5061'],
                'bandwidth': '5000 Mbps',
                'latency': 'low',
                'jitter': 'low'
            },
            'web': {
                'keywords': ['web', 'website', 'http', 'https', 'browser',
                            'internet', 'surf', 'browse'],
                'protocols': ['TCP/80', 'TCP/443'],
                'bandwidth': '2000 Mbps',
                'latency': 'medium',
                'jitter': 'high'
            },
            'database': {
                'keywords': ['database', 'db', 'sql', 'mysql', 'postgres',
                            'oracle', 'mongodb', 'data'],
                'protocols': ['TCP/3306', 'TCP/5432', 'TCP/1521', 'TCP/27017'],
                'bandwidth': '3000 Mbps',
                'latency': 'low',
                'jitter': 'low'
            },
            'email': {
                'keywords': ['email', 'mail', 'smtp', 'imap', 'pop3',
                            'outlook', 'gmail'],
                'protocols': ['TCP/25', 'TCP/587', 'TCP/993', 'TCP/995'],
                'bandwidth': '500 Mbps',
                'latency': 'medium',
                'jitter': 'high'
            },
            'backup': {
                'keywords': ['backup', 'sync', 'replication', 'copy',
                            'archive', 'snapshot'],
                'protocols': ['TCP/22', 'TCP/873', 'TCP/3260'],
                'bandwidth': '1000 Mbps',
                'latency': 'high',
                'jitter': 'high'
            },
            'voip': {
                'keywords': ['voice', 'voip', 'phone', 'sip', 'call'],
                'protocols': ['UDP/5060', 'UDP/5061', 'UDP/10000-20000'],
                'bandwidth': '1000 Mbps',
                'latency': 'very_low',
                'jitter': 'very_low'
            },
            'gaming': {
                'keywords': ['game', 'gaming', 'multiplayer', 'steam'],
                'protocols': ['UDP/27015-27030', 'TCP/27015-27030'],
                'bandwidth': '2000 Mbps',
                'latency': 'very_low',
                'jitter': 'low'
            }
        }
        
        # User roles and priorities
        self.user_roles = {
            'ceo': 100,
            'executive': 95,
            'manager': 80,
            'employee': 50,
            'guest': 10,
            'admin': 90,
            'it': 85
        }
        
        # Time-based adjustments
        self.time_modifiers = {
            'urgent': 1.2,
            'immediate': 1.3,
            'critical': 1.5,
            'low_priority': 0.7,
            'background': 0.5
        }
        
        logger.info("Intent Parser initialized with knowledge base")
    
    def parse_intent(self, user_input: str, context: Dict = None) -> Dict:
        """
        Main function to parse natural language intent
        
        Args:
            user_input: Natural language string from user
            context: Additional context (user role, time, network state)
            
        Returns:
            Dict with parsed intent and recommended policies
        """
        logger.info(f"Parsing intent: '{user_input}'")
        
        # Clean and tokenize input
        cleaned_text = self._clean_text(user_input)
        tokens = word_tokenize(cleaned_text.lower())
        
        # Remove stopwords
        stop_words = set(stopwords.words('english'))
        filtered_tokens = [w for w in tokens if w not in stop_words]
        
        # Analyze sentiment
        sentiment = self._analyze_sentiment(user_input)
        
        # Detect intent category
        category = self._detect_category(filtered_tokens)
        
        # Detect application
        application = self._detect_application(filtered_tokens)
        
        # Extract entities (bandwidth, protocols, etc.)
        entities = self._extract_entities(user_input)
        
        # Apply context
        if context:
            category = self._apply_context(category, context)
        
        # Generate policy configuration
        policy_config = self._generate_policy(
            category=category,
            application=application,
            entities=entities,
            sentiment=sentiment,
            context=context
        )
        
        # Generate human-readable explanation
        explanation = self._generate_explanation(policy_config)
        
        result = {
            'original_input': user_input,
            'cleaned_input': cleaned_text,
            'detected_category': category,
            'detected_application': application,
            'sentiment': sentiment,
            'entities': entities,
            'policy_config': policy_config,
            'explanation': explanation,
            'confidence': self._calculate_confidence(category, application)
        }
        
        logger.info(f"Intent parsed: category={category}, confidence={result['confidence']}")
        return result
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize input text"""
        # Convert to lowercase
        text = text.lower()
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^a-zA-Z0-9\s\.\,\!\?]', '', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text
    
    def _analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment to understand urgency/importance"""
        blob = TextBlob(text)
        sentiment = blob.sentiment
        
        return {
            'polarity': sentiment.polarity,  # -1 to 1
            'subjectivity': sentiment.subjectivity,  # 0 to 1
            'urgency': 'high' if sentiment.polarity > 0.5 else 'medium' if sentiment.polarity > 0 else 'low'
        }
    
    def _detect_category(self, tokens: List[str]) -> str:
        """Detect intent category based on keywords"""
        scores = {}
        
        for category, data in self.intent_categories.items():
            score = 0
            for token in tokens:
                for keyword in data['keywords']:
                    # Use fuzzy matching for flexibility
                    similarity = fuzz.ratio(token, keyword)
                    if similarity > 80:  # 80% similarity threshold
                        score += similarity
            scores[category] = score
        
        # Return category with highest score
        if scores:
            best_category = max(scores, key=scores.get)
            if scores[best_category] > 0:
                return best_category
        
        return 'performance'  # Default category
    
    def _detect_application(self, tokens: List[str]) -> str:
        """Detect application type from keywords"""
        scores = {}
        
        for app, data in self.applications.items():
            score = 0
            for token in tokens:
                for keyword in data['keywords']:
                    similarity = fuzz.ratio(token, keyword)
                    if similarity > 80:
                        score += similarity
            scores[app] = score
        
        if scores:
            best_app = max(scores, key=scores.get)
            if scores[best_app] > 0:
                return best_app
        
        return 'web'  # Default application
    
    def _extract_entities(self, text: str) -> Dict:
        """Extract specific entities like bandwidth, IPs, ports"""
        entities = {}
        
        # Extract bandwidth (e.g., "5000 Mbps", "1 Gbps")
        bandwidth_pattern = r'(\d+)\s*(mbps|gbps|kbps)'
        bandwidth_match = re.search(bandwidth_pattern, text.lower())
        if bandwidth_match:
            value = int(bandwidth_match.group(1))
            unit = bandwidth_match.group(2)
            if unit == 'gbps':
                value *= 1000
            elif unit == 'kbps':
                value /= 1000
            entities['bandwidth'] = f"{int(value)} Mbps"
        
        # Extract IP addresses
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ips = re.findall(ip_pattern, text)
        if ips:
            entities['ips'] = ips
        
        # Extract ports
        port_pattern = r'port\s+(\d+)'
        ports = re.findall(port_pattern, text.lower())
        if ports:
            entities['ports'] = ports
        
        # Extract priority indicators
        if any(word in text.lower() for word in ['high', 'critical', 'urgent']):
            entities['priority_level'] = 'high'
        elif any(word in text.lower() for word in ['low', 'background']):
            entities['priority_level'] = 'low'
        
        return entities
    
    def _apply_context(self, category: str, context: Dict) -> str:
        """Apply contextual information to refine intent"""
        # Check user role
        if 'user_role' in context:
            role = context['user_role'].lower()
            if role in ['ceo', 'executive'] and category == 'performance':
                # VIPs always get highest priority
                return 'performance'
        
        # Check time of day
        if 'time' in context:
            hour = context['time'].hour
            # Business hours (9 AM - 5 PM)
            if 9 <= hour <= 17:
                if category == 'backup':
                    # Delay backups during business hours
                    return 'limit'
        
        # Check network load
        if 'network_load' in context:
            if context['network_load'] > 0.8:  # 80% utilization
                if category == 'performance':
                    # Apply more aggressive QoS during high load
                    return 'performance'
        
        return category
    
    def _generate_policy(self, category: str, application: str, 
                        entities: Dict, sentiment: Dict, context: Dict = None) -> Dict:
        """Generate complete policy configuration"""
        
        # Start with category defaults
        cat_data = self.intent_categories[category]
        app_data = self.applications.get(application, {})
        
        # Base configuration
        config = {
            'name': f"Auto: {category.title()} for {application.title()}",
            'policy': cat_data['policy'],
            'priority': cat_data['priority'],
            'bandwidth': entities.get('bandwidth', cat_data['bandwidth']),
            'application': application,
            'protocols': app_data.get('protocols', []),
            'auto_generated': True
        }
        
        # Adjust priority based on sentiment
        if sentiment['urgency'] == 'high':
            config['priority'] = min(100, config['priority'] + 10)
        elif sentiment['urgency'] == 'low':
            config['priority'] = max(1, config['priority'] - 10)
        
        # Adjust based on context
        if context:
            # User role adjustment
            if 'user_role' in context:
                role_priority = self.user_roles.get(context['user_role'].lower(), 50)
                config['priority'] = max(config['priority'], role_priority)
                config['user_role'] = context['user_role']
            
            # Time-based adjustment
            if 'time_modifier' in context:
                modifier = self.time_modifiers.get(context['time_modifier'], 1.0)
                config['priority'] = int(config['priority'] * modifier)
        
        # Application-specific tuning
        if application in self.applications:
            app_config = self.applications[application]
            config['latency_requirement'] = app_config.get('latency', 'medium')
            config['jitter_requirement'] = app_config.get('jitter', 'medium')
        
        # Add QoS parameters based on application
        if config['latency_requirement'] == 'very_low':
            config['qos_class'] = 'EF'  # Expedited Forwarding
            config['max_latency_ms'] = 20
        elif config['latency_requirement'] == 'low':
            config['qos_class'] = 'AF41'  # Assured Forwarding
            config['max_latency_ms'] = 50
        else:
            config['qos_class'] = 'BE'  # Best Effort
            config['max_latency_ms'] = 200
        
        return config
    
    def _generate_explanation(self, policy_config: Dict) -> str:
        """Generate human-readable explanation of what will be done"""
        explanations = []
        
        # Main action
        policy = policy_config['policy']
        app = policy_config['application']
        priority = policy_config['priority']
        
        explanations.append(
            f"I will apply '{policy}' policy for {app} traffic."
        )
        
        # Priority explanation
        if priority >= 90:
            explanations.append(
                f"This will get the highest priority (level {priority}) in the network."
            )
        elif priority >= 70:
            explanations.append(
                f"This will get high priority (level {priority}) in the network."
            )
        elif priority >= 40:
            explanations.append(
                f"This will get medium priority (level {priority}) in the network."
            )
        else:
            explanations.append(
                f"This will get lower priority (level {priority}) to save bandwidth for critical traffic."
            )
        
        # Bandwidth explanation
        bandwidth = policy_config['bandwidth']
        if bandwidth != 'unlimited':
            if policy == 'Traffic Shaping':
                explanations.append(
                    f"Bandwidth will be limited to {bandwidth}."
                )
            else:
                explanations.append(
                    f"Up to {bandwidth} bandwidth will be reserved for this traffic."
                )
        
        # Protocol explanation
        if policy_config.get('protocols'):
            protocols = ', '.join(policy_config['protocols'])
            explanations.append(
                f"This will affect traffic on protocols: {protocols}."
            )
        
        # QoS explanation
        if 'qos_class' in policy_config:
            qos = policy_config['qos_class']
            latency = policy_config.get('max_latency_ms', 'N/A')
            explanations.append(
                f"Traffic will be marked with QoS class '{qos}' with maximum latency of {latency}ms."
            )
        
        return ' '.join(explanations)
    
    def _calculate_confidence(self, category: str, application: str) -> float:
        """Calculate confidence score for the intent detection"""
        # Simple confidence calculation
        # In production, this would be more sophisticated
        confidence = 0.8  # Base confidence
        
        if category in self.intent_categories:
            confidence += 0.1
        
        if application in self.applications:
            confidence += 0.1
        
        return min(1.0, confidence)

