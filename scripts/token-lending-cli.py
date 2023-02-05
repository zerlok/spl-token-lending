import argparse
import typing as t
import uuid
from pathlib import Path

import requests
from requests import Session
from solders.keypair import Keypair


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-C", "--config", type=Path, default=Path.cwd() / "spl-token-lending.keypair")
    parser.add_argument("-U", "--url", type=str, default="http://localhost:8000")
    parser.add_argument("command", type=str, choices=list(CLI_COMMANDS))

    return parser.parse_args()


def get_or_create_keypair_config(config_path: Path) -> Keypair:
    if not config_path.exists():
        kp = Keypair()
        with config_path.open("w") as f:
            f.write(str(kp))

    else:
        with config_path.open("r") as f:
            kp = Keypair.from_base58_string(f.read())

    return kp


def show_loans(session: Session, url: str, kp: Keypair) -> None:
    loans_resp = session.get(f"{url}/loans", params={"wallet": str(kp.pubkey())})

    print(f"loans: {loans_resp.json()}")


def process_lending(session: Session, url: str, kp: Keypair) -> None:
    amount = int(input("loan amount: "))
    loan_init_resp = session.put(f"{url}/loans", json={"wallet": str(kp.pubkey()), "amount": amount})

    init_data = loan_init_resp.json()
    print(f"loan initialized: {init_data}")

    loan_id = uuid.UUID(init_data["id"])
    confirm = input("submit [y/n]: ")
    if confirm.strip().lower() != "y":
        print("loan declined")
        return

    sig = kp.sign_message(loan_id.bytes)
    print("confirming the loan with keypair signature (this can take a while) ...")
    loan_submit_resp = session.patch(f"{url}/loans/{loan_id}", json={"signature": str(sig)})

    print(f"loan submitted: {loan_submit_resp.json()}")


CLI_COMMANDS: t.Mapping[str, t.Callable[[Session, str, Keypair], None]] = {
    "list": show_loans,
    "lend": process_lending,
}


def main() -> None:
    ns = parse_args()

    url: str = ns.url
    kp = get_or_create_keypair_config(ns.config)

    print(f"user keypair: {kp}")
    print(f"user pubkey: {kp.pubkey()}")

    with requests.session() as session:
        cmd = CLI_COMMANDS.get(ns.command)
        cmd(session, url, kp)


if __name__ == "__main__":
    main()
