#!/usr/bin/env python3
"""
Demonstration script for the Packet Capture and Analysis System
Shows various features and capabilities of the system
"""

import os
import sys
import time
import json
from datetime import datetime
from packet_capture_setup import PacketCaptureSetup
from pcap_dashboard import PCAPDashboard

def demo_basic_capture():
    """Demonstrate basic packet capture functionality"""
    print("🔍 Demo: Basic Packet Capture")
    print("=" * 50)

    setup = PacketCaptureSetup(interface="lo0", output_dir="pcap")

    print("📡 Starting 10-second packet capture on loopback interface...")
    pcap_file = setup.start_capture(duration=10)

    if pcap_file and os.path.exists(pcap_file):
        print(f"✅ Capture completed: {pcap_file}")

        print("\n📊 Analyzing captured packets...")
        analysis = setup.analyze_pcap(pcap_file)

        print("📈 Analysis Results:")
        print(f"   Total Packets: {analysis['packet_count']}")
        print(f"   Protocols Found: {len(analysis['protocols'])}")
        print(f"   Unique IPs: {len(analysis['ip_addresses'])}")
        print(f"   Unique Ports: {len(analysis['ports'])}")

        if analysis['protocols']:
            top_protocol = max(analysis['protocols'].items(), key=lambda x: x[1])
            print(f"   Top Protocol: {top_protocol[0]} ({top_protocol[1]} packets)")

        return pcap_file
    else:
        print("❌ Capture failed or no packets captured")
        return None

def demo_filtered_capture():
    """Demonstrate filtered packet capture"""
    print("\n🌐 Demo: Filtered Packet Capture (HTTP/HTTPS)")
    print("=" * 50)

    setup = PacketCaptureSetup(interface="lo0", output_dir="pcap")

    # Filter for HTTP and HTTPS traffic
    filter_expr = "tcp port 80 or tcp port 443 or tcp port 8080"

    print(f"🔍 Starting 15-second filtered capture: {filter_expr}")
    pcap_file = setup.start_capture(duration=15, filter_expr=filter_expr)

    if pcap_file and os.path.exists(pcap_file):
        print(f"✅ Filtered capture completed: {pcap_file}")

        analysis = setup.analyze_pcap(pcap_file)
        report = setup.generate_report(analysis)

        print("\n📋 Filtered Capture Report:")
        print("=" * 60)
        print(report[:1000] + "..." if len(report) > 1000 else report)

        return pcap_file
    else:
        print("❌ Filtered capture failed")
        return None

def demo_configuration():
    """Demonstrate configuration management"""
    print("\n⚙️  Demo: Configuration Management")
    print("=" * 50)

    setup = PacketCaptureSetup()

    print("🔧 Creating configuration file...")
    config_file = setup.create_capture_config()

    if os.path.exists(config_file):
        print(f"✅ Configuration created: {config_file}")

        # Load and display configuration
        with open(config_file, 'r') as f:
            config = json.load(f)

        print("\n📋 Configuration Contents:")
        print(f"   Interface: {config['interface']}")
        print(f"   Output Directory: {config['output_directory']}")
        print(f"   Available Filters: {len(config['default_filters'])}")
        print(f"   HTTP Filter: {config['default_filters']['http']}")
        print(f"   HTTPS Filter: {config['default_filters']['https']}")

        return config_file
    else:
        print("❌ Configuration creation failed")
        return None

def demo_dashboard():
    """Demonstrate dashboard functionality"""
    print("\n📊 Demo: Dashboard Analysis")
    print("=" * 50)

    dashboard = PCAPDashboard()

    # Get list of available PCAP files
    pcap_files = dashboard.load_pcap_files()

    if not pcap_files:
        print("⚠️  No PCAP files found for dashboard demo")
        print("   Run a capture first, then try the dashboard")
        return None

    print(f"📁 Found {len(pcap_files)} PCAP files")

    # Analyze the most recent file
    latest_file = pcap_files[0]
    print(f"📈 Analyzing latest file: {os.path.basename(latest_file)}")

    analysis_data = dashboard.analyze_pcap_for_dashboard(latest_file)

    if analysis_data:
        print("✅ Dashboard analysis completed")
        print("\n📋 Dashboard Summary:")
        summary = analysis_data['summary']
        print(f"   Filename: {summary['filename']}")
        print(f"   Total Packets: {summary['total_packets']:,}")
","
        print(f"   Duration: {summary['duration']".2f"} seconds")
        print(f"   Average Packet Size: {summary['avg_packet_size']".0f"} bytes")
        print(f"   Protocols: {len(analysis_data['protocols'])}")
        print(f"   IP Addresses: {len(analysis_data['ip_addresses'])}")
        print(f"   Ports: {len(analysis_data['ports'])}")

        return latest_file
    else:
        print("❌ Dashboard analysis failed")
        return None

def demo_error_handling():
    """Demonstrate error handling capabilities"""
    print("\n🛡️  Demo: Error Handling")
    print("=" * 50)

    setup = PacketCaptureSetup()

    # Test with non-existent file
    print("🔍 Testing analysis of non-existent file...")
    try:
        analysis = setup.analyze_pcap("non_existent_file.pcap")
        print("❌ Should have failed!")
    except FileNotFoundError as e:
        print(f"✅ Correctly caught error: {e}")

    # Test dependency checking
    print("\n🔧 Testing dependency checking...")
    deps_ok = setup.check_dependencies()
    if deps_ok:
        print("✅ All dependencies are available")
    else:
        print("⚠️  Some dependencies are missing (this is expected in demo)")

def demo_performance():
    """Demonstrate performance with larger captures"""
    print("\n⚡ Demo: Performance Analysis")
    print("=" * 50)

    setup = PacketCaptureSetup()

    print("📊 Creating a larger sample capture for performance testing...")
    print("🔍 This would normally capture 30 seconds of traffic")

    # In a real scenario, this would capture actual traffic
    # For demo purposes, we'll simulate with existing data if available
    pcap_files = [f for f in os.listdir("pcap") if f.endswith(".pcap")]

    if pcap_files:
        largest_file = max(pcap_files, key=lambda f: os.path.getsize(os.path.join("pcap", f)))
        file_path = os.path.join("pcap", largest_file)

        print(f"📈 Analyzing largest file: {largest_file}")
        start_time = time.time()

        analysis = setup.analyze_pcap(file_path)

        end_time = time.time()
        analysis_time = end_time - start_time

        print("✅ Performance Analysis Results:"        print(f"   Analysis Time: {analysis_time:.".2f"econds")
        print(f"   Packets Analyzed: {analysis['packet_count']:,}")
","
        print(f"   Packets/Second: {analysis['packet_count']/analysis_time:",.0f"}")

        if analysis['packet_count'] > 0:
            print(f"   Average Processing Speed: {analysis_time/analysis['packet_count']*1000".2f"}ms per packet")
    else:
        print("⚠️  No PCAP files available for performance demo")

def main():
    """Run all demonstrations"""
    print("🚀 Packet Capture System Demonstration")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Run demonstrations
    demo_basic_capture()
    demo_filtered_capture()
    demo_configuration()
    demo_dashboard()
    demo_error_handling()
    demo_performance()

    print("\n🎉 Demonstration Complete!")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("   1. Run './setup_pcap_environment.sh' to install dependencies")
    print("   2. Run './start_capture.sh -d 60' to capture packets")
    print("   3. Run './start_dashboard.sh' to launch the web interface")
    print("   4. Open http://localhost:8501 to view the dashboard")
    print("\n📖 See README_PCAP.md for detailed documentation")

if __name__ == "__main__":
    main()
