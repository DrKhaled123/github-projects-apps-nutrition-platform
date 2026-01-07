#!/usr/bin/env python3
"""
System Automation MCP Server
Provides tools for automatic control of applications, monitoring, desktop management, and browser automation
"""

import json
import subprocess
import sys
import os
import asyncio
import logging
import time
import psutil
import signal
from typing import Any, Dict, List, Optional
from pathlib import Path
import tempfile
import shutil

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemAutomationServer:
    """MCP server for system automation and control"""

    def __init__(self):
        self.name = "system-automation"
        self.tools = self._register_tools()
        self.running_processes = {}  # Track processes we started

    def _register_tools(self) -> List[Dict[str, Any]]:
        """Register available system automation tools"""
        return [
            {
                "name": "run_application",
                "description": "Launch an application or executable",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Command or application path to run"
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Command arguments",
                            "default": []
                        },
                        "working_directory": {
                            "type": "string",
                            "description": "Working directory for the command"
                        },
                        "background": {
                            "type": "boolean",
                            "description": "Run in background",
                            "default": True
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds",
                            "default": 30
                        }
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "monitor_processes",
                "description": "Monitor running processes and system resources",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "process_name": {
                            "type": "string",
                            "description": "Filter by process name"
                        },
                        "pid": {
                            "type": "integer",
                            "description": "Monitor specific process by PID"
                        },
                        "include_system_info": {
                            "type": "boolean",
                            "description": "Include system resource information",
                            "default": True
                        }
                    }
                }
            },
            {
                "name": "stop_process",
                "description": "Stop a running process",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pid": {
                            "type": "integer",
                            "description": "Process ID to stop"
                        },
                        "process_name": {
                            "type": "string",
                            "description": "Process name to stop (stops first match)"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force kill the process",
                            "default": False
                        }
                    }
                }
            },
            {
                "name": "execute_task",
                "description": "Execute a general system task or command",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Command to execute"
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Command arguments"
                        },
                        "working_directory": {
                            "type": "string",
                            "description": "Working directory"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds",
                            "default": 60
                        }
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "manage_files",
                "description": "File system operations (copy, move, delete)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "enum": ["copy", "move", "delete", "list", "create_dir"],
                            "description": "File operation"
                        },
                        "source": {
                            "type": "string",
                            "description": "Source path"
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination path (for copy/move)"
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Recursive operation",
                            "default": False
                        }
                    },
                    "required": ["operation"]
                }
            },
            {
                "name": "browser_automation",
                "description": "Automate browser operations using Selenium",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "enum": ["navigate", "click", "type", "screenshot", "get_text", "wait"],
                            "description": "Browser action"
                        },
                        "url": {
                            "type": "string",
                            "description": "URL to navigate to"
                        },
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for element"
                        },
                        "text": {
                            "type": "string",
                            "description": "Text to type or search for"
                        },
                        "wait_seconds": {
                            "type": "integer",
                            "description": "Wait time in seconds",
                            "default": 5
                        },
                        "browser": {
                            "enum": ["chrome", "firefox", "safari"],
                            "description": "Browser to use",
                            "default": "chrome"
                        }
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "desktop_management",
                "description": "Manage desktop windows and applications",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "enum": ["list_windows", "focus_window", "minimize_window", "close_window", "get_active_window"],
                            "description": "Desktop action"
                        },
                        "window_title": {
                            "type": "string",
                            "description": "Window title to target"
                        },
                        "window_id": {
                            "type": "string",
                            "description": "Window ID to target"
                        }
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "system_health_check",
                "description": "Check system health and resource usage",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "check_type": {
                            "enum": ["cpu", "memory", "disk", "network", "all"],
                            "description": "Type of health check",
                            "default": "all"
                        },
                        "alert_thresholds": {
                            "type": "object",
                            "description": "Custom alert thresholds"
                        }
                    }
                }
            }
        ]

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return list of available tools"""
        return self.tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the specified tool with given arguments"""
        try:
            if name == "run_application":
                return await self._run_application(arguments)
            elif name == "monitor_processes":
                return await self._monitor_processes(arguments)
            elif name == "stop_process":
                return await self._stop_process(arguments)
            elif name == "execute_task":
                return await self._execute_task(arguments)
            elif name == "manage_files":
                return await self._manage_files(arguments)
            elif name == "browser_automation":
                return await self._browser_automation(arguments)
            elif name == "desktop_management":
                return await self._desktop_management(arguments)
            elif name == "system_health_check":
                return await self._system_health_check(arguments)
            else:
                return {"error": f"Unknown tool: {name}"}

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return {"error": f"Tool execution failed: {str(e)}"}

    async def _run_application(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Launch an application or executable"""
        command = args["command"]
        cmd_args = args.get("args", [])
        working_dir = args.get("working_directory")
        background = args.get("background", True)
        timeout = args.get("timeout", 30)

        # Security check - prevent dangerous commands
        dangerous_commands = ['rm', 'del', 'format', 'fdisk', 'mkfs', 'dd', 'sudo', 'su']
        if any(dangerous in command.lower() for dangerous in dangerous_commands):
            return {"error": "Dangerous command blocked for safety"}

        full_cmd = [command] + cmd_args

        try:
            if background:
                # Run in background
                process = subprocess.Popen(
                    full_cmd,
                    cwd=working_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.running_processes[process.pid] = {
                    "command": full_cmd,
                    "start_time": time.time(),
                    "process": process
                }

                return {
                    "success": True,
                    "pid": process.pid,
                    "command": full_cmd,
                    "background": True,
                    "message": f"Application started in background with PID {process.pid}"
                }
            else:
                # Run synchronously with timeout
                process = await asyncio.create_subprocess_exec(
                    *full_cmd,
                    cwd=working_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )

                    return {
                        "success": process.returncode == 0,
                        "exit_code": process.returncode,
                        "stdout": stdout.decode('utf-8', errors='replace'),
                        "stderr": stderr.decode('utf-8', errors='replace'),
                        "command": full_cmd
                    }

                except asyncio.TimeoutError:
                    process.kill()
                    return {
                        "success": False,
                        "error": f"Command timed out after {timeout} seconds",
                        "command": full_cmd
                    }

        except FileNotFoundError:
            return {"error": f"Command not found: {command}"}
        except Exception as e:
            return {"error": f"Failed to run application: {str(e)}"}

    async def _monitor_processes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor running processes"""
        process_name = args.get("process_name")
        pid = args.get("pid")
        include_system_info = args.get("include_system_info", True)

        result = {
            "processes": [],
            "system_info": {}
        }

        try:
            if pid:
                # Monitor specific process
                try:
                    proc = psutil.Process(pid)
                    result["processes"].append(self._get_process_info(proc))
                except psutil.NoSuchProcess:
                    return {"error": f"Process with PID {pid} not found"}
            else:
                # Monitor all processes or filter by name
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                    try:
                        if process_name and process_name.lower() not in proc.info['name'].lower():
                            continue

                        result["processes"].append(self._get_process_info(proc))

                        # Limit results to prevent overwhelming output
                        if len(result["processes"]) >= 50:
                            result["truncated"] = True
                            break

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            if include_system_info:
                result["system_info"] = {
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory": psutil.virtual_memory()._asdict(),
                    "disk": psutil.disk_usage('/')._asdict(),
                    "network": psutil.net_io_counters()._asdict()
                }

            return result

        except Exception as e:
            return {"error": f"Failed to monitor processes: {str(e)}"}

    def _get_process_info(self, proc: psutil.Process) -> Dict[str, Any]:
        """Get detailed process information"""
        try:
            return {
                "pid": proc.pid,
                "name": proc.name(),
                "cpu_percent": proc.cpu_percent(),
                "memory_percent": proc.memory_percent(),
                "status": proc.status(),
                "create_time": proc.create_time(),
                "cmdline": proc.cmdline() if proc.cmdline() else [],
                "exe": proc.exe() if proc.exe() else ""
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"pid": proc.pid, "error": "Access denied or process terminated"}

    async def _stop_process(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Stop a running process"""
        pid = args.get("pid")
        process_name = args.get("process_name")
        force = args.get("force", False)

        try:
            if pid:
                # Stop by PID
                proc = psutil.Process(pid)
                if force:
                    proc.kill()
                else:
                    proc.terminate()

                return {
                    "success": True,
                    "pid": pid,
                    "action": "killed" if force else "terminated",
                    "message": f"Process {pid} {'killed' if force else 'terminated'}"
                }

            elif process_name:
                # Stop by name (first match)
                for proc in psutil.process_iter(['pid', 'name']):
                    if process_name.lower() in proc.info['name'].lower():
                        if force:
                            proc.kill()
                        else:
                            proc.terminate()

                        return {
                            "success": True,
                            "pid": proc.pid,
                            "name": proc.info['name'],
                            "action": "killed" if force else "terminated",
                            "message": f"Process {proc.info['name']} (PID {proc.pid}) {'killed' if force else 'terminated'}"
                        }

                return {"error": f"No process found with name containing '{process_name}'"}

            else:
                return {"error": "Either pid or process_name must be specified"}

        except psutil.NoSuchProcess:
            return {"error": f"Process not found"}
        except Exception as e:
            return {"error": f"Failed to stop process: {str(e)}"}

    async def _execute_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a general system task"""
        command = args["command"]
        cmd_args = args.get("args", [])
        working_dir = args.get("working_directory")
        timeout = args.get("timeout", 60)

        # Security check
        dangerous_commands = ['rm', 'del', 'format', 'fdisk', 'mkfs', 'dd', 'sudo', 'su']
        if any(dangerous in command.lower() for dangerous in dangerous_commands):
            return {"error": "Dangerous command blocked for safety"}

        full_cmd = [command] + cmd_args

        try:
            process = await asyncio.create_subprocess_exec(
                *full_cmd,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return {
                "success": process.returncode == 0,
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "command": full_cmd
            }

        except asyncio.TimeoutError:
            process.kill()
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "command": full_cmd
            }
        except Exception as e:
            return {"error": f"Failed to execute task: {str(e)}"}

    async def _manage_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """File system operations"""
        operation = args["operation"]
        source = args.get("source")
        destination = args.get("destination")
        recursive = args.get("recursive", False)

        try:
            if operation == "copy":
                if not source or not destination:
                    return {"error": "Source and destination required for copy"}
                if os.path.isdir(source) and recursive:
                    shutil.copytree(source, destination)
                else:
                    shutil.copy2(source, destination)
                return {"success": True, "operation": "copy", "source": source, "destination": destination}

            elif operation == "move":
                if not source or not destination:
                    return {"error": "Source and destination required for move"}
                shutil.move(source, destination)
                return {"success": True, "operation": "move", "source": source, "destination": destination}

            elif operation == "delete":
                if not source:
                    return {"error": "Source required for delete"}
                if os.path.isdir(source) and recursive:
                    shutil.rmtree(source)
                else:
                    os.remove(source)
                return {"success": True, "operation": "delete", "path": source}

            elif operation == "list":
                if not source:
                    source = "."
                if os.path.isdir(source):
                    items = os.listdir(source)
                    return {"success": True, "operation": "list", "path": source, "items": items}
                else:
                    return {"error": f"Path is not a directory: {source}"}

            elif operation == "create_dir":
                if not source:
                    return {"error": "Path required for create_dir"}
                os.makedirs(source, exist_ok=True)
                return {"success": True, "operation": "create_dir", "path": source}

            else:
                return {"error": f"Unsupported operation: {operation}"}

        except Exception as e:
            return {"error": f"File operation failed: {str(e)}"}

    async def _browser_automation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Browser automation using Selenium"""
        action = args["action"]

        # This is a simplified implementation - in practice you'd use selenium
        # For now, we'll use curl for basic operations

        try:
            if action == "navigate":
                url = args.get("url")
                if not url:
                    return {"error": "URL required for navigate"}
                # Use curl to test navigation
                result = await self._execute_task({
                    "command": "curl",
                    "args": ["-s", "-I", url],
                    "timeout": 10
                })
                return {
                    "success": result.get("success", False),
                    "action": "navigate",
                    "url": url,
                    "result": result
                }

            elif action == "screenshot":
                # Placeholder - would use selenium with webdriver
                return {
                    "success": False,
                    "action": "screenshot",
                    "message": "Screenshot functionality requires Selenium WebDriver setup"
                }

            else:
                return {"error": f"Unsupported browser action: {action}"}

        except Exception as e:
            return {"error": f"Browser automation failed: {str(e)}"}

    async def _desktop_management(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Desktop window management"""
        action = args["action"]

        try:
            if action == "list_windows":
                # On macOS, use osascript or other tools
                if sys.platform == "darwin":
                    result = await self._execute_task({
                        "command": "osascript",
                        "args": ["-e", 'tell application "System Events" to get name of every window of every process']
                    })
                    return {
                        "success": result.get("success", False),
                        "action": "list_windows",
                        "windows": result.get("stdout", "").split(", ") if result.get("stdout") else []
                    }
                else:
                    return {"error": "Desktop management not implemented for this platform"}

            elif action == "get_active_window":
                if sys.platform == "darwin":
                    result = await self._execute_task({
                        "command": "osascript",
                        "args": ["-e", 'tell application "System Events" to get name of first window of (first process whose frontmost is true)']
                    })
                    return {
                        "success": result.get("success", False),
                        "action": "get_active_window",
                        "active_window": result.get("stdout", "").strip()
                    }
                else:
                    return {"error": "Desktop management not implemented for this platform"}

            else:
                return {"error": f"Unsupported desktop action: {action}"}

        except Exception as e:
            return {"error": f"Desktop management failed: {str(e)}"}

    async def _system_health_check(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check system health and resources"""
        check_type = args.get("check_type", "all")
        alert_thresholds = args.get("alert_thresholds", {})

        result = {
            "timestamp": time.time(),
            "checks": {},
            "alerts": []
        }

        try:
            if check_type in ["cpu", "all"]:
                cpu_percent = psutil.cpu_percent(interval=1)
                result["checks"]["cpu"] = {
                    "usage_percent": cpu_percent,
                    "cores": psutil.cpu_count()
                }

                threshold = alert_thresholds.get("cpu_percent", 90)
                if cpu_percent > threshold:
                    result["alerts"].append(f"High CPU usage: {cpu_percent}% (threshold: {threshold}%)")

            if check_type in ["memory", "all"]:
                memory = psutil.virtual_memory()
                result["checks"]["memory"] = {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory.percent
                }

                threshold = alert_thresholds.get("memory_percent", 90)
                if memory.percent > threshold:
                    result["alerts"].append(f"High memory usage: {memory.percent}% (threshold: {threshold}%)")

            if check_type in ["disk", "all"]:
                disk = psutil.disk_usage('/')
                result["checks"]["disk"] = {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": disk.percent
                }

                threshold = alert_thresholds.get("disk_percent", 90)
                if disk.percent > threshold:
                    result["alerts"].append(f"High disk usage: {disk.percent}% (threshold: {threshold}%)")

            if check_type in ["network", "all"]:
                network = psutil.net_io_counters()
                result["checks"]["network"] = {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }

            result["overall_health"] = "healthy" if not result["alerts"] else "warning"
            return result

        except Exception as e:
            return {"error": f"Health check failed: {str(e)}"}

def main():
    """Main function to run the MCP server"""
    server = SystemAutomationServer()

    # Simple stdio server implementation
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line.strip())

            if request.get("method") == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {"tools": server.list_tools()}
                }

            elif request.get("method") == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                # Run the tool
                result = asyncio.run(server.call_tool(tool_name, arguments))

                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
                }

            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {"code": -32601, "message": "Method not found"}
                }

            print(json.dumps(response))
            sys.stdout.flush()

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id", None),
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    main()