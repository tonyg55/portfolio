"""
Mimicking developer provision requests.

These tests mock Docker so they run without Docker installed,
but exercise the real provisioner, CLI, and health check code paths.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from main import cli
from src.config.settings import Settings
from src.provisioner.local import LocalProvisioner


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def provisioner(settings):
    return LocalProvisioner(settings)


@pytest.fixture
def runner():
    return CliRunner()


def _mock_run(stdout="", returncode=0):
    """Helper: return a fake subprocess.CompletedProcess."""
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = ""
    return m


# ── Provisioner unit tests ─────────────────────────────────────────────────────

class TestLocalProvisioner:
    """Simulate a developer calling the provisioner directly."""

    @patch("src.provisioner.local.subprocess.run")
    def test_provision_success(self, mock_run, provisioner):
        """
        Developer requests a new database named 'payments-db'.
        Expect: container started, connection details returned.
        """
        # First call: docker ps -a (check if exists) → not found
        # Second call: docker run → container ID
        # Third call: docker inspect → host port
        mock_run.side_effect = [
            _mock_run(stdout=""),                          # container does not exist, nothing to return
            _mock_run(stdout="abc123def456\n"),            # docker run succeeds and returns a sample container id
            _mock_run(stdout="54321\n"),                   # docker inspect returns sample port number
        ]

        result = provisioner.provision(
            name="payments-db",
            db_name="paymentsdb",
            username="devuser",
            password="supersecret",
            size="small",
            version="16",
        )

        assert result["name"] == "payments-db"
        assert result["host"] == "localhost"
        assert result["port"] == 54321
        assert result["db_name"] == "paymentsdb"
        assert result["username"] == "devuser"
        assert result["version"] == "16"
        assert result["status"] == "running"
        assert result["container"] == "pg-payments-db"

    @patch("src.provisioner.local.subprocess.run")
    def test_provision_duplicate_returns_existing(self, mock_run, provisioner):
        """
        Developer provisions a database that already exists.
        Expect: existing connection details returned (create-or-return idempotency).
        """
        # First call: docker ps -a (container exists) → container ID
        # Second call: docker inspect → host port
        mock_run.side_effect = [
            _mock_run(stdout="existing-container-id\n"),  # container exists
            _mock_run(stdout="54321\n"),                  # docker inspect returns port
        ]

        result = provisioner.provision(
            name="payments-db",
            db_name="paymentsdb",
            username="devuser",
            password="supersecret",
            size="small",
            version="16",
        )

        assert result["name"] == "payments-db"
        assert result["host"] == "localhost"
        assert result["port"] == 54321
        assert result["status"] == "running"

    @patch("src.provisioner.local.subprocess.run")
    def test_destroy_success(self, mock_run, provisioner):
        """
        Developer requests teardown of their database.
        Expect: docker stop and docker rm both called.
        """
        mock_run.return_value = _mock_run(stdout="ok\n")

        provisioner.destroy(name="payments-db")

        calls = [str(c) for c in mock_run.call_args_list]
        assert any("stop" in c for c in calls)
        assert any("rm" in c for c in calls)

    @patch("src.provisioner.local.subprocess.run")
    def test_list_instances_returns_running(self, mock_run, provisioner):
        """
        Platform team lists all provisioned databases.
        Expect: running instance appears with correct status.
        """
        fake_docker_output = json.dumps({
            "Names": "/pg-payments-db",
            "Status": "Up 2 hours",
            "Labels": (
                "pg-provision.managed=true,"
                "pg-provision.version=16,"
                "pg-provision.db=paymentsdb,"
                "pg-provision.user=devuser"
            ),
            "Ports": "0.0.0.0:54321->5432/tcp",
            "CreatedAt": "2026-03-09 10:00:00",
        })
        mock_run.return_value = _mock_run(stdout=fake_docker_output + "\n")

        instances = provisioner.list_instances()

        assert len(instances) == 1
        assert instances[0]["name"] == "payments-db"
        assert instances[0]["status"] == "running"
        assert instances[0]["version"] == "16"
        assert instances[0]["port"] == "54321"

    @patch("src.provisioner.local.subprocess.run")
    def test_list_instances_empty(self, mock_run, provisioner):
        """No databases provisioned yet — list returns empty."""
        mock_run.return_value = _mock_run(stdout="")

        instances = provisioner.list_instances()
        assert instances == []


# ── CLI integration tests ──────────────────────────────────────────────────────

class TestCLI:
    """Simulate a developer running CLI commands."""

    @patch("src.provisioner.local.subprocess.run")
    def test_cli_provision_command(self, mock_run, runner):
        """
        Developer runs: python main.py provision --target local --name mydb
        Expect: success output with connection details table.
        """
        mock_run.side_effect = [
            _mock_run(stdout=""),           # container does not exist
            _mock_run(stdout="abc123\n"),   # docker run and returns sample container id
            _mock_run(stdout="5555\n"),     # docker inspect return sample port number
        ]

        result = runner.invoke(cli, [
            "provision",
            "--target", "local",
            "--name", "mydb",
            "--db-name", "appdb",
            "--username", "appuser",
            "--password", "testpass",
        ])

        assert result.exit_code == 0, result.output
        assert "provisioned successfully" in result.output
        assert "localhost" in result.output
        assert "appdb" in result.output

    @patch("src.provisioner.local.subprocess.run")
    def test_cli_list_command(self, mock_run, runner):
        """Developer runs: python main.py list --target local"""
        fake = json.dumps({
            "Names": "/pg-mydb",
            "Status": "Up 1 hour",
            "Labels": "pg-provision.managed=true,pg-provision.version=16",
            "Ports": "0.0.0.0:5432->5432/tcp",
            "CreatedAt": "2026-03-09 09:00:00",
        })
        mock_run.return_value = _mock_run(stdout=fake + "\n")

        result = runner.invoke(cli, ["list", "--target", "local"])

        assert result.exit_code == 0
        assert "mydb" in result.output

    @patch("src.provisioner.local.subprocess.run")
    def test_cli_destroy_requires_confirmation(self, mock_run, runner):
        """
        Developer runs destroy without --force.
        Expect: confirmation prompt shown.
        """
        result = runner.invoke(cli, [
            "destroy", "--target", "local", "--name", "mydb"
        ], input="n\n")

        assert result.exit_code != 0 or "Aborted" in result.output

    @patch("src.provisioner.local.subprocess.run")
    def test_cli_destroy_with_force(self, mock_run, runner):
        """Developer runs destroy --force — skips confirmation."""
        mock_run.return_value = _mock_run(stdout="ok\n")

        result = runner.invoke(cli, [
            "destroy", "--target", "local", "--name", "mydb", "--force"
        ])

        assert result.exit_code == 0
        assert "destroyed" in result.output


# ── Health check tests ─────────────────────────────────────────────────────────

class TestHealthChecker:
    """Simulate the platform team running health checks on a live database."""

    @patch("src.monitoring.health.psycopg2.connect")
    @patch("src.monitoring.health.socket.create_connection")
    def test_all_checks_pass(self, mock_socket, mock_connect):
        """
        All six health checks pass against a healthy database.
        """
        from src.monitoring.health import HealthChecker

        # Mock TCP connection
        mock_socket.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_socket.return_value.__exit__ = MagicMock(return_value=False)

        # Mock psycopg2 connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # Return values for each SQL query that calls fetchone.
        # Note: _check_query runs SELECT 1 but does NOT call fetchone — no entry needed.
        mock_cursor.fetchone.side_effect = [
            (0,),           # inactive replication slots = 0
            (100, 5),       # max_connections=100, used=5
            ("on",),        # autovacuum = on
        ]

        checker = HealthChecker(
            host="localhost", port=5432,
            db_name="appdb", username="appuser", password="testpass"
        )
        results = checker.run_all()

        passed = [r for r in results if r["passed"]]
        failed = [r for r in results if not r["passed"]]

        assert len(failed) == 0, f"Unexpected failures: {failed}"
        assert len(passed) == 6

    @patch("src.monitoring.health.socket.create_connection")
    def test_tcp_check_fails_when_db_unreachable(self, mock_socket):
        """
        Health check correctly reports failure when database is unreachable.
        """
        from src.monitoring.health import HealthChecker

        mock_socket.side_effect = ConnectionRefusedError("Connection refused")

        checker = HealthChecker(
            host="localhost", port=9999,
            db_name="appdb", username="appuser", password="testpass"
        )
        results = checker.run_all()

        tcp_result = next(r for r in results if r["name"] == "TCP Connectivity")
        assert tcp_result["passed"] is False
        assert "Connection refused" in tcp_result["detail"]
