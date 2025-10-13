#!/usr/bin/env python3
"""
Comprehensive Packet Capture and Analysis Setup
Creates a powerful packet capture environment with analysis capabilities
"""

import subprocess
import os
import sys
import json
import time
from datetime import datetime
import argparse
import signal
import threading
from typing import Dict, List, Optional
import socket
import struct

class PacketCaptureSetup:
    def __init__(self, interface: str = "lo0", output_dir: str = "pcap"):
        self.interface = interface
        self.output_dir = output_dir
        self.capture_process = None
        self.analysis_thread = None
        self.is_capturing = False

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def check_dependencies(self) -> bool:
        """Check if required tools are installed"""
        required_tools = ['tcpdump', 'tshark', 'wireshark']
        missing_tools = []

        for tool in required_tools:
            if not self._check_command_exists(tool):
                missing_tools.append(tool)

        if missing_tools:
            print(f"Missing required tools: {', '.join(missing_tools)}")
            print("Please install them using:")
            print("  brew install tcpdump wireshark" if sys.platform == "darwin" else "  sudo apt install tcpdump tshark wireshark")
            return False

        return True

    def _check_command_exists(self, command: str) -> bool:
        """Check if a command exists in the system"""
        try:
            subprocess.run([command, '--version'], capture_output=True, timeout=5)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            return False

    def start_capture(self, duration: Optional[int] = None, filter_expr: str = "") -> str:
        """Start packet capture"""
        if not self.check_dependencies():
            raise RuntimeError("Required dependencies not installed")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.pcap"
        filepath = os.path.join(self.output_dir, filename)

        # Build tcpdump command
        cmd = ['tcpdump', '-i', self.interface, '-w', filepath]

        if filter_expr:
            cmd.extend(['-s', '0', filter_expr])  # -s 0 captures full packets

        print(f"Starting packet capture: {filepath}")
        print(f"Command: {' '.join(cmd)}")

        try:
            if duration:
                # Use timeout for limited duration capture
                self.capture_process = subprocess.run(cmd + ['-G', str(duration), '-W', '1'])
            else:
                # Continuous capture until manually stopped
                self.capture_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.is_capturing = True

                # Set up signal handler for graceful shutdown
                def signal_handler(signum, frame):
                    self.stop_capture()
                    sys.exit(0)

                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)

                # Wait for the process
                self.capture_process.wait()

        except KeyboardInterrupt:
            self.stop_capture()
        except Exception as e:
            print(f"Error during capture: {e}")
            self.stop_capture()

        return filepath

    def stop_capture(self):
        """Stop the current packet capture"""
        if self.capture_process and self.is_capturing:
            print("Stopping packet capture...")
            self.capture_process.terminate()
            try:
                self.capture_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.capture_process.kill()
                self.capture_process.wait()
            self.is_capturing = False
            print("Packet capture stopped.")

    def analyze_pcap(self, pcap_file: str) -> Dict:
        """Analyze a PCAP file and return statistics"""
        if not os.path.exists(pcap_file):
            raise FileNotFoundError(f"PCAP file not found: {pcap_file}")

        analysis = {
            'filename': pcap_file,
            'timestamp': datetime.now().isoformat(),
            'packet_count': 0,
            'protocols': {},
            'ip_addresses': {},
            'ports': {},
            'packet_sizes': [],
            'duration': 0
        }

        try:
            # Get basic packet count and info
            result = subprocess.run(['tshark', '-r', pcap_file, '-T', 'fields',
                                   '-e', 'frame.number', '-e', 'frame.time_relative',
                                   '-e', 'ip.src', '-e', 'ip.dst', '-e', 'tcp.srcport',
                                   '-e', 'tcp.dstport', '-e', 'udp.srcport', '-e', 'udp.dstport',
                                   '-e', 'frame.protocols', '-e', 'frame.len'],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                analysis['packet_count'] = len(lines)

                for line in lines:
                    if not line.strip():
                        continue

                    fields = line.split('\t')
                    if len(fields) >= 8:
                        # Count protocols
                        protocols = fields[7].split(':')
                        for protocol in protocols:
                            analysis['protocols'][protocol] = analysis['protocols'].get(protocol, 0) + 1

                        # Count IP addresses
                        src_ip = fields[2] if len(fields) > 2 and fields[2] else 'unknown'
                        dst_ip = fields[3] if len(fields) > 3 and fields[3] else 'unknown'

                        if src_ip != 'unknown':
                            analysis['ip_addresses'][src_ip] = analysis['ip_addresses'].get(src_ip, 0) + 1
                        if dst_ip != 'unknown':
                            analysis['ip_addresses'][dst_ip] = analysis['ip_addresses'].get(dst_ip, 0) + 1

                        # Count ports
                        src_port = self._extract_port(fields, 4, 6)  # TCP or UDP src port
                        dst_port = self._extract_port(fields, 5, 7)  # TCP or UDP dst port

                        if src_port:
                            analysis['ports'][src_port] = analysis['ports'].get(src_port, 0) + 1
                        if dst_port:
                            analysis['ports'][dst_port] = analysis['ports'].get(dst_port, 0) + 1

                        # Packet sizes
                        try:
                            packet_size = int(fields[8]) if len(fields) > 8 and fields[8] else 0
                            if packet_size > 0:
                                analysis['packet_sizes'].append(packet_size)
                        except (ValueError, IndexError):
                            pass

                # Calculate duration if we have time info
                if lines and len(lines[0].split('\t')) > 1:
                    try:
                        start_time = float(lines[0].split('\t')[1])
                        end_time = float(lines[-1].split('\t')[1])
                        analysis['duration'] = end_time - start_time
                    except (ValueError, IndexError):
                        pass

        except subprocess.TimeoutExpired:
            print("Analysis timed out, using partial results")
        except Exception as e:
            print(f"Error during analysis: {e}")

        return analysis

    def _extract_port(self, fields: List[str], tcp_idx: int, udp_idx: int) -> Optional[str]:
        """Extract port number from TCP or UDP fields"""
        try:
            if len(fields) > tcp_idx and fields[tcp_idx]:
                return fields[tcp_idx]
            if len(fields) > udp_idx and fields[udp_idx]:
                return fields[udp_idx]
        except (ValueError, IndexError):
            pass
        return None

    def generate_report(self, analysis: Dict) -> str:
        """Generate a human-readable report from analysis"""
        report = []
        report.append("=" * 60)
        report.append("PACKET CAPTURE ANALYSIS REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {analysis['timestamp']}")
        report.append(f"File: {analysis['filename']}")
        report.append("")

        report.append("SUMMARY:")
        report.append(f"  Total Packets: {analysis['packet_count']}")
        report.append(f"  Duration: {analysis['duration']".2f"} seconds")
        report.append(f"  Average Packet Size: {sum(analysis['packet_sizes'])/len(analysis['packet_sizes'])".0f"} bytes" if analysis['packet_sizes'] else "  Average Packet Size: N/A")
        report.append("")

        report.append("PROTOCOLS:")
        for protocol, count in sorted(analysis['protocols'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / analysis['packet_count']) * 100 if analysis['packet_count'] > 0 else 0
            report.append(f"  {protocol}: {count} packets ({percentage".1f"}%)")
        report.append("")

        report.append("TOP IP ADDRESSES:")
        for ip, count in sorted(analysis['ip_addresses'].items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / analysis['packet_count']) * 100 if analysis['packet_count'] > 0 else 0
            report.append(f"  {ip}: {count} packets ({percentage".1f"}%)")
        report.append("")

        report.append("TOP PORTS:")
        for port, count in sorted(analysis['ports'].items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / analysis['packet_count']) * 100 if analysis['packet_count'] > 0 else 0
            report.append(f"  {port}: {count} packets ({percentage".1f"}%)")

        return '\n'.join(report)

    def create_capture_config(self) -> str:
        """Create a configuration file for packet capture settings"""
        config = {
            "interface": self.interface,
            "output_directory": self.output_dir,
            "default_filters": {
                "http": "tcp port 80 or tcp port 8080",
                "https": "tcp port 443",
                "dns": "udp port 53",
                "ssh": "tcp port 22",
                "ftp": "tcp port 21",
                "smtp": "tcp port 25",
                "pop3": "tcp port 110",
                "imap": "tcp port 143"
            },
            "analysis_settings": {
                "enable_protocol_analysis": True,
                "enable_ip_analysis": True,
                "enable_port_analysis": True,
                "max_packets_for_analysis": 10000
            }
        }

        config_file = os.path.join(self.output_dir, "capture_config.json")
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        return config_file

def main():
    parser = argparse.ArgumentParser(description="Packet Capture and Analysis Tool")
    parser.add_argument('-i', '--interface', default='lo0', help='Network interface to capture from')
    parser.add_argument('-o', '--output-dir', default='pcap', help='Output directory for PCAP files')
    parser.add_argument('-d', '--duration', type=int, help='Capture duration in seconds')
    parser.add_argument('-f', '--filter', help='BPF filter expression')
    parser.add_argument('-a', '--analyze', help='Analyze existing PCAP file')
    parser.add_argument('--create-config', action='store_true', help='Create configuration file')

    args = parser.parse_args()

    setup = PacketCaptureSetup(args.interface, args.output_dir)

    if args.create_config:
        config_file = setup.create_capture_config()
        print(f"Configuration file created: {config_file}")
        return

    if args.analyze:
        print(f"Analyzing PCAP file: {args.analyze}")
        analysis = setup.analyze_pcap(args.analyze)
        report = setup.generate_report(analysis)
        print(report)

        # Save report to file
        report_file = args.analyze + "_analysis.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"Report saved to: {report_file}")
        return

    # Start packet capture
    print(f"Packet Capture Setup - Interface: {args.interface}")
    print(f"Output Directory: {args.output_dir}")
    print("=" * 50)

    try:
        pcap_file = setup.start_capture(duration=args.duration, filter_expr=args.filter)
        print(f"\nPacket capture completed: {pcap_file}")

        # Analyze the captured file
        if pcap_file and os.path.exists(pcap_file):
            print(f"\nAnalyzing captured file...")
            analysis = setup.analyze_pcap(pcap_file)
            report = setup.generate_report(analysis)
            print(report)

            # Save report
            report_file = pcap_file + "_analysis.txt"
            with open(report_file, 'w') as f:
                f.write(report)
            print(f"Analysis report saved to: {report_file}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
