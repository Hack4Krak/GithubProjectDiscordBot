from rich import print as rich_print


def bot(text: str):
    rich_print("[bold blue]BOT: [/bold blue]" + text)


def bot_info(text: str):
    bot(f"[bold green]INFO:[/bold green] {text}")


# Currently unused:
# def bot_warning(text: str):
#     bot(f"[bold yellow]WARNING:[/bold yellow] {text}")


def bot_error(text: str):
    bot(f"[bold red]ERROR:[/bold red] {text}")


def server(text: str):
    rich_print("[bold purple]SERVER: [/bold purple]" + text)


def server_info(text: str):
    server(f"[bold green]INFO:[/bold green] {text}")


def server_warning(text: str):
    server(f"[bold yellow]WARNING:[/bold yellow] {text}")


def server_error(text: str):
    server(f"[bold red]ERROR:[/bold red] {text}")
