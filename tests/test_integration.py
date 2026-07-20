import unittest
import http.server
import socketserver
import threading
import time
import asyncio
from pathlib import Path
from app.config import settings
from app.services.importer import ImportWorker

class MockCucumberStudioHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress logging console spam
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        path = self.path

        if "/users/sign_in" in path:
            # Login Page
            self.wfile.write(b"""
            <html>
            <body>
                <form action="/projects" method="GET">
                    <input id="user_email" name="user[email]" type="email" placeholder="Email" />
                    <input id="user_password" name="user[password]" type="password" placeholder="Password" />
                    <input type="submit" value="Sign in" />
                </form>
            </body>
            </html>
            """)
            
        elif "/projects/1" in path:
            # Project View
            self.wfile.write(b"""
            <html>
            <head>
                <script>
                    function showFolderForm() {
                        document.getElementById('folder_form').style.display = 'block';
                    }
                    function createFolder() {
                        let val = document.getElementById('folder_name').value;
                        let div = document.createElement('div');
                        div.className = 'folder-name';
                        div.innerText = val;
                        document.getElementById('folder_tree').appendChild(div);
                        document.getElementById('folder_form').style.display = 'none';
                    }
                    function showScenarioForm() {
                        document.getElementById('scenario_form').style.display = 'block';
                    }
                </script>
            </head>
            <body>
                <h1>Project 1</h1>
                <div id="folder_tree">
                    <span class="folder-name">Mobile</span>
                </div>
                
                <button class="create-folder-btn" onclick="showFolderForm()">Create folder</button>
                <form id="folder_form" style="display:none;" onsubmit="createFolder(); return false;">
                    <input id="folder_name" type="text" placeholder="Folder name" />
                    <input type="submit" id="folder_submit" value="Create" />
                </form>

                <button class="create-scenario-btn" onclick="showScenarioForm()">Create scenario</button>
                <div id="scenario_form" style="display:none;">
                    <form action="/scenario_editor" method="GET">
                        <input id="scenario_name" name="scenario[name]" type="text" placeholder="Scenario name" />
                        <input type="submit" value="Create" />
                    </form>
                </div>
            </body>
            </html>
            """)
            
        elif "/projects" in path:
            # Projects Dashboard
            self.wfile.write(b"""
            <html>
            <body>
                <h1>Projects Dashboard</h1>
                <a href="/projects/1">Test Project</a>
            </body>
            </html>
            """)
            
        elif "/scenario_editor" in path:
            # Scenario details editor
            self.wfile.write(b"""
            <html>
            <head>
                <script>
                    function addStepRow() {
                        let c = document.getElementById('step_container');
                        let div = document.createElement('div');
                        div.innerHTML = '<textarea class="step-action" placeholder="Action"></textarea><textarea class="step-result" placeholder="Result"></textarea>';
                        c.appendChild(div);
                    }
                </script>
            </head>
            <body>
                <h1>Scenario Editor</h1>
                <div class="breadcrumbs">
                    <a href="/projects/1">Register</a>
                </div>
                <form action="/projects/1" method="GET">
                    <div id="step_container">
                        <div>
                            <textarea class="step-action" placeholder="Action"></textarea>
                            <textarea class="step-result" placeholder="Result"></textarea>
                        </div>
                    </div>
                    <button class="add-step-btn" type="button" onclick="addStepRow()">Add step</button>
                    <button class="btn-save" type="submit">Save</button>
                </form>
            </body>
            </html>
            """)
        else:
            self.wfile.write(b"OK")


class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Find a free port
        cls.port = 8089
        cls.server = socketserver.TCPServer(("127.0.0.1", cls.port), MockCucumberStudioHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        
        # Patch settings
        settings.SIGN_IN_URL = f"http://127.0.0.1:{cls.port}/users/sign_in"
        settings.PROJECTS_URL = f"http://127.0.0.1:{cls.port}/projects"
        
        cls.test_file = Path("scenarios_mobile.txt")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join()

    def test_full_import_workflow(self):
        # Construct config
        config_data = {
            "email": "test@example.com",
            "password": "password123",
            "project_name": "Test Project",
            "headless": True,
            "typing_speed_ms": 1,  # Fast typing for testing
            "timeout_ms": 3000,
            "retries": 2
        }

        # Instantiate worker and clear progress history
        worker = ImportWorker(self.test_file, config_data)
        worker.progress_mgr.clear()
        
        # We hook into QThread finished signal
        finished_data = {}
        def on_finished(success, message):
            finished_data["success"] = success
            finished_data["message"] = message

        worker.finished_signal.connect(on_finished)
        
        # Execute worker synchronously in this thread for testing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(worker.async_run())
        finally:
            loop.close()

        # Check results
        self.assertTrue(finished_data.get("success", False))
        self.assertIn("Imported: 2", finished_data.get("message", ""))
        print("Integration test passed!")

if __name__ == "__main__":
    unittest.main()
