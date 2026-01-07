#!/usr/bin/env python3
"""
Hybrid Deployment Framework with MCP
Combines Model Context Protocol with traditional CLI tools for comprehensive deployment and API access
"""

import json
import subprocess
import sys
import os
import asyncio
import logging
import requests
from typing import Any, Dict, List, Optional
import base64

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HybridDeploymentServer:
    """MCP server for hybrid deployment framework"""
    
    def __init__(self):
        self.name = "hybrid-deployment"
        self.tools = self._register_tools()
    
    def _register_tools(self) -> List[Dict[str, Any]]:
        """Register available deployment and API access tools"""
        return [
            {
                "name": "deploy_to_cloud",
                "description": "Deploy application to cloud platform",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "platform": {
                            "enum": ["gcp", "aws", "azure", "coolify"],
                            "description": "Cloud platform"
                        },
                        "service": {
                            "enum": ["cloud-run", "ecs", "app-service", "container"],
                            "description": "Cloud service"
                        },
                        "config": {
                            "type": "object",
                            "description": "Deployment configuration"
                        }
                    },
                    "required": ["platform", "service", "config"]
                }
            },
            {
                "name": "access_coolify_api",
                "description": "Access Coolify self-hosted platform API",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "enum": ["deploy", "status", "logs", "env_vars"],
                            "description": "Coolify operation"
                        },
                        "app_uuid": {
                            "type": "string",
                            "description": "Application UUID"
                        },
                        "api_token": {
                            "type": "string",
                            "description": "Coolify API token"
                        },
                        "host": {
                            "type": "string",
                            "description": "Coolify host URL",
                            "default": "localhost:8000"
                        },
                        "params": {
                            "type": "object",
                            "description": "Operation parameters"
                        }
                    },
                    "required": ["operation", "app_uuid", "api_token"]
                }
            },
            {
                "name": "access_web_service",
                "description": "Access generic web services and APIs",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Service URL"
                        },
                        "method": {
                            "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                            "description": "HTTP method"
                        },
                        "headers": {
                            "type": "object",
                            "description": "HTTP headers"
                        },
                        "body": {
                            "type": "object",
                            "description": "Request body"
                        },
                        "auth": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "enum": ["bearer", "basic", "api_key"],
                                    "description": "Authentication type"
                                },
                                "token": {
                                    "type": "string",
                                    "description": "Authentication token"
                                }
                            }
                        }
                    },
                    "required": ["url", "method"]
                }
            },
            {
                "name": "build_docker_image",
                "description": "Build Docker image for deployment",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dockerfile_path": {
                            "type": "string",
                            "description": "Path to Dockerfile",
                            "default": "."
                        },
                        "image_name": {
                            "type": "string",
                            "description": "Docker image name and tag"
                        },
                        "build_args": {
                            "type": "object",
                            "description": "Docker build arguments"
                        },
                        "platform": {
                            "type": "string",
                            "description": "Target platform (e.g., linux/amd64)",
                            "default": "linux/amd64"
                        }
                    },
                    "required": ["image_name"]
                }
            },
            {
                "name": "manage_ssh_tunnel",
                "description": "Manage SSH tunnels for secure connections",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "enum": ["create", "close", "status"],
                            "description": "Tunnel action"
                        },
                        "local_port": {
                            "type": "integer",
                            "description": "Local port"
                        },
                        "remote_host": {
                            "type": "string",
                            "description": "Remote host"
                        },
                        "remote_port": {
                            "type": "integer",
                            "description": "Remote port"
                        },
                        "ssh_key": {
                            "type": "string",
                            "description": "Path to SSH key"
                        },
                        "ssh_user": {
                            "type": "string",
                            "description": "SSH user"
                        }
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "health_check_deployment",
                "description": "Perform comprehensive health checks on deployed application",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "app_url": {
                            "type": "string",
                            "description": "Application URL to check"
                        },
                        "health_endpoints": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of health check endpoints",
                            "default": ["/health", "/ready", "/"]
                        },
                        "expected_response_time": {
                            "type": "integer",
                            "description": "Expected response time in milliseconds",
                            "default": 2000
                        }
                    },
                    "required": ["app_url"]
                }
            }
        ]
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """Return list of available tools"""
        return self.tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the specified tool with given arguments"""
        try:
            if name == "deploy_to_cloud":
                return await self._deploy_to_cloud(arguments)
            elif name == "access_coolify_api":
                return await self._access_coolify_api(arguments)
            elif name == "access_web_service":
                return await self._access_web_service(arguments)
            elif name == "build_docker_image":
                return await self._build_docker_image(arguments)
            elif name == "manage_ssh_tunnel":
                return await self._manage_ssh_tunnel(arguments)
            elif name == "health_check_deployment":
                return await self._health_check_deployment(arguments)
            else:
                return {"error": f"Unknown tool: {name}"}
        
        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return {"error": f"Tool execution failed: {str(e)}"}
    
    async def _deploy_to_cloud(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy application to specified cloud platform"""
        platform = args["platform"]
        service = args["service"]
        config = args["config"]
        
        if platform == "coolify":
            # Use Coolify deployment
            return await self._deploy_coolify(config)
        
        elif platform == "gcp":
            if service == "cloud-run":
                cmd = [
                    "gcloud", "run", "deploy", config["service_name"],
                    "--image", config["image"],
                    "--platform", "managed"
                ]
                
                if config.get("region"):
                    cmd.extend(["--region", config["region"]])
                
                if config.get("port"):
                    cmd.extend(["--port", str(config["port"])])
                
                if config.get("allow_unauthenticated", True):
                    cmd.append("--allow-unauthenticated")
        
        elif platform == "aws":
            if service == "ecs":
                cmd = [
                    "aws", "ecs", "create-service",
                    "--service-name", config["service_name"],
                    "--task-definition", config["task_definition"],
                    "--cluster", config["cluster"]
                ]
        
        elif platform == "azure":
            if service == "app-service":
                cmd = [
                    "az", "webapp", "create",
                    "--resource-group", config["resource_group"],
                    "--plan", config["app_service_plan"],
                    "--name", config["app_name"],
                    "--runtime", config["runtime"]
                ]
        else:
            return {"error": f"Unsupported platform: {platform}"}
        
        logger.info(f"Deploying to {platform}: {' '.join(cmd)}")
        result = await self._run_command(cmd)
        
        # Enhanced result with deployment summary
        if result.get("exit_code") == 0:
            result["deployment_status"] = "success"
            result["platform"] = platform
            result["service"] = service
        else:
            result["deployment_status"] = "failed"
        
        return result
    
    async def _deploy_coolify(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to Coolify platform"""
        try:
            # Use the deploy script if available
            if os.path.exists("./deploy.sh"):
                cmd = ["bash", "./deploy.sh"]
                logger.info("Using deploy.sh script for Coolify deployment")
                return await self._run_command(cmd)
            
            # Fallback to direct API call
            api_token = config.get("api_token")
            app_uuid = config.get("app_uuid")
            host = config.get("host", "localhost:8000")
            
            if not api_token or not app_uuid:
                return {"error": "Missing api_token or app_uuid for Coolify deployment"}
            
            return await self._access_coolify_api({
                "operation": "deploy",
                "app_uuid": app_uuid,
                "api_token": api_token,
                "host": host
            })
        
        except Exception as e:
            return {"error": f"Coolify deployment failed: {str(e)}"}
    
    async def _access_coolify_api(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Access Coolify API for various operations"""
        operation = args["operation"]
        app_uuid = args["app_uuid"]
        api_token = args["api_token"]
        host = args.get("host", "localhost:8000")
        params = args.get("params", {})
        
        base_url = f"http://{host}/api/v1"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        try:
            if operation == "deploy":
                url = f"{base_url}/deploy"
                data = {"uuid": app_uuid}
                response = requests.post(url, json=data, headers=headers)
            
            elif operation == "status":
                url = f"{base_url}/applications/{app_uuid}"
                response = requests.get(url, headers=headers)
            
            elif operation == "logs":
                url = f"{base_url}/applications/{app_uuid}/logs"
                response = requests.get(url, headers=headers)
            
            elif operation == "env_vars":
                url = f"{base_url}/applications/{app_uuid}/envs"
                if params.get("set"):
                    # Set environment variable
                    data = {
                        "key": params["key"],
                        "value": params["value"]
                    }
                    response = requests.post(url, json=data, headers=headers)
                else:
                    # Get environment variables
                    response = requests.get(url, headers=headers)
            else:
                return {"error": f"Unsupported Coolify operation: {operation}"}
            
            return {
                "status_code": response.status_code,
                "response": response.json() if response.content else {},
                "success": response.status_code < 400,
                "operation": operation
            }
        
        except requests.RequestException as e:
            return {"error": f"Coolify API request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Coolify API access failed: {str(e)}"}
    
    async def _access_web_service(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Access generic web services"""
        url = args["url"]
        method = args["method"]
        headers = args.get("headers", {})
        body = args.get("body", {})
        auth = args.get("auth", {})
        
        # Add authentication headers
        if auth:
            auth_type = auth.get("type")
            token = auth.get("token")
            
            if auth_type == "bearer" and token:
                headers["Authorization"] = f"Bearer {token}"
            elif auth_type == "api_key" and token:
                headers["X-API-Key"] = token
            elif auth_type == "basic" and token:
                # Assume token is already base64 encoded
                headers["Authorization"] = f"Basic {token}"
        
        # Build curl command
        cmd = ["curl", "-s", "-X", method]
        
        # Add headers
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
        
        # Add body if present
        if body and method in ["POST", "PUT", "PATCH"]:
            cmd.extend(["-d", json.dumps(body)])
        
        # Add URL
        cmd.append(url)
        
        logger.info(f"Accessing web service: {method} {url}")
        result = await self._run_command(cmd)
        
        # Try to parse JSON response
        try:
            if result.get("stdout"):
                parsed_response = json.loads(result["stdout"])
                result["parsed_response"] = parsed_response
        except json.JSONDecodeError:
            pass
        
        return result
    
    async def _build_docker_image(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build Docker image"""
        dockerfile_path = args.get("dockerfile_path", ".")
        image_name = args["image_name"]
        build_args = args.get("build_args", {})
        platform = args.get("platform", "linux/amd64")
        
        cmd = ["docker", "build", "--platform", platform]
        
        # Add build arguments
        for key, value in build_args.items():
            cmd.extend(["--build-arg", f"{key}={value}"])
        
        # Add tag and context
        cmd.extend(["-t", image_name, dockerfile_path])
        
        logger.info(f"Building Docker image: {' '.join(cmd)}")
        result = await self._run_command(cmd)
        
        if result.get("exit_code") == 0:
            result["image_built"] = image_name
            result["build_status"] = "success"
        else:
            result["build_status"] = "failed"
        
        return result
    
    async def _manage_ssh_tunnel(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Manage SSH tunnels"""
        action = args["action"]
        
        if action == "create":
            local_port = args["local_port"]
            remote_host = args["remote_host"]
            remote_port = args["remote_port"]
            ssh_key = args.get("ssh_key")
            ssh_user = args["ssh_user"]
            
            cmd = ["ssh", "-N", "-L", f"{local_port}:localhost:{remote_port}"]
            
            if ssh_key:
                cmd.extend(["-i", ssh_key])
            
            cmd.append(f"{ssh_user}@{remote_host}")
            
            # Run in background
            logger.info(f"Creating SSH tunnel: {' '.join(cmd)}")
            process = subprocess.Popen(cmd)
            
            return {
                "tunnel_created": True,
                "pid": process.pid,
                "local_port": local_port,
                "remote_host": remote_host,
                "remote_port": remote_port
            }
        
        elif action == "status":
            # Check for existing SSH tunnels
            cmd = ["ps", "aux"]
            result = await self._run_command(cmd)
            
            tunnels = []
            if result.get("stdout"):
                for line in result["stdout"].split('\n'):
                    if "ssh" in line and "-L" in line:
                        tunnels.append(line.strip())
            
            return {
                "active_tunnels": tunnels,
                "tunnel_count": len(tunnels)
            }
        
        elif action == "close":
            # Kill SSH tunnel processes
            cmd = ["pkill", "-f", "ssh.*-L"]
            result = await self._run_command(cmd)
            return {
                "tunnels_closed": result.get("exit_code") == 0,
                "message": "SSH tunnels terminated"
            }
        
        return {"error": f"Unsupported tunnel action: {action}"}
    
    async def _health_check_deployment(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive health checks"""
        app_url = args["app_url"]
        health_endpoints = args.get("health_endpoints", ["/health", "/ready", "/"])
        expected_response_time = args.get("expected_response_time", 2000)
        
        results = {
            "app_url": app_url,
            "overall_health": True,
            "checks": [],
            "summary": {}
        }
        
        total_checks = len(health_endpoints)
        successful_checks = 0
        
        for endpoint in health_endpoints:
            url = f"{app_url.rstrip('/')}{endpoint}"
            
            # Use curl with timeout
            cmd = [
                "curl", "-s", "-w", 
                "response_time:%{time_total}\\nhttp_code:%{http_code}\\n",
                "--max-time", "5",
                url
            ]
            
            result = await self._run_command(cmd)
            
            check_result = {
                "endpoint": endpoint,
                "url": url,
                "success": False,
                "response_time": None,
                "status_code": None
            }
            
            if result.get("exit_code") == 0 and result.get("stdout"):
                output = result["stdout"]
                
                # Parse response time and status code
                if "response_time:" in output:
                    try:
                        response_time = float(output.split("response_time:")[1].split()[0])
                        check_result["response_time"] = round(response_time * 1000, 2)  # Convert to ms
                    except (ValueError, IndexError):
                        pass
                
                if "http_code:" in output:
                    try:
                        status_code = int(output.split("http_code:")[1].split()[0])
                        check_result["status_code"] = status_code
                        
                        # Consider 2xx and 3xx as successful
                        if 200 <= status_code < 400:
                            check_result["success"] = True
                            successful_checks += 1
                            
                            # Check response time
                            if check_result["response_time"] and check_result["response_time"] > expected_response_time:
                                check_result["warning"] = f"Response time {check_result['response_time']}ms exceeds expected {expected_response_time}ms"
                    except (ValueError, IndexError):
                        pass
            
            if not check_result["success"]:
                results["overall_health"] = False
                check_result["error"] = result.get("stderr", "Health check failed")
            
            results["checks"].append(check_result)
        
        # Summary
        results["summary"] = {
            "total_checks": total_checks,
            "successful_checks": successful_checks,
            "success_rate": round((successful_checks / total_checks) * 100, 2) if total_checks > 0 else 0,
            "health_status": "healthy" if results["overall_health"] else "unhealthy"
        }
        
        return results
    
    async def _run_command(self, cmd: List[str]) -> Dict[str, Any]:
        """Run a command asynchronously and return result"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "command": " ".join(cmd)
            }
        
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "command": " ".join(cmd),
                "error": f"Command execution failed: {str(e)}"
            }

def main():
    """Main function to run the MCP server"""
    server = HybridDeploymentServer()
    
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