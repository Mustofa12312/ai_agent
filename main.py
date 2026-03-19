#!/usr/bin/env python3
"""
🤖 AI Agent — main.py
Rich/Typer CLI entrypoint with interactive chat, config, and history commands.
"""
import sys
import os
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.text import Text
from rich import box
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer(
    name="ai-agent",
    help="🤖 Modular AI Agent — Gemini + Tools + Memory",
    add_completion=False,
)
console = Console()

# ─────────────────────────────────────────────────────────────────────────────
#  Banner
# ─────────────────────────────────────────────────────────────────────────────

BANNER = """
[bold cyan]  ╔══════════════════════════════════════════╗[/bold cyan]
[bold cyan]  ║   🤖  AI AGENT  —  Powered by Gemini     ║[/bold cyan]
[bold cyan]  ╚══════════════════════════════════════════╝[/bold cyan]
[dim]  Tools · Memory · Scheduler · Plugins[/dim]
"""


def print_banner(ai_name: str, user_name: str, personality: str) -> None:
    console.print(BANNER)
    console.print(
        Panel(
            f"[bold green]Halo, {user_name}![/bold green] "
            f"Aku [bold cyan]{ai_name}[/bold cyan] siap membantu. "
            f"[dim](personality: {personality})[/dim]\n"
            f"[dim]Ketik [bold]help[/bold] untuk daftar perintah, "
            f"[bold]exit[/bold] atau [bold]quit[/bold] untuk keluar.[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Special CLI commands (inside chat loop)
# ─────────────────────────────────────────────────────────────────────────────

def handle_special_command(cmd: str, agent, scheduler) -> tuple:
    """Return (handled: bool, output: str | None)."""
    cmd_lower = cmd.strip().lower()

    if cmd_lower in ("exit", "quit", "keluar", "bye"):
        return True, "EXIT"

    if cmd_lower in ("help", "bantuan", "?"):
        return True, _help_text()

    if cmd_lower in ("clear", "reset", "bersih"):
        agent.clear_session()
        return True, "✅ Memori sesi dihapus."

    if cmd_lower in ("history", "riwayat"):
        return True, _show_history(agent)

    if cmd_lower in ("tools", "tool"):
        return True, _list_tools(agent)

    if cmd_lower in ("facts", "fakta", "ingatan"):
        return True, _show_facts(agent)

    if cmd_lower.startswith("ya hapus "):
        filename = cmd_lower[len("ya hapus "):].strip()
        result = agent.registry.run_tool("file_tool", action="delete", path=filename)
        return True, result

    if cmd_lower in ("jadwal", "scheduler", "schedule"):
        return True, scheduler.list_jobs()

    return False, None


def _help_text() -> str:
    table = Table(title="📖 Perintah Tersedia", box=box.ROUNDED, style="cyan")
    table.add_column("Perintah", style="bold green")
    table.add_column("Fungsi")
    rows = [
        ("help / ?", "Tampilkan daftar perintah ini"),
        ("history / riwayat", "Lihat percakapan terakhir"),
        ("tools", "Lihat semua tools aktif"),
        ("facts / ingatan", "Lihat semua fakta yang diingat AI"),
        ("clear / reset", "Hapus memori sesi saat ini"),
        ("jadwal", "Lihat jadwal/reminder aktif"),
        ("ya hapus <file>", "Konfirmasi penghapusan file"),
        ("exit / quit", "Keluar dari AI Agent"),
        ("", ""),
        ("Contoh input:", ""),
        ("cuaca di Bandung", "Cuaca real-time"),
        ("jam berapa sekarang?", "Waktu sekarang"),
        ("buat file todo.txt", "Buat file di workspace"),
        ("baca file todo.txt", "Baca isi file"),
        ("hapus file todo.txt", "Hapus file (butuh konfirmasi)"),
        ("cari berita AI terbaru", "Web search"),
        ("berita AI hari ini", "Agregasi berita"),
        ("ingat bahwa saya suka kopi", "Simpan preferensi"),
        ("ingatkan saya jam 5 sore", "Set reminder"),
        ("harga bitcoin", "Harga crypto (plugin)"),
    ]
    for r in rows:
        table.add_row(*r)
    console.print(table)
    return ""


def _show_history(agent) -> str:
    history = agent.get_history(limit=20)
    if not history:
        return "📭 Belum ada riwayat percakapan."
    table = Table(title="📜 Riwayat Percakapan", box=box.SIMPLE, min_width=60)
    table.add_column("Waktu", style="dim", width=12)
    table.add_column("Role", style="bold", width=8)
    table.add_column("Pesan")
    for msg in history:
        role_str = "👤 User" if msg["role"] == "user" else "🤖 AI"
        ts = msg.get("timestamp", "")[:16]
        content = msg["content"][:80] + ("..." if len(msg["content"]) > 80 else "")
        table.add_row(ts, role_str, content)
    console.print(table)
    return ""


def _list_tools(agent) -> str:
    table = Table(title="🛠️ Tools Aktif", box=box.ROUNDED, style="green")
    table.add_column("Nama", style="bold cyan")
    table.add_column("Deskripsi")
    for tool in agent.registry.all_tools():
        table.add_row(tool.name, tool.description[:80])
    console.print(table)
    return ""


def _show_facts(agent) -> str:
    facts = agent.get_facts()
    if not facts:
        return "🧠 Belum ada fakta yang tersimpan."
    table = Table(title="🧠 Fakta Tersimpan", box=box.ROUNDED)
    table.add_column("Key", style="bold yellow")
    table.add_column("Value")
    table.add_column("Waktu", style="dim")
    for f in facts:
        table.add_row(f["key"], f["value"], f["timestamp"][:10])
    console.print(table)
    return ""


# ─────────────────────────────────────────────────────────────────────────────
#  Main chat command
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def chat(
    session: str = typer.Option("", "--session", "-s", help="ID sesi (opsional)"),
):
    """💬 Mulai sesi chat interaktif dengan AI Agent."""
    from core.agent import Agent
    from scheduler.scheduler import Scheduler

    # Boot
    with console.status("[bold cyan]Menginisialisasi AI Agent...[/bold cyan]", spinner="dots"):
        try:
            agent = Agent()
            scheduler = Scheduler(
                notify_callback=lambda msg: console.print(f"\n[bold yellow]⏰ {msg}[/bold yellow]\n")
            )
        except Exception as e:
            console.print(f"[bold red]❌ Gagal menginisialisasi agent: {e}[/bold red]")
            raise typer.Exit(1)

    cfg = agent.config
    ai_name = cfg.get("ai_name", "Madura Ai")
    user_name = cfg.get("user_name", "Boss")
    personality = cfg.get("personality", "santai")

    console.clear()
    print_banner(ai_name, user_name, personality)

    # --- Main loop ---
    while True:
        try:
            console.print()
            user_input = Prompt.ask(f"[bold green]{user_name}[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye! 👋[/dim]")
            break

        if not user_input:
            continue

        # Handle special commands
        handled, output = handle_special_command(user_input, agent, scheduler)
        if handled:
            if output == "EXIT":
                console.print(f"\n[bold cyan]Sampai jumpa, {user_name}! 👋[/bold cyan]")
                break
            if output:
                console.print(output)
            continue

        # Scheduler commands
        sched_keywords = ["ingatkan", "remind", "jadwalkan", "alarm", "tiap pagi", "tiap hari"]
        if any(kw in user_input.lower() for kw in sched_keywords):
            with console.status("[dim]Menyiapkan pengingat...[/dim]", spinner="dots2"):
                result = scheduler.parse_and_schedule(user_input)
            console.print(Panel(result, border_style="yellow", padding=(0, 1)))
            continue

        # File delete confirmation
        is_delete = (
            any(kw in user_input.lower() for kw in ["hapus file", "delete file", "rm file"])
        )

        # Stream response
        with console.status(f"[dim]{ai_name} sedang berpikir...[/dim]", spinner="bouncingBar"):
            response = agent.chat(user_input, confirm_delete=False)

        # Render response
        if response:
            try:
                # Try to render as Markdown for rich formatting
                md = Markdown(response)
                console.print(
                    Panel(
                        md,
                        title=f"[bold cyan]🤖 {ai_name}[/bold cyan]",
                        border_style="cyan",
                        padding=(0, 1),
                    )
                )
            except Exception:
                console.print(
                    Panel(
                        response,
                        title=f"[bold cyan]🤖 {ai_name}[/bold cyan]",
                        border_style="cyan",
                    )
                )

    scheduler.shutdown()


# ─────────────────────────────────────────────────────────────────────────────
#  Config command
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def config():
    """⚙️ Konfigurasi identitas dan personality AI Agent."""
    from config.config_manager import load_config, save_config

    cfg = load_config()
    console.print(Panel("[bold]⚙️ Konfigurasi AI Agent[/bold]", border_style="cyan"))

    console.print(f"\nKonfigurasi saat ini:")
    console.print(f"  Nama AI     : [cyan]{cfg.get('ai_name', 'Madura Ai')}[/cyan]")
    console.print(f"  Nama User   : [green]{cfg.get('user_name', 'Boss')}[/green]")
    console.print(f"  Personality : [yellow]{cfg.get('personality', 'santai')}[/yellow]")
    console.print()

    ai_name = Prompt.ask("Nama AI", default=cfg.get("ai_name", "Madura Ai"))
    user_name = Prompt.ask("Nama kamu (dipanggil AI)", default=cfg.get("user_name", "Boss"))
    personality = Prompt.ask(
        "Personality [santai/formal/hacker]",
        default=cfg.get("personality", "santai"),
        choices=["santai", "formal", "hacker"],
    )

    cfg["ai_name"] = ai_name
    cfg["user_name"] = user_name
    cfg["personality"] = personality
    save_config(cfg)

    console.print(f"\n[green]✅ Konfigurasi disimpan![/green]")
    console.print(f"  Nama AI: [cyan]{ai_name}[/cyan] | User: [green]{user_name}[/green] | Personality: [yellow]{personality}[/yellow]")


# ─────────────────────────────────────────────────────────────────────────────
#  History command
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def history(limit: int = typer.Option(20, "--limit", "-n", help="Jumlah pesan yang ditampilkan")):
    """📜 Lihat riwayat percakapan dari long-term memory."""
    from memory.long_term import LongTermMemory
    mem = LongTermMemory()
    msgs = mem.get_recent_conversations(limit=limit)
    if not msgs:
        console.print("📭 Belum ada riwayat percakapan tersimpan.")
        return
    table = Table(title=f"📜 Riwayat Terakhir ({len(msgs)} pesan)", box=box.SIMPLE, min_width=60)
    table.add_column("Waktu", style="dim", width=12)
    table.add_column("Role", style="bold", width=10)
    table.add_column("Pesan")
    for msg in msgs:
        role_str = "👤 User" if msg["role"] == "user" else "🤖 AI"
        ts = msg.get("timestamp", "")[:16]
        content = msg["content"][:100] + ("..." if len(msg["content"]) > 100 else "")
        table.add_row(ts, role_str, content)
    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
#  Clear command
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def clear(
    all_data: bool = typer.Option(False, "--all", "-a", help="Hapus semua data (termasuk long-term)"),
):
    """🗑️ Hapus memori sesi atau semua data."""
    if all_data:
        if Confirm.ask("[bold red]Yakin hapus SEMUA data (percakapan, fakta, preferensi)?[/bold red]"):
            from memory.long_term import LongTermMemory
            LongTermMemory().clear_all()
            console.print("[green]✅ Semua data dihapus.[/green]")
    else:
        console.print("[green]✅ Memori sesi (short-term) dihapus.[/green]")
        console.print("[dim](long-term memory tetap tersimpan)[/dim]")


# ─────────────────────────────────────────────────────────────────────────────
#  Status command
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def status():
    """📊 Tampilkan status sistem AI Agent."""
    from config.config_manager import load_config
    from memory.long_term import LongTermMemory

    cfg = load_config()
    mem = LongTermMemory()
    facts = mem.get_all_facts()
    recent = mem.get_recent_conversations(limit=1)

    gemini_ok = bool(os.getenv("GEMINI_API_KEY"))
    openai_ok = bool(os.getenv("OPENAI_API_KEY"))
    groq_ok = bool(os.getenv("GROQ_API_KEY"))
    serpapi_ok = bool(os.getenv("SERPAPI_KEY"))
    openweather_ok = bool(os.getenv("OPENWEATHER_API_KEY"))

    table = Table(title="📊 Status AI Agent", box=box.ROUNDED, border_style="cyan")
    table.add_column("Komponen", style="bold")
    table.add_column("Status")

    table.add_row("Nama AI", f"[cyan]{cfg.get('ai_name', 'Madura Ai')}[/cyan]")
    table.add_row("User", f"[green]{cfg.get('user_name', 'Boss')}[/green]")
    table.add_row("Personality", cfg.get("personality", "santai"))
    table.add_row("Gemini API", "[green]✅ Tersedia[/green]" if gemini_ok else "[red]❌ Tidak ada key[/red]")
    table.add_row("OpenAI API", "[green]✅ Tersedia[/green]" if openai_ok else "[yellow]⚠️ Tidak dikonfigurasi[/yellow]")
    table.add_row("Groq API", "[green]✅ Tersedia[/green]" if groq_ok else "[yellow]⚠️ Tidak dikonfigurasi[/yellow]")
    table.add_row("SerpAPI", "[green]✅ Tersedia[/green]" if serpapi_ok else "[yellow]⚠️ Tidak dikonfigurasi[/yellow]")
    table.add_row("OpenWeather API", "[green]✅ Tersedia[/green]" if openweather_ok else "[yellow]⚠️ Tidak dikonfigurasi[/yellow]")
    table.add_row("Fakta tersimpan", str(len(facts)))
    table.add_row("Percakapan terakhir", recent[0]["timestamp"][:16] if recent else "Belum ada")

    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
#  Web UI command
# ─────────────────────────────────────────────────────────────────────────────

@app.command()
def web(port: int = typer.Option(8000, "--port", "-p", help="Port untuk Web UI")):
    """🌐 Jalankan AI Agent dalam mode Web Browser (Visual UI lokal)."""
    import uvicorn
    import socket
    
    # Deteksi IP lokal jaringan WiFi
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()
        
    console.print(f"[bold green]🚀 Menyiapkan Web Server...[/bold green]")
    console.print(f"👉 Akses di [yellow]Laptop Anda[/yellow]: [link=http://localhost:{port}/]http://localhost:{port}/[/link]")
    if local_ip != '127.0.0.1':
        console.print(f"👉 Akses di [yellow]HP Anda (WiFi yang sama)[/yellow]: [link=http://{local_ip}:{port}/]http://{local_ip}:{port}/[/link]")
        
    try:
        # Ubah host dari 127.0.0.1 menjadi 0.0.0.0 agar port terbuka ke WiFi
        uvicorn.run("web_server:app", host="0.0.0.0", port=port, reload=True)
    except KeyboardInterrupt:
        console.print("\n[dim]Server dimatikan. Bye! 👋[/dim]")


# ─────────────────────────────────────────────────────────────────────────────
#  Default: run chat if no subcommand
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        chat()


if __name__ == "__main__":
    app()
