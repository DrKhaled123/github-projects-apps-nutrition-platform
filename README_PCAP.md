# 🔍 Packet Capture and Analysis System

A comprehensive packet capture and analysis system with real-time visualization, automated analysis, and web-based dashboard.

## 🌟 Features

- **Real-time Packet Capture**: Capture network traffic using tcpdump
- **Automated Analysis**: Extract protocols, IP addresses, ports, and packet statistics
- **Web Dashboard**: Interactive visualization using Streamlit and Plotly
- **Multiple Interfaces**: Support for different network interfaces
- **BPF Filtering**: Advanced packet filtering capabilities
- **Export Capabilities**: Save reports and analysis results
- **Cross-platform**: Works on macOS and Linux

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Examples](#examples)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🚀 Quick Start

1. **Install Dependencies**
   ```bash
   chmod +x setup_pcap_environment.sh
   ./setup_pcap_environment.sh
   ```

2. **Start Packet Capture**
   ```bash
   ./start_capture.sh -i lo0 -d 60  # Capture for 60 seconds on loopback
   ```

3. **Launch Dashboard**
   ```bash
   ./start_dashboard.sh
   ```
   Open http://localhost:8501 in your browser

4. **Analyze Existing Capture**
   ```bash
   ./analyze_pcap.sh pcap/capture_20231201_120000.pcap
   ```

## 📦 Installation

### Prerequisites

- **Python 3.8+**: Required for the analysis tools
- **tcpdump**: For packet capture (usually pre-installed)
- **Wireshark/tshark**: For advanced packet analysis
- **Network Access**: Appropriate permissions for packet capture

### Automated Installation

Run the setup script to automatically install all dependencies:

```bash
./setup_pcap_environment.sh
```

This script will:
- Detect your operating system (macOS/Linux)
- Install system dependencies (tcpdump, wireshark)
- Create a Python virtual environment
- Install all required Python packages
- Set up necessary directories and permissions
- Create convenience scripts

### Manual Installation

1. **Install System Dependencies**

   **macOS:**
   ```bash
   brew install tcpdump wireshark
   ```

   **Ubuntu/Debian:**
   ```bash
   sudo apt-get update
   sudo apt-get install tcpdump tshark wireshark
   ```

   **CentOS/RHEL:**
   ```bash
   sudo yum install tcpdump wireshark
   ```

2. **Set Up Python Environment**

   ```bash
   python3 -m venv venv_pcap
   source venv_pcap/bin/activate
   pip install --upgrade pip
   pip install -r requirements-pcap.txt
   playwright install
   ```

3. **Set Permissions**

   **Linux:**
   ```bash
   sudo usermod -a -G wireshark $USER
   # Or run captures with sudo
   ```

   **macOS:**
   - Go to System Preferences > Security & Privacy > Privacy > Monitoring
   - Allow terminal access for packet capture

## 🎯 Usage

### Command Line Interface

#### Basic Capture

```bash
# Capture all traffic for 60 seconds
./start_capture.sh -d 60

# Capture HTTP traffic only
./start_capture.sh -f "tcp port 80 or tcp port 8080"

# Capture on specific interface
./start_capture.sh -i en0 -d 30

# Continuous capture (Ctrl+C to stop)
./start_capture.sh -i lo0
```

#### Analysis

```bash
# Analyze existing PCAP file
./analyze_pcap.sh capture.pcap

# Get detailed protocol breakdown
python3 packet_capture_setup.py --analyze capture.pcap
```

#### Configuration

```bash
# Create default configuration
python3 packet_capture_setup.py --create-config

# Custom interface and output directory
python3 packet_capture_setup.py -i en0 -o /path/to/captures
```

### Web Dashboard

1. **Start the dashboard**
   ```bash
   ./start_dashboard.sh
   ```

2. **Access the interface**
   - Open http://localhost:8501
   - Select a PCAP file from the sidebar
   - View real-time analysis and visualizations

3. **Dashboard Features**
   - Protocol distribution charts
   - IP address analysis
   - Port usage statistics
   - Packet size distributions
   - Detailed data tables

### Python API

```python
from packet_capture_setup import PacketCaptureSetup
from pcap_dashboard import PCAPDashboard

# Initialize capture system
setup = PacketCaptureSetup(interface="lo0", output_dir="pcap")

# Start capture
pcap_file = setup.start_capture(duration=60, filter_expr="tcp port 80")

# Analyze results
analysis = setup.analyze_pcap(pcap_file)
report = setup.generate_report(analysis)

# Launch dashboard
dashboard = PCAPDashboard()
# Dashboard runs as web application
```

## ⚙️ Configuration

### Configuration File

The system creates a `pcap/capture_config.json` file with the following structure:

```json
{
  "interface": "lo0",
  "output_directory": "pcap",
  "default_filters": {
    "http": "tcp port 80 or tcp port 8080",
    "https": "tcp port 443",
    "dns": "udp port 53",
    "ssh": "tcp port 22"
  },
  "analysis_settings": {
    "enable_protocol_analysis": true,
    "enable_ip_analysis": true,
    "enable_port_analysis": true,
    "max_packets_for_analysis": 10000
  }
}
```

### BPF Filter Expressions

Use Berkeley Packet Filter (BPF) syntax for advanced filtering:

```bash
# HTTP traffic
"tcp port 80 or tcp port 8080"

# HTTPS traffic
"tcp port 443"

# DNS queries
"udp port 53"

# Specific IP range
"net 192.168.1.0/24"

# TCP SYN packets only
"tcp[tcpflags] & tcp-syn != 0"

# ICMP packets
"icmp"

# ARP packets
"arp"

# Specific host communication
"host 192.168.1.100"

# Port range
"tcp portrange 8000-9000"
```

## 💡 Examples

### Network Traffic Analysis

```bash
# Monitor web server traffic
./start_capture.sh -f "tcp port 80 or tcp port 443" -d 300

# Analyze DNS queries
./start_capture.sh -f "udp port 53" -d 60

# Monitor SSH connections
./start_capture.sh -f "tcp port 22" -d 120
```

### Security Monitoring

```bash
# Capture suspicious traffic
./start_capture.sh -f "tcp port 23 or tcp port 2323" -d 600

# Monitor for unusual port activity
./start_capture.sh -f "tcp port not 80 and tcp port not 443 and tcp port not 22" -d 300
```

### Performance Analysis

```bash
# Capture during load test
./start_capture.sh -i eth0 -d 180

# Monitor database connections
./start_capture.sh -f "tcp port 3306 or tcp port 5432 or tcp port 27017" -d 60
```

### Automated Reporting

```python
import schedule
import time
from packet_capture_setup import PacketCaptureSetup

def daily_capture():
    setup = PacketCaptureSetup()
    pcap_file = setup.start_capture(duration=3600)  # 1 hour
    analysis = setup.analyze_pcap(pcap_file)
    report = setup.generate_report(analysis)

    # Save to timestamped file
    timestamp = time.strftime("%Y%m%d")
    with open(f"reports/daily_report_{timestamp}.txt", 'w') as f:
        f.write(report)

# Schedule daily at 2 AM
schedule.every().day.at("02:00").do(daily_capture)

while True:
    schedule.run_pending()
    time.sleep(3600)
```

## 📊 Dashboard Features

### Real-time Metrics
- Total packet count
- Capture duration
- Average packet size
- Protocol diversity

### Visualizations
- **Protocol Distribution**: Pie chart showing protocol breakdown
- **IP Address Analysis**: Bar chart of top communicating hosts
- **Port Usage**: Horizontal bar chart of most active ports
- **Packet Size Distribution**: Histogram with size analysis

### Data Tables
- Detailed protocol statistics
- IP address frequency tables
- Port activity breakdowns
- Packet size distributions

## 🔧 API Reference

### PacketCaptureSetup Class

#### Methods

- `__init__(interface="lo0", output_dir="pcap")`: Initialize capture system
- `check_dependencies() -> bool`: Verify all tools are installed
- `start_capture(duration=None, filter_expr="") -> str`: Start packet capture
- `stop_capture()`: Stop current capture
- `analyze_pcap(pcap_file: str) -> Dict`: Analyze PCAP file
- `generate_report(analysis: Dict) -> str`: Generate human-readable report
- `create_capture_config() -> str`: Create default configuration file

#### Parameters

- `interface`: Network interface to capture from (default: "lo0")
- `output_dir`: Directory to save PCAP files (default: "pcap")
- `duration`: Capture duration in seconds (optional, continuous if None)
- `filter_expr`: BPF filter expression for packet filtering

### PCAPDashboard Class

#### Methods

- `__init__()`: Initialize dashboard
- `load_pcap_files() -> List[str]`: Get list of available PCAP files
- `analyze_pcap_for_dashboard(pcap_file: str) -> Dict`: Analyze for dashboard display
- `run_dashboard()`: Launch Streamlit dashboard

## 🚨 Troubleshooting

### Common Issues

#### Permission Denied
```bash
# Linux
sudo usermod -a -G wireshark $USER
# Or run with sudo
sudo ./start_capture.sh

# macOS
# Go to System Preferences > Security & Privacy > Privacy > Monitoring
# Allow terminal access
```

#### No Packets Captured
```bash
# Check available interfaces
tcpdump -D

# Test with loopback
./start_capture.sh -i lo0 -d 10

# Check if interface exists
ifconfig  # or ip addr
```

#### Wireshark/tshark Not Found
```bash
# macOS
brew install wireshark

# Ubuntu/Debian
sudo apt-get install tshark

# CentOS/RHEL
sudo yum install wireshark
```

#### Python Dependencies Issues
```bash
# Recreate virtual environment
rm -rf venv_pcap
python3 -m venv venv_pcap
source venv_pcap/bin/activate
pip install -r requirements-pcap.txt
```

#### Dashboard Not Loading
```bash
# Check if port 8501 is available
lsof -i :8501

# Kill conflicting process
kill -9 <PID>

# Or use different port
streamlit run pcap_dashboard.py --server.port 8502
```

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or run with verbose output
./start_capture.sh -v
```

### Performance Issues

For high-traffic networks:

```bash
# Use sampling
tcpdump -i eth0 -w capture.pcap -s 96  # Smaller packets

# Filter early
./start_capture.sh -f "tcp port 80"  # Only HTTP

# Limit analysis scope
# Edit capture_config.json to reduce max_packets_for_analysis
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd packet-capture-system

# Set up development environment
./setup_pcap_environment.sh

# Activate virtual environment
source venv_pcap/bin/activate

# Run tests
python3 -m pytest tests/

# Run linting
flake8 packet_capture_setup.py pcap_dashboard.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [tcpdump](https://www.tcpdump.org/) for packet capture
- [Wireshark](https://www.wireshark.org/) for packet analysis
- [Streamlit](https://streamlit.io/) for the web dashboard
- [Plotly](https://plotly.com/) for data visualization

## 📞 Support

For support and questions:

- 📧 Email: support@packetanalysis.dev
- 💬 Discord: [Join our community](https://discord.gg/packetanalysis)
- 🐛 Issues: [GitHub Issues](https://github.com/username/packet-capture-system/issues)
- 📖 Wiki: [Documentation](https://github.com/username/packet-capture-system/wiki)

---

**Made with ❤️ for network analysts and security professionals**
