#!/usr/bin/env python3
"""
PostgreSQL Provisioning CLI
Platform Engineering Portfolio Demo
"""

import sys
import click
import logging
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.panel import Panel

from src.config.settings import Settings
from src.provisioner.local import LocalProvisioner
from src.provisioner.aws_rds import AWSRDSProvisioner
from src.provisioner.kubernetes import KubernetesProvisioner
from src.monitoring.health import HealthChecker

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
log = logging.getLogger("pgprovision")


def get_provisioner(target: str, settings: Settings):
    """Factory function to return the correct provisioner."""
    provisioners = {
        "local": LocalProvisioner,
        "aws": AWSRDSProvisioner,
        "k8s": KubernetesProvisioner,
    }
    if target not in provisioners:
        raise click.BadParameter(f"Unknown target '{target}'. Choose: {', '.join(provisioners)}")
    return provisioners[target](settings)


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(ctx, debug):
    """pg-provision — PostgreSQL instance provisioning tool.

    Supports local Docker, AWS RDS, and Kubernetes targets.
    """
    ctx.ensure_object(dict)
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    ctx.obj["settings"] = Settings()


@cli.command()
@click.option("--target", "-t", default="local", show_default=True,
              type=click.Choice(["local", "aws", "k8s"]),
              help="Provisioning target.")
@click.option("--name", "-n", required=True, help="Instance name.")
@click.option("--db-name", default="appdb", show_default=True, help="Database name.")
@click.option("--username", default="appuser", show_default=True, help="Database user.")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True,
              help="Database password.")
@click.option("--size", default="small", show_default=True,
              type=click.Choice(["small", "medium", "large"]),
              help="Instance size class.")
@click.option("--version", default="16", show_default=True,
              type=click.Choice(["14", "15", "16"]),
              help="PostgreSQL major version.")
@click.pass_context
def provision(ctx, target, name, db_name, username, password, size, version):
    """Provision a new PostgreSQL instance."""
    settings = ctx.obj["settings"]
    provisioner = get_provisioner(target, settings)

    console.print(Panel.fit(
        f"[bold cyan]Provisioning PostgreSQL[/bold cyan]\n"
        f"Target: [yellow]{target}[/yellow]  |  Name: [yellow]{name}[/yellow]  |  "
        f"Version: [yellow]{version}[/yellow]  |  Size: [yellow]{size}[/yellow]",
        border_style="cyan"
    ))

    try:
        result = provisioner.provision(
            name=name,
            db_name=db_name,
            username=username,
            password=password,
            size=size,
            version=version,
        )
        console.print(f"\n[bold green]✓ Instance provisioned successfully![/bold green]")
        table = Table(title="Connection Details", border_style="green")
        table.add_column("Key", style="bold")
        table.add_column("Value")
        for k, v in result.items():
            table.add_row(k, str(v))
        console.print(table)
    except Exception as e:
        log.error(f"Provisioning failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--target", "-t", default="local", show_default=True,
              type=click.Choice(["local", "aws", "k8s"]))
@click.option("--name", "-n", required=True, help="Instance name.")
@click.option("--force", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def destroy(ctx, target, name, force):
    """Destroy a PostgreSQL instance."""
    settings = ctx.obj["settings"]
    provisioner = get_provisioner(target, settings)

    if not force:
        click.confirm(
            f"[red]Destroy instance '{name}' on {target}? This is irreversible.[/red]",
            abort=True
        )

    try:
        provisioner.destroy(name=name)
        console.print(f"[bold green]✓ Instance '{name}' destroyed.[/bold green]")
    except Exception as e:
        log.error(f"Destroy failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--target", "-t", default="local", show_default=True,
              type=click.Choice(["local", "aws", "k8s"]))
@click.pass_context
def list_instances(ctx, target):
    """List all provisioned PostgreSQL instances."""
    settings = ctx.obj["settings"]
    provisioner = get_provisioner(target, settings)

    instances = provisioner.list_instances()

    if not instances:
        console.print("[yellow]No instances found.[/yellow]")
        return

    table = Table(title=f"PostgreSQL Instances ({target})", border_style="blue")
    table.add_column("Name", style="bold")
    table.add_column("Status")
    table.add_column("Version")
    table.add_column("Host")
    table.add_column("Port")
    table.add_column("Created")

    for inst in instances:
        status_color = "green" if inst.get("status") == "running" else "red"
        table.add_row(
            inst.get("name", "—"),
            f"[{status_color}]{inst.get('status', '—')}[/{status_color}]",
            inst.get("version", "—"),
            inst.get("host", "—"),
            str(inst.get("port", "—")),
            inst.get("created", "—"),
        )

    console.print(table)


@cli.command()
@click.option("--host", default="localhost", show_default=True)
@click.option("--port", default=5432, show_default=True, type=int)
@click.option("--db-name", default="appdb", show_default=True)
@click.option("--username", default="appuser", show_default=True)
@click.option("--password", prompt=True, hide_input=True)
def health(host, port, db_name, username, password):
    """Run health checks against a PostgreSQL instance."""
    checker = HealthChecker(host=host, port=port, db_name=db_name,
                            username=username, password=password)
    results = checker.run_all()

    table = Table(title="Health Check Results", border_style="blue")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    all_pass = True
    for check in results:
        passed = check["passed"]
        if not passed:
            all_pass = False
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        table.add_row(check["name"], status, check.get("detail", ""))

    console.print(table)
    if all_pass:
        console.print("[bold green]✓ All checks passed.[/bold green]")
    else:
        console.print("[bold red]✗ Some checks failed.[/bold red]")
        sys.exit(1)


@cli.command()
@click.option("--host", default="localhost", show_default=True)
@click.option("--port", default=5432, show_default=True, type=int)
@click.option("--db-name", default="appdb", show_default=True)
@click.option("--username", default="appuser", show_default=True)
@click.option("--password", prompt=True, hide_input=True)
@click.option("--output", "-o", default="backup.sql", show_default=True,
              help="Output file path.")
def backup(host, port, db_name, username, password, output):
    """Create a logical backup of a PostgreSQL database."""
    import subprocess
    import os
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    cmd = [
        "pg_dump", "-h", host, "-p", str(port),
        "-U", username, "-d", db_name, "-F", "c", "-f", output
    ]
    console.print(f"[cyan]Running pg_dump → {output}[/cyan]")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode == 0:
        console.print(f"[bold green]✓ Backup written to {output}[/bold green]")
    else:
        console.print(f"[bold red]Backup failed:[/bold red] {result.stderr}")
        sys.exit(1)


cli.add_command(list_instances, name="list")

if __name__ == "__main__":
    cli()
