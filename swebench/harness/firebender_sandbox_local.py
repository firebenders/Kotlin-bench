#!/usr/bin/env python3
"""
Local Firebender Agent Sandbox Test Script

This script can be run locally (on a machine with a display or Xvfb) to test
the Firebender agent server setup before deploying to Modal.

Requirements:
- Git
- Java 17+
- Xvfb (for headless mode)

Usage:
    # With display (macOS/Linux with GUI)
    python swebench/harness/firebender_sandbox_local.py
    
    # Headless with Xvfb (Linux servers)
    python swebench/harness/firebender_sandbox_local.py --headless
    
    # Custom query
    python swebench/harness/firebender_sandbox_local.py --query "Add logs to AutocompleteCache.kt"
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

# Configuration
AGENT_SERVER_PORT = 8742
DISPLAY_NUM = 99
SCREEN_RESOLUTION = "1920x1080x24"
REPO_URL = "https://github.com/firebenders/android-studio-copilot.git"
DEFAULT_BRANCH = "aman/firebender-harness"


class FirebenderSandbox:
    """
    Manages the Firebender IDE sandbox environment.
    """
    
    def __init__(
        self,
        repo_dir: str = "./firebender-sandbox",
        headless: bool = False,
        verbose: bool = True,
    ):
        self.repo_dir = Path(repo_dir).absolute()
        self.headless = headless
        self.verbose = verbose
        self.xvfb_process: Optional[subprocess.Popen] = None
        self.ide_process: Optional[subprocess.Popen] = None
        self.log_file: Optional[Path] = None
        
    def log(self, message: str):
        """Print log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[Sandbox] {message}")
    
    def clone_repo(self, branch: str = DEFAULT_BRANCH, force: bool = False) -> bool:
        """
        Clone or update the Firebender repository.
        
        Args:
            branch: Git branch to checkout
            force: If True, delete and re-clone
            
        Returns:
            True if successful
        """
        repo_path = self.repo_dir / "android-studio-copilot"
        
        if repo_path.exists():
            if force:
                self.log(f"Removing existing repo at {repo_path}")
                shutil.rmtree(repo_path)
            else:
                self.log(f"Updating existing repo at {repo_path}")
                try:
                    subprocess.run(
                        ["git", "fetch", "--all"],
                        cwd=repo_path,
                        check=True,
                        capture_output=True,
                    )
                    subprocess.run(
                        ["git", "checkout", branch],
                        cwd=repo_path,
                        check=True,
                        capture_output=True,
                    )
                    subprocess.run(
                        ["git", "pull", "origin", branch],
                        cwd=repo_path,
                        check=False,
                        capture_output=True,
                    )
                    return True
                except subprocess.CalledProcessError as e:
                    self.log(f"Failed to update repo: {e}")
                    return False
        
        # Clone fresh
        self.log(f"Cloning {REPO_URL} (branch: {branch})...")
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            subprocess.run(
                [
                    "git", "clone",
                    "--branch", branch,
                    "--single-branch",
                    REPO_URL,
                    str(repo_path),
                ],
                check=True,
            )
            
            # Make gradlew executable
            gradlew = repo_path / "gradlew"
            if gradlew.exists():
                gradlew.chmod(0o755)
            
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to clone repo: {e}")
            return False
    
    def start_xvfb(self) -> bool:
        """
        Start Xvfb virtual display (Linux only).
        
        Returns:
            True if started successfully or not needed
        """
        if not self.headless:
            self.log("Headless mode disabled, skipping Xvfb")
            return True
        
        if sys.platform == "darwin":
            self.log("Xvfb not supported on macOS, using native display")
            return True
        
        self.log(f"Starting Xvfb on display :{DISPLAY_NUM}")
        
        try:
            self.xvfb_process = subprocess.Popen(
                [
                    "Xvfb",
                    f":{DISPLAY_NUM}",
                    "-screen", "0", SCREEN_RESOLUTION,
                    "-ac",
                    "-nolisten", "tcp",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            time.sleep(2)
            
            if self.xvfb_process.poll() is not None:
                stdout, stderr = self.xvfb_process.communicate()
                self.log(f"Xvfb failed to start: {stderr.decode()}")
                return False
            
            self.log(f"Xvfb started (PID: {self.xvfb_process.pid})")
            return True
            
        except FileNotFoundError:
            self.log("Xvfb not found. Install with: apt-get install xvfb")
            return False
        except Exception as e:
            self.log(f"Failed to start Xvfb: {e}")
            return False
    
    def start_ide(self, timeout: int = 300) -> bool:
        """
        Start IntelliJ IDE with agent server enabled.
        
        Args:
            timeout: Seconds to wait for IDE to be ready
            
        Returns:
            True if IDE and agent server are ready
        """
        repo_path = self.repo_dir / "android-studio-copilot"
        
        if not repo_path.exists():
            self.log(f"Repository not found at {repo_path}")
            return False
        
        # Prepare environment
        env = os.environ.copy()
        env["FIREBENDER_AGENT_SERVER"] = "true"
        env["FIREBENDER_AGENT_SERVER_PORT"] = str(AGENT_SERVER_PORT)
        
        if self.headless and sys.platform != "darwin":
            env["DISPLAY"] = f":{DISPLAY_NUM}"
        
        # Create log file
        logs_dir = self.repo_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        self.log_file = logs_dir / f"ide_{int(time.time())}.log"
        
        self.log(f"Starting IDE with agent server on port {AGENT_SERVER_PORT}...")
        self.log(f"Logs: {self.log_file}")
        
        try:
            with open(self.log_file, "w") as log_f:
                self.ide_process = subprocess.Popen(
                    ["./gradlew", "runIde", "--no-daemon"],
                    env=env,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    cwd=repo_path,
                )
            
            self.log(f"IDE process started (PID: {self.ide_process.pid})")
            
            # Wait for agent server to be ready
            return self._wait_for_server(timeout)
            
        except Exception as e:
            self.log(f"Failed to start IDE: {e}")
            return False
    
    def _wait_for_server(self, timeout: int) -> bool:
        """Wait for the agent server to be ready."""
        import urllib.request
        import urllib.error
        
        start_time = time.time()
        
        self.log(f"Waiting for agent server (timeout: {timeout}s)...")
        
        while time.time() - start_time < timeout:
            # Check if IDE process is still running
            if self.ide_process and self.ide_process.poll() is not None:
                self.log(f"IDE process exited with code {self.ide_process.returncode}")
                if self.log_file and self.log_file.exists():
                    self.log("Last 50 lines of log:")
                    with open(self.log_file) as f:
                        lines = f.readlines()
                        for line in lines[-50:]:
                            print(f"  {line.rstrip()}")
                return False
            
            # Try to connect to agent server
            for endpoint in ["/health", "/agent/status", "/"]:
                try:
                    url = f"http://localhost:{AGENT_SERVER_PORT}{endpoint}"
                    req = urllib.request.Request(url, method="GET")
                    with urllib.request.urlopen(req, timeout=2) as response:
                        self.log(f"Agent server is ready! (endpoint: {endpoint})")
                        return True
                except urllib.error.HTTPError as e:
                    if e.code in [404, 405]:  # Server is up but endpoint doesn't exist
                        self.log(f"Agent server is ready! (got {e.code} on {endpoint})")
                        return True
                except:
                    pass
            
            elapsed = int(time.time() - start_time)
            if elapsed % 30 == 0:
                self.log(f"Still waiting... ({elapsed}s)")
            
            time.sleep(5)
        
        self.log(f"Timeout waiting for agent server")
        return False
    
    def run_query(self, query: str, timeout: int = 120) -> Dict[str, Any]:
        """
        Send a query to the agent server.
        
        Args:
            query: The query/task to send
            timeout: Request timeout in seconds
            
        Returns:
            Response dict
        """
        import urllib.request
        import urllib.error
        
        url = f"http://localhost:{AGENT_SERVER_PORT}/agent/run"
        
        self.log(f"Sending query: {query}")
        
        try:
            data = json.dumps({"query": query}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                response_data = response.read().decode("utf-8")
                return {
                    "status": "success",
                    "response": json.loads(response_data),
                    "status_code": response.status,
                }
                
        except urllib.error.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.code}: {e.reason}",
                "response": e.read().decode("utf-8") if e.fp else None,
            }
        except urllib.error.URLError as e:
            return {
                "status": "error",
                "error": f"Connection failed: {e.reason}",
            }
        except TimeoutError:
            return {
                "status": "timeout",
                "error": f"Request timed out after {timeout}s",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
    
    def cleanup(self):
        """Stop all processes and clean up."""
        self.log("Cleaning up...")
        
        if self.ide_process:
            self.log(f"Terminating IDE process (PID: {self.ide_process.pid})")
            self.ide_process.terminate()
            try:
                self.ide_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.ide_process.kill()
        
        if self.xvfb_process:
            self.log(f"Terminating Xvfb process (PID: {self.xvfb_process.pid})")
            self.xvfb_process.terminate()
    
    def run_test(
        self,
        query: str = "List the files in this project",
        branch: str = DEFAULT_BRANCH,
        ide_timeout: int = 300,
        query_timeout: int = 120,
    ) -> Dict[str, Any]:
        """
        Run a complete sandbox test.
        
        Args:
            query: Test query to send
            branch: Git branch to use
            ide_timeout: Timeout for IDE startup
            query_timeout: Timeout for agent query
            
        Returns:
            Test results dict
        """
        results = {
            "steps": [],
            "success": False,
            "query": query,
        }
        
        try:
            # Step 1: Clone repo
            self.log("=" * 50)
            self.log("Step 1: Clone/update repository")
            self.log("=" * 50)
            
            if self.clone_repo(branch):
                results["steps"].append({"step": "clone", "status": "success"})
            else:
                results["steps"].append({"step": "clone", "status": "error"})
                return results
            
            # Step 2: Start Xvfb (if headless)
            if self.headless:
                self.log("\n" + "=" * 50)
                self.log("Step 2: Start Xvfb")
                self.log("=" * 50)
                
                if self.start_xvfb():
                    results["steps"].append({"step": "xvfb", "status": "success"})
                else:
                    results["steps"].append({"step": "xvfb", "status": "error"})
                    return results
            
            # Step 3: Start IDE
            self.log("\n" + "=" * 50)
            self.log("Step 3: Start IDE with agent server")
            self.log("=" * 50)
            
            if self.start_ide(ide_timeout):
                results["steps"].append({
                    "step": "ide",
                    "status": "success",
                    "port": AGENT_SERVER_PORT,
                })
            else:
                results["steps"].append({"step": "ide", "status": "error"})
                return results
            
            # Step 4: Run query
            self.log("\n" + "=" * 50)
            self.log(f"Step 4: Run agent query")
            self.log("=" * 50)
            
            query_result = self.run_query(query, query_timeout)
            results["steps"].append({
                "step": "query",
                **query_result,
            })
            
            if query_result["status"] == "success":
                results["success"] = True
            
            return results
            
        finally:
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="Firebender Agent Sandbox Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "--query", "-q",
        default="List the files in this project",
        help="Query to send to the agent",
    )
    
    parser.add_argument(
        "--branch", "-b",
        default=DEFAULT_BRANCH,
        help=f"Git branch to use (default: {DEFAULT_BRANCH})",
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode with Xvfb (Linux only)",
    )
    
    parser.add_argument(
        "--repo-dir",
        default="./firebender-sandbox",
        help="Directory to clone repository into",
    )
    
    parser.add_argument(
        "--ide-timeout",
        type=int,
        default=300,
        help="Timeout in seconds for IDE startup (default: 300)",
    )
    
    parser.add_argument(
        "--query-timeout",
        type=int,
        default=120,
        help="Timeout in seconds for agent query (default: 120)",
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )
    
    args = parser.parse_args()
    
    # Handle Ctrl+C gracefully
    sandbox = FirebenderSandbox(
        repo_dir=args.repo_dir,
        headless=args.headless,
        verbose=not args.quiet,
    )
    
    def signal_handler(sig, frame):
        print("\n\nInterrupted! Cleaning up...")
        sandbox.cleanup()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run test
    print("=" * 60)
    print("Firebender Agent Sandbox Test")
    print("=" * 60)
    print(f"Query: {args.query}")
    print(f"Branch: {args.branch}")
    print(f"Headless: {args.headless}")
    print(f"IDE Timeout: {args.ide_timeout}s")
    print(f"Query Timeout: {args.query_timeout}s")
    print("=" * 60)
    
    results = sandbox.run_test(
        query=args.query,
        branch=args.branch,
        ide_timeout=args.ide_timeout,
        query_timeout=args.query_timeout,
    )
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(json.dumps(results, indent=2))
    
    return 0 if results["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
