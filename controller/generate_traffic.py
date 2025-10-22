#!/usr/bin/env python3
"""
Network Traffic Generator for SDN Controller Testing
Simulates realistic network traffic patterns
"""
import time
import random
import sys
from datetime import datetime

class TrafficGenerator:
    def __init__(self):
        self.flows = [
            {'src': '10.0.0.1', 'dst': '10.0.0.2', 'protocol': 'TCP', 'port': 80, 'type': 'Web'},
            {'src': '10.0.0.2', 'dst': '10.0.0.3', 'protocol': 'UDP', 'port': 443, 'type': 'HTTPS'},
            {'src': '10.0.0.3', 'dst': '10.0.0.1', 'protocol': 'TCP', 'port': 22, 'type': 'SSH'},
            {'src': '10.0.0.1', 'dst': '10.0.0.3', 'protocol': 'UDP', 'port': 53, 'type': 'DNS'},
            {'src': '10.0.0.2', 'dst': '10.0.0.1', 'protocol': 'TCP', 'port': 3306, 'type': 'MySQL'},
        ]
        
        self.total_packets = 0
        self.total_bytes = 0
    
    def generate_burst(self):
        """Generate a burst of traffic"""
        burst_size = random.randint(100, 2000)
        selected_flows = random.sample(self.flows, k=random.randint(2, len(self.flows)))
        
        print(f"\n{'='*70}")
        print(f"⚡ Traffic Burst at {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*70}")
        
        for flow in selected_flows:
            packets = random.randint(burst_size // len(selected_flows), burst_size)
            avg_packet_size = random.randint(64, 1500)  # Bytes
            bytes_count = packets * avg_packet_size
            
            self.total_packets += packets
            self.total_bytes += bytes_count
            
            # Calculate throughput for this flow
            mbps = (bytes_count * 8) / (1024 * 1024)  # Convert to Mbps
            
            print(f"📤 {flow['type']:8} | {flow['src']} → {flow['dst']} | "
                  f"{flow['protocol']:4} port {flow['port']:5} | "
                  f"{packets:5} pkts | {bytes_count/1024:7.1f} KB | {mbps:6.2f} Mbps")
    
    def print_stats(self):
        """Print cumulative statistics"""
        total_mb = self.total_bytes / (1024 * 1024)
        print(f"\n{'─'*70}")
        print(f"📊 Cumulative Stats: {self.total_packets:,} packets | "
              f"{total_mb:.2f} MB transferred")
        print(f"{'─'*70}")
    
    def run(self, duration=None, interval=2):
        """
        Run traffic generator
        
        Args:
            duration: Run for specified seconds (None = infinite)
            interval: Seconds between bursts
        """
        print("\n" + "="*70)
        print("🚦 SDN Traffic Generator Started")
        print("="*70)
        print(f"⏱️  Interval: {interval}s between bursts")
        if duration:
            print(f"⏰ Duration: {duration}s")
        else:
            print(f"⏰ Duration: Infinite (Press Ctrl+C to stop)")
        print(f"📡 Simulating {len(self.flows)} network flows")
        print("="*70)
        
        start_time = time.time()
        burst_count = 0
        
        try:
            while True:
                if duration and (time.time() - start_time) >= duration:
                    break
                
                self.generate_burst()
                burst_count += 1
                
                if burst_count % 5 == 0:
                    self.print_stats()
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping traffic generator...")
        
        finally:
            elapsed = time.time() - start_time
            avg_throughput = (self.total_bytes * 8) / (elapsed * 1024 * 1024)
            
            print("\n" + "="*70)
            print("📊 Final Statistics")
            print("="*70)
            print(f"⏱️  Runtime: {elapsed:.1f} seconds")
            print(f"📦 Total Packets: {self.total_packets:,}")
            print(f"💾 Total Data: {self.total_bytes / (1024*1024):.2f} MB")
            print(f"📈 Average Throughput: {avg_throughput:.2f} Mbps")
            print(f"🔥 Bursts Generated: {burst_count}")
            print("="*70)
            print("\n✅ Traffic generation complete")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Network Traffic Generator for SDN Testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Run for 60 seconds with 2s interval
  python3 generate_traffic.py -d 60 -i 2
  
  # Run indefinitely with 1s interval
  python3 generate_traffic.py -i 1
  
  # Quick test (30 seconds, fast)
  python3 generate_traffic.py -d 30 -i 0.5
        '''
    )
    
    parser.add_argument('-d', '--duration', type=int, default=None,
                        help='Duration in seconds (default: infinite)')
    parser.add_argument('-i', '--interval', type=float, default=2.0,
                        help='Interval between bursts in seconds (default: 2.0)')
    
    args = parser.parse_args()
    
    generator = TrafficGenerator()
    generator.run(duration=args.duration, interval=args.interval)

if __name__ == '__main__':
    main()