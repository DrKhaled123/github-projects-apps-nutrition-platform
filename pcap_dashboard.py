#!/usr/bin/env python3
"""
Web Dashboard for Packet Capture Analysis
Provides real-time visualization and analysis of captured packets
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime
import glob
from packet_capture_setup import PacketCaptureSetup

class PCAPDashboard:
    def __init__(self):
        self.pcap_dir = "pcap"
        self.setup = PacketCaptureSetup(output_dir=self.pcap_dir)

    def load_pcap_files(self):
        """Load all PCAP files from the directory"""
        if not os.path.exists(self.pcap_dir):
            return []

        pcap_files = glob.glob(os.path.join(self.pcap_dir, "*.pcap"))
        return sorted(pcap_files, key=os.path.getmtime, reverse=True)

    def analyze_pcap_for_dashboard(self, pcap_file):
        """Analyze PCAP file for dashboard display"""
        try:
            analysis = self.setup.analyze_pcap(pcap_file)

            # Create visualizations
            return {
                'summary': {
                    'filename': os.path.basename(pcap_file),
                    'total_packets': analysis['packet_count'],
                    'duration': analysis['duration'],
                    'avg_packet_size': sum(analysis['packet_sizes']) / len(analysis['packet_sizes']) if analysis['packet_sizes'] else 0
                },
                'protocols': analysis['protocols'],
                'ip_addresses': analysis['ip_addresses'],
                'ports': analysis['ports'],
                'packet_sizes': analysis['packet_sizes']
            }
        except Exception as e:
            st.error(f"Error analyzing {pcap_file}: {e}")
            return None

    def create_protocol_chart(self, protocols):
        """Create protocol distribution chart"""
        if not protocols:
            return None

        df = pd.DataFrame(list(protocols.items()), columns=['Protocol', 'Count'])
        df = df.sort_values('Count', ascending=False)

        fig = px.pie(df, values='Count', names='Protocol',
                    title='Protocol Distribution',
                    color_discrete_sequence=px.colors.qualitative.Set3)
        return fig

    def create_ip_chart(self, ip_addresses):
        """Create IP address distribution chart"""
        if not ip_addresses:
            return None

        df = pd.DataFrame(list(ip_addresses.items()), columns=['IP Address', 'Count'])
        df = df.sort_values('Count', ascending=False).head(10)

        fig = px.bar(df, x='IP Address', y='Count',
                    title='Top 10 IP Addresses',
                    color='Count', color_continuous_scale='Viridis')
        fig.update_layout(xaxis_tickangle=-45)
        return fig

    def create_port_chart(self, ports):
        """Create port distribution chart"""
        if not ports:
            return None

        df = pd.DataFrame(list(ports.items()), columns=['Port', 'Count'])
        df = df.sort_values('Count', ascending=False).head(10)

        fig = px.bar(df, x='Port', y='Count',
                    title='Top 10 Ports',
                    color='Count', color_continuous_scale='Plasma')
        return fig

    def create_packet_size_histogram(self, packet_sizes):
        """Create packet size distribution histogram"""
        if not packet_sizes:
            return None

        df = pd.DataFrame(packet_sizes, columns=['Size'])

        fig = px.histogram(df, x='Size', title='Packet Size Distribution',
                          marginal='box', color_discrete_sequence=['#1f77b4'])
        return fig

    def run_dashboard(self):
        """Run the Streamlit dashboard"""
        st.set_page_config(page_title="Packet Capture Dashboard", layout="wide")

        st.title("🔍 Packet Capture Analysis Dashboard")
        st.markdown("Real-time packet capture analysis and visualization")

        # Sidebar
        st.sidebar.header("Configuration")
        pcap_files = self.load_pcap_files()

        if not pcap_files:
            st.sidebar.warning("No PCAP files found. Start a capture first!")
            selected_file = None
        else:
            selected_file = st.sidebar.selectbox(
                "Select PCAP File",
                pcap_files,
                format_func=lambda x: os.path.basename(x)
            )

        # Main content
        if selected_file:
            st.header(f"Analysis: {os.path.basename(selected_file)}")

            with st.spinner("Analyzing PCAP file..."):
                analysis_data = self.analyze_pcap_for_dashboard(selected_file)

            if analysis_data:
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Total Packets", f"{analysis_data['summary']['total_packets']:,}")
                with col2:
                    st.metric("Duration", f"{analysis_data['summary']['duration']".2f"}s")
                with col3:
                    st.metric("Avg Packet Size", f"{analysis_data['summary']['avg_packet_size']".0f"} bytes")
                with col4:
                    protocol_count = len(analysis_data['protocols'])
                    st.metric("Protocols", protocol_count)

                st.markdown("---")

                # Create charts
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Protocol Distribution")
                    protocol_fig = self.create_protocol_chart(analysis_data['protocols'])
                    if protocol_fig:
                        st.plotly_chart(protocol_fig, use_container_width=True)
                    else:
                        st.info("No protocol data available")

                with col2:
                    st.subheader("Top IP Addresses")
                    ip_fig = self.create_ip_chart(analysis_data['ip_addresses'])
                    if ip_fig:
                        st.plotly_chart(ip_fig, use_container_width=True)
                    else:
                        st.info("No IP address data available")

                # Second row
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Top Ports")
                    port_fig = self.create_port_chart(analysis_data['ports'])
                    if port_fig:
                        st.plotly_chart(port_fig, use_container_width=True)
                    else:
                        st.info("No port data available")

                with col2:
                    st.subheader("Packet Size Distribution")
                    size_fig = self.create_packet_size_histogram(analysis_data['packet_sizes'])
                    if size_fig:
                        st.plotly_chart(size_fig, use_container_width=True)
                    else:
                        st.info("No packet size data available")

                # Detailed tables
                st.markdown("---")
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Protocol Details")
                    if analysis_data['protocols']:
                        protocol_df = pd.DataFrame(
                            list(analysis_data['protocols'].items()),
                            columns=['Protocol', 'Count']
                        ).sort_values('Count', ascending=False)
                        st.dataframe(protocol_df, use_container_width=True)
                    else:
                        st.info("No protocol data available")

                with col2:
                    st.subheader("IP Address Details")
                    if analysis_data['ip_addresses']:
                        ip_df = pd.DataFrame(
                            list(analysis_data['ip_addresses'].items()),
                            columns=['IP Address', 'Count']
                        ).sort_values('Count', ascending=False)
                        st.dataframe(ip_df, use_container_width=True)
                    else:
                        st.info("No IP address data available")

        else:
            st.info("👈 Select a PCAP file from the sidebar to start analysis")

            # Show available files
            if pcap_files:
                st.subheader("Available PCAP Files")
                for pcap_file in pcap_files:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📄 {os.path.basename(pcap_file)}")
                    with col2:
                        if st.button("Analyze", key=pcap_file):
                            st.rerun()

        # Footer
        st.markdown("---")
        st.markdown("*Packet Capture Dashboard - Real-time network analysis and visualization*")

def main():
    dashboard = PCAPDashboard()
    dashboard.run_dashboard()

if __name__ == "__main__":
    main()
