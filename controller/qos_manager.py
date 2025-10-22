#!/usr/bin/env python3
"""
QoS Manager for SDN Controller
Handles Quality of Service configurations
"""
import logging
import subprocess
import os

logger = logging.getLogger(__name__)

class QoSManager:
    """
    Manages Quality of Service settings
    """
    
    def __init__(self):
        self.qos_enabled = False
        self.interface = os.getenv('NETWORK_INTERFACE', 'eth0')
        logger.info(f"QoS Manager initialized for interface: {self.interface}")
    
    def setup_qos(self):
        """
        Setup QoS queues (Linux tc command)
        Note: Requires root privileges
        """
        try:
            logger.info("Attempting to setup QoS...")
            
            # Check if running as root
            if os.geteuid() != 0:
                logger.warning("⚠️ QoS setup requires root privileges, skipping...")
                return False
            
            # Clear existing qdisc
            subprocess.run(
                ['tc', 'qdisc', 'del', 'dev', self.interface, 'root'],
                stderr=subprocess.DEVNULL,
                check=False
            )
            
            # Add HTB qdisc
            subprocess.run(
                ['tc', 'qdisc', 'add', 'dev', self.interface, 'root', 'handle', '1:', 'htb'],
                check=True,
                capture_output=True
            )
            
            # Add root class
            subprocess.run(
                ['tc', 'class', 'add', 'dev', self.interface, 'parent', '1:', 
                 'classid', '1:1', 'htb', 'rate', '1000mbit'],
                check=True,
                capture_output=True
            )
            
            # Add priority classes
            # High priority (video, real-time)
            subprocess.run(
                ['tc', 'class', 'add', 'dev', self.interface, 'parent', '1:1',
                 'classid', '1:10', 'htb', 'rate', '500mbit', 'prio', '1'],
                check=True,
                capture_output=True
            )
            
            # Medium priority (web, database)
            subprocess.run(
                ['tc', 'class', 'add', 'dev', self.interface, 'parent', '1:1',
                 'classid', '1:20', 'htb', 'rate', '300mbit', 'prio', '2'],
                check=True,
                capture_output=True
            )
            
            # Low priority (background)
            subprocess.run(
                ['tc', 'class', 'add', 'dev', self.interface, 'parent', '1:1',
                 'classid', '1:30', 'htb', 'rate', '200mbit', 'prio', '3'],
                check=True,
                capture_output=True
            )
            
            self.qos_enabled = True
            logger.info("✅ QoS setup complete")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to setup QoS: {e}")
            logger.error(f"Error output: {e.stderr.decode() if e.stderr else 'N/A'}")
            return False
        except Exception as e:
            logger.error(f"❌ QoS setup error: {e}")
            return False
    
    def remove_qos(self):
        """
        Remove QoS configuration
        """
        try:
            if os.geteuid() == 0:
                subprocess.run(
                    ['tc', 'qdisc', 'del', 'dev', self.interface, 'root'],
                    stderr=subprocess.DEVNULL,
                    check=False
                )
                logger.info("✅ QoS removed")
            else:
                logger.warning("⚠️ QoS removal requires root privileges")
        except Exception as e:
            logger.error(f"❌ Error removing QoS: {e}")
    
    def apply_bandwidth_limit(self, classid, rate):
        """
        Apply bandwidth limit to a specific class
        """
        try:
            if not self.qos_enabled:
                logger.warning("⚠️ QoS not enabled, cannot apply bandwidth limit")
                return False
            
            if os.geteuid() != 0:
                logger.warning("⚠️ Bandwidth limit requires root privileges")
                return False
            
            subprocess.run(
                ['tc', 'class', 'change', 'dev', self.interface,
                 'parent', '1:1', 'classid', f'1:{classid}',
                 'htb', 'rate', rate],
                check=True,
                capture_output=True
            )
            
            logger.info(f"✅ Applied bandwidth limit: {rate} to class {classid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply bandwidth limit: {e}")
            return False
    
    def get_qos_stats(self):
        """
        Get QoS statistics
        """
        try:
            if not self.qos_enabled:
                return None
            
            result = subprocess.run(
                ['tc', '-s', 'class', 'show', 'dev', self.interface],
                capture_output=True,
                text=True,
                check=True
            )
            
            return result.stdout
            
        except Exception as e:
            logger.error(f"❌ Failed to get QoS stats: {e}")
            return None
