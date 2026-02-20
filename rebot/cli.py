"""Rebot CLI - Command Line Interface for Multi-Agent Code Generation.

Usage:
    rebot generate "Build a 2048 game"
    rebot generate "Create a todo app" --language typescript --platform web,ios
    rebot init my-project
    rebot run workflow.yaml
    rebot config set openai_api_key sk-xxx
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional, List
import json

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich import print as rprint

console = Console()


# ============================================================================
# Main CLI Group
# ============================================================================

@click.group()
@click.version_option(version="0.1.0", prog_name="rebot")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--config", "-c", type=click.Path(), help="Path to config file")
@click.pass_context
def main(ctx: click.Context, verbose: bool, config: Optional[str]) -> None:
    """Rebot - Multi-Agent Code Generation Framework.
    
    Generate production-ready applications from natural language descriptions.
    
    Examples:
    
        rebot generate "Build a 2048 game"
        
        rebot generate "Create a fitness tracking app" --platform ios,android
        
        rebot init my-project --template web-app
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_path"] = config


# ============================================================================
# Generate Command
# ============================================================================

@main.command()
@click.argument("requirement")
@click.option("--output", "-o", type=click.Path(), default="./output", help="Output directory")
@click.option("--language", "-l", default="python", help="Backend language (python/typescript/go)")
@click.option("--platform", "-p", default="web", help="Target platforms (web,ios,android,desktop,miniapp)")
@click.option("--model", "-m", default="gpt-4", help="LLM model to use")
@click.option("--provider", default="openai", help="LLM provider")
@click.option("--no-ai-codegen", is_flag=True, help="Disable AI code generation")
@click.option("--no-metagpt", is_flag=True, help="Disable MetaGPT chain")
@click.option("--dry-run", is_flag=True, help="Show plan without executing")
@click.pass_context
def generate(
    ctx: click.Context,
    requirement: str,
    output: str,
    language: str,
    platform: str,
    model: str,
    provider: str,
    no_ai_codegen: bool,
    no_metagpt: bool,
    dry_run: bool,
) -> None:
    """Generate code from natural language requirement.
    
    Examples:
    
        rebot generate "Build a 2048 game"
        
        rebot generate "Create a REST API for user management" -l python
        
        rebot generate "Build a fitness app" -p ios,android -o ./fitness-app
    """
    platforms = [p.strip() for p in platform.split(",")]
    output_path = Path(output).resolve()
    
    console.print(Panel.fit(
        f"[bold blue]Rebot Code Generator[/bold blue]\n\n"
        f"[yellow]Requirement:[/yellow] {requirement}\n"
        f"[yellow]Output:[/yellow] {output_path}\n"
        f"[yellow]Language:[/yellow] {language}\n"
        f"[yellow]Platforms:[/yellow] {', '.join(platforms)}\n"
        f"[yellow]Model:[/yellow] {provider}/{model}",
        title="Configuration",
    ))
    
    if dry_run:
        console.print("\n[yellow]Dry run mode - showing plan only[/yellow]\n")
        _show_generation_plan(requirement, language, platforms)
        return
    
    # Check API key
    api_key = _get_api_key(provider)
    if not api_key:
        console.print(f"[red]Error: No API key found for {provider}[/red]")
        console.print(f"Set it with: rebot config set {provider}_api_key YOUR_KEY")
        sys.exit(1)
    
    try:
        from rebot.auto.generate import OneShotGenerator, GeneratorConfig
        from rebot.models.universal import LLMProvider, ProviderConfig
        from rebot.models.providers import MODEL_PROVIDERS
        
        # Create model
        provider_enum = LLMProvider(provider)
        config = ProviderConfig(
            provider=provider_enum,
            api_key=api_key,
            model=model,
        )
        
        # Get model class
        model_instance = MODEL_PROVIDERS.get(provider_enum.value)(config)
        
        # Create generator
        generator = OneShotGenerator(model=model_instance, root=output_path)
        gen_config = GeneratorConfig(
            language=language,
            platforms=platforms,
            ai_codegen=not no_ai_codegen,
            metagpt_chain=not no_metagpt,
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating...", total=None)
            
            def on_progress(stage: str, message: str) -> None:
                progress.update(task, description=f"[cyan]{stage}[/cyan]: {message}")
            
            generator.generate(requirement, gen_config, progress_callback=on_progress)
        
        console.print(f"\n[green]✓ Generation complete![/green]")
        console.print(f"Output: {output_path}")
        
    except ImportError as e:
        console.print(f"[red]Import error: {e}[/red]")
        console.print("Some dependencies may be missing. Run: pip install rebot[all]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.get("verbose"):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


def _show_generation_plan(requirement: str, language: str, platforms: List[str]) -> None:
    """Show the generation plan without executing."""
    table = Table(title="Generation Plan")
    table.add_column("Step", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")
    
    steps = [
        ("1. Spec Compilation", "Parse requirement into structured spec", "Pending"),
        ("2. Architecture Design", "Generate system architecture", "Pending"),
        ("3. UI Design", "Create UI/UX design spec", "Pending"),
        ("4. Task Planning", "Break down into development tasks", "Pending"),
        ("5. Code Generation", f"Generate {language} code", "Pending"),
    ]
    
    for platform in platforms:
        steps.append((f"6. {platform.title()} Build", f"Build {platform} application", "Pending"))
    
    steps.append(("7. Quality Gate", "Run quality checks", "Pending"))
    steps.append(("8. Documentation", "Generate documentation", "Pending"))
    
    for step in steps:
        table.add_row(*step)
    
    console.print(table)


# ============================================================================
# Init Command
# ============================================================================

@main.command()
@click.argument("project_name")
@click.option("--template", "-t", default="default", help="Project template")
@click.option("--language", "-l", default="python", help="Backend language")
@click.pass_context
def init(ctx: click.Context, project_name: str, template: str, language: str) -> None:
    """Initialize a new Rebot project.
    
    Examples:
    
        rebot init my-app
        
        rebot init my-api --template backend-only
    """
    project_path = Path(project_name).resolve()
    
    if project_path.exists():
        console.print(f"[red]Error: Directory {project_name} already exists[/red]")
        sys.exit(1)
    
    console.print(f"[cyan]Creating project: {project_name}[/cyan]")
    
    # Create directory structure
    project_path.mkdir(parents=True)
    (project_path / "docs").mkdir()
    (project_path / "backend").mkdir()
    (project_path / "frontend").mkdir()
    (project_path / "tests").mkdir()
    
    # Create config file
    config = {
        "project": project_name,
        "language": language,
        "template": template,
        "version": "0.1.0",
    }
    (project_path / "rebot.yaml").write_text(
        f"# Rebot Project Configuration\n"
        f"project: {project_name}\n"
        f"language: {language}\n"
        f"template: {template}\n"
        f"version: 0.1.0\n"
        f"\n"
        f"# LLM Configuration\n"
        f"model: gpt-4\n"
        f"provider: openai\n"
        f"\n"
        f"# Generation Options\n"
        f"platforms:\n"
        f"  - web\n"
        f"\n"
        f"# Quality Gates\n"
        f"quality:\n"
        f"  lint: true\n"
        f"  test: true\n"
        f"  security: true\n",
        encoding="utf-8",
    )
    
    # Create README
    (project_path / "README.md").write_text(
        f"# {project_name}\n\n"
        f"Generated by Rebot.\n\n"
        f"## Getting Started\n\n"
        f"```bash\n"
        f"cd {project_name}\n"
        f"rebot generate \"Your requirement here\"\n"
        f"```\n",
        encoding="utf-8",
    )
    
    console.print(f"[green]✓ Project created: {project_path}[/green]")
    console.print(f"\nNext steps:")
    console.print(f"  cd {project_name}")
    console.print(f'  rebot generate "Your app description"')


# ============================================================================
# Config Command
# ============================================================================

@main.group()
def config() -> None:
    """Manage Rebot configuration."""
    pass


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a configuration value.
    
    Examples:
    
        rebot config set openai_api_key sk-xxx
        
        rebot config set default_model gpt-4
    """
    config_path = _get_config_path()
    config_data = _load_config(config_path)
    
    config_data[key] = value
    _save_config(config_path, config_data)
    
    # Mask sensitive values in output
    display_value = value
    if "api_key" in key.lower() or "token" in key.lower():
        display_value = value[:8] + "..." if len(value) > 8 else "***"
    
    console.print(f"[green]✓ Set {key} = {display_value}[/green]")


@config.command("get")
@click.argument("key", required=False)
def config_get(key: Optional[str]) -> None:
    """Get configuration value(s).
    
    Examples:
    
        rebot config get
        
        rebot config get default_model
    """
    config_path = _get_config_path()
    config_data = _load_config(config_path)
    
    if key:
        value = config_data.get(key)
        if value:
            # Mask sensitive values
            if "api_key" in key.lower() or "token" in key.lower():
                value = value[:8] + "..." if len(value) > 8 else "***"
            console.print(f"{key} = {value}")
        else:
            console.print(f"[yellow]Key not found: {key}[/yellow]")
    else:
        table = Table(title="Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")
        
        for k, v in sorted(config_data.items()):
            # Mask sensitive values
            if "api_key" in k.lower() or "token" in k.lower():
                v = v[:8] + "..." if len(str(v)) > 8 else "***"
            table.add_row(k, str(v))
        
        console.print(table)


@config.command("list")
def config_list() -> None:
    """List all configuration values."""
    config_get(None)


# ============================================================================
# Run Command
# ============================================================================

@main.command()
@click.argument("workflow_path", type=click.Path(exists=True))
@click.option("--input", "-i", "inputs", multiple=True, help="Workflow inputs (key=value)")
@click.pass_context
def run(ctx: click.Context, workflow_path: str, inputs: tuple) -> None:
    """Run a workflow from YAML file.
    
    Examples:
    
        rebot run workflow.yaml
        
        rebot run deploy.yaml --input env=production
    """
    workflow_file = Path(workflow_path)
    
    console.print(f"[cyan]Running workflow: {workflow_file.name}[/cyan]")
    
    # Parse inputs
    input_dict = {}
    for inp in inputs:
        if "=" in inp:
            k, v = inp.split("=", 1)
            input_dict[k] = v
    
    try:
        import yaml
        
        with open(workflow_file, "r", encoding="utf-8") as f:
            workflow_data = yaml.safe_load(f)
        
        console.print(f"[green]Workflow loaded: {workflow_data.get('name', 'Unnamed')}[/green]")
        
        # TODO: Execute workflow
        console.print("[yellow]Workflow execution not yet implemented[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# ============================================================================
# Info Command
# ============================================================================

@main.command()
def info() -> None:
    """Show Rebot system information."""
    import platform
    
    table = Table(title="Rebot System Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Version", "0.1.0")
    table.add_row("Python", platform.python_version())
    table.add_row("Platform", platform.system())
    table.add_row("Architecture", platform.machine())
    
    # Check installed providers
    providers = []
    try:
        import openai
        providers.append("openai")
    except ImportError:
        pass
    
    try:
        import anthropic
        providers.append("anthropic")
    except ImportError:
        pass
    
    try:
        import google.generativeai
        providers.append("google")
    except ImportError:
        pass
    
    table.add_row("Installed Providers", ", ".join(providers) or "None")
    
    # Check config
    config_path = _get_config_path()
    table.add_row("Config Path", str(config_path))
    table.add_row("Config Exists", "Yes" if config_path.exists() else "No")
    
    console.print(table)


# ============================================================================
# Test Command
# ============================================================================

@main.command()
@click.option("--coverage", is_flag=True, help="Run with coverage")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def test(coverage: bool, verbose: bool) -> None:
    """Run Rebot test suite."""
    import subprocess
    
    cmd = ["pytest"]
    if coverage:
        cmd.extend(["--cov=rebot", "--cov-report=term-missing"])
    if verbose:
        cmd.append("-v")
    
    console.print(f"[cyan]Running: {' '.join(cmd)}[/cyan]")
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    sys.exit(result.returncode)


# ============================================================================
# Helper Functions
# ============================================================================

def _get_config_path() -> Path:
    """Get the path to the config file."""
    config_dir = Path.home() / ".rebot"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.json"


def _load_config(config_path: Path) -> dict:
    """Load configuration from file."""
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_config(config_path: Path, config_data: dict) -> None:
    """Save configuration to file."""
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)


def _get_api_key(provider: str) -> Optional[str]:
    """Get API key for a provider."""
    # Check environment variables first
    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "azure": "AZURE_OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }
    
    env_var = env_map.get(provider.lower())
    if env_var and os.environ.get(env_var):
        return os.environ.get(env_var)
    
    # Check config file
    config_path = _get_config_path()
    config_data = _load_config(config_path)
    return config_data.get(f"{provider}_api_key")


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    main()
