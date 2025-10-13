#!/bin/bash

# Packet Capture Environment Setup Script
# This script installs all required dependencies for the packet capture system

set -e

echo "🔧 Setting up Packet Capture Environment..."
echo "============================================="

# Check if we're on macOS or Linux
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📱 Detected macOS system"
    PACKAGE_MANAGER="brew"
    INSTALL_CMD="brew install"
    UPDATE_CMD="brew update"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Detected Linux system"
    if command -v apt-get &> /dev/null; then
        PACKAGE_MANAGER="apt"
        INSTALL_CMD="sudo apt-get install -y"
        UPDATE_CMD="sudo apt-get update"
    elif command -v yum &> /dev/null; then
        PACKAGE_MANAGER="yum"
        INSTALL_CMD="sudo yum install -y"
        UPDATE_CMD="sudo yum update -y"
    else
        echo "❌ Unsupported Linux distribution"
        exit 1
    fi
else
    echo "❌ Unsupported operating system: $OSTYPE"
    exit 1
fi

echo "📦 Installing system dependencies..."

# Install tcpdump and wireshark (includes tshark)
if [[ "$PACKAGE_MANAGER" == "brew" ]]; then
    $INSTALL_CMD tcpdump wireshark || {
        echo "⚠️  Wireshark installation might require additional setup"
        echo "   You may need to install it manually from: https://www.wireshark.org/download.html"
    }
elif [[ "$PACKAGE_MANAGER" == "apt" ]]; then
    $UPDATE_CMD
    $INSTALL_CMD tcpdump tshark wireshark || {
        echo "⚠️  Wireshark installation might require additional setup"
        echo "   You may need to install it manually from: https://www.wireshark.org/download.html"
    }
elif [[ "$PACKAGE_MANAGER" == "yum" ]]; then
    $INSTALL_CMD tcpdump wireshark || {
        echo "⚠️  Wireshark installation might require additional setup"
        echo "   You may need to install it manually from: https://www.wireshark.org/download.html"
    }
fi

# Check Python version
echo "🐍 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "   Please install Python 3.8 or higher from https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
echo "✅ Python $PYTHON_VERSION detected"

# Create virtual environment if it doesn't exist
if [[ ! -d "venv_pcap" ]]; then
    echo "🏗️  Creating virtual environment..."
    python3 -m venv venv_pcap
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv_pcap/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📚 Installing Python packages..."
pip install -r requirements-pcap.txt

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p pcap
mkdir -p logs
mkdir -p reports

# Set permissions for packet capture
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🔒 Setting permissions for macOS..."
    # On macOS, we might need to allow tcpdump in System Preferences > Security & Privacy > Privacy > Monitoring
    echo "ℹ️  Note: You may need to allow terminal access to capture packets in System Preferences"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🔒 Setting permissions for Linux..."
    # Check if user is in wireshark group or has sudo access
    if groups | grep -q wireshark || sudo -n true 2>/dev/null; then
        echo "✅ Packet capture permissions OK"
    else
        echo "⚠️  You may need to run with sudo for packet capture"
        echo "   Or add your user to the 'wireshark' group: sudo usermod -a -G wireshark $USER"
    fi
fi

# Create configuration file if it doesn't exist
if [[ ! -f "pcap/capture_config.json" ]]; then
    echo "⚙️  Creating default configuration..."
    python3 packet_capture_setup.py --create-config
fi

# Test the installation
echo "🧪 Testing installation..."
python3 -c "
import packet_capture_setup
import pcap_dashboard
print('✅ All imports successful!')
"

# Create startup scripts
echo "📝 Creating startup scripts..."

cat > start_capture.sh << 'EOF'
#!/bin/bash
source venv_pcap/bin/activate
echo "Starting packet capture..."
python3 packet_capture_setup.py "$@"
EOF

cat > start_dashboard.sh << 'EOF'
#!/bin/bash
source venv_pcap/bin/activate
echo "Starting packet capture dashboard..."
streamlit run pcap_dashboard.py
EOF

cat > analyze_pcap.sh << 'EOF'
#!/bin/bash
source venv_pcap/bin/activate
if [ $# -eq 0 ]; then
    echo "Usage: $0 <pcap_file>"
    exit 1
fi
echo "Analyzing $1..."
python3 packet_capture_setup.py --analyze "$1"
EOF

chmod +x start_capture.sh start_dashboard.sh analyze_pcap.sh

echo ""
echo "🎉 Packet Capture Environment Setup Complete!"
echo "============================================="
echo ""
echo "📋 Available commands:"
echo "  ./start_capture.sh     - Start packet capture"
echo "  ./start_dashboard.sh   - Launch web dashboard"
echo "  ./analyze_pcap.sh      - Analyze existing PCAP file"
echo ""
echo "🐍 Usage examples:"
echo "  ./start_capture.sh -i lo0 -d 60                    # Capture for 60 seconds"
echo "  ./start_capture.sh -f 'tcp port 80'               # Capture HTTP traffic"
echo "  ./analyze_pcap.sh pcap/capture_20231201_120000.pcap  # Analyze file"
echo ""
echo "🌐 Dashboard will be available at: http://localhost:8501"
echo ""
echo "📖 For more information, see the README.md file"
echo ""

# Deactivate virtual environment
deactivate
