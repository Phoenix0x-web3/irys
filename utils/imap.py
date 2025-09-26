import asyncio
from email import message_from_bytes, utils
from imaplib import IMAP4, IMAP4_SSL
from time import time
from typing import List, Union

from bs4 import BeautifulSoup
from loguru import logger

from utils.db_api.models import Wallet


class MailTimedOut(Exception):
    """Custom exception for email timeout errors."""

    pass


class Mail:
    __module__ = "IMAP Mail"

    def __init__(self, user: Wallet):
        """Initialize Mail with login credentials if provided."""
        self.user = user
        self.mail_data = user.email_data
        self.authed = False
        self.imap = None
        self.fake_mail = None
        if "icloud" in self.mail_data:
            self.mail_login, self.mail_pass, self.fake_mail = self.mail_data.split(":")
        else:
            self.mail_login, self.mail_pass = self.mail_data.split(":", 1)
        try:
            self._login(only_check=True)
        except ValueError as e:
            logger.error(f"{self.user} Invalid mail_data format: {e}")
            raise

    def _login(self, only_check: bool = False) -> None:
        """Attempt to log in to the IMAP server."""
        try:
            imap_port = 993
            if "icloud" in self.mail_data:
                imap_server = "imap.mail.me.com"
            elif "gmx" in self.mail_data:
                imap_server = "imap.gmx.com"
            else:
                raise Exception(f"{self.user} {self.__module__} Imap server it's not icloud or gmx")
            self.imap = IMAP4_SSL(host=imap_server, port=imap_port)
            self.imap.login(self.mail_login, self.mail_pass)
            self.authed = True
        except IMAP4.error as error:
            error_msg = error.args[0].decode() if isinstance(error.args[0], bytes) else str(error)
            if only_check:
                logger.error(f"{self.user} Email login failed for {self.mail_login}: {error_msg}")
            else:
                raise Exception(f"{self.user} {self.__module__} | Email login failed for {self.mail_login}: {error_msg}")

    async def find_mail(
        self,
        msg_from: Union[str, List[str]],
        subject: str | None = None,
        part_subject: str | None = None,
    ) -> BeautifulSoup:
        """Search INBOX and Spam, collect matching emails, sort by Date, return newest."""
        if isinstance(msg_from, str):
            msg_from = [msg_from]

        self._login()
        start_time = time()
        first = True
        if not self.imap:
            raise Exception(f" {self.user} {self.__module__} | IMAP connection not established")

        folders = ["INBOX", "Spam", "Junk"]

        while time() < start_time + 120:
            try:
                await asyncio.sleep(10)

                all_candidates: list[tuple[float, object]] = []

                for mbox in folders:
                    typ, _ = self.imap.select(mbox, readonly=True)
                    if typ != "OK":
                        continue

                    # Collect IDs from all specified senders in this folder
                    ids: set[bytes] = set()
                    for sender in msg_from:
                        if self.fake_mail:
                            typ, data = self.imap.search(None, "FROM", sender, "TO", self.fake_mail)
                            if typ == "OK" and data and data[0]:
                                ids.update(data[0].split())
                        else:
                            typ, data = self.imap.search(None, "FROM", sender)
                            if typ == "OK" and data and data[0]:
                                ids.update(data[0].split())

                    if not ids:
                        continue

                    # Fetch and filter messages, remember their Date as timestamp
                    for msg_id in ids:
                        typ, fetched = self.imap.fetch(msg_id, "(BODY.PEEK[])")
                        if typ != "OK" or not fetched or not fetched[0]:
                            continue

                        raw_email = fetched[0][1]
                        msg = message_from_bytes(raw_email)

                        subj = msg.get("Subject") or ""
                        if subject and subj != subject:
                            continue
                        if part_subject and part_subject not in subj:
                            continue

                        try:
                            dt = utils.parsedate_to_datetime(msg.get("Date")).timestamp()
                        except Exception:
                            dt = 0.0

                        all_candidates.append((dt, msg))

                if all_candidates:
                    # newest by Date
                    _, newest = max(all_candidates, key=lambda t: t[0])
                    return self._format_mail(newest)

                if first:
                    logger.info(f"Waiting for mail from {', '.join(msg_from)} in INBOX/Spam")
                    first = False

            except Exception as e:
                logger.error(f"{self.user} Error while searching email: {e}")
                await asyncio.sleep(5)

        raise MailTimedOut(f"Timeout waiting for email from {', '.join(msg_from)}")

    def _format_mail(self, mail) -> BeautifulSoup:
        """Extract and parse HTML content from an email."""
        try:
            if not mail.is_multipart():
                payload = mail.get_payload(decode=True)
                charset = mail.get_content_charset() or "utf-8"
                return BeautifulSoup(payload.decode(charset), "html.parser")

            for part in mail.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "iso-8859-1"
                    return BeautifulSoup(payload.decode(charset), "html.parser")

            raise ValueError("No HTML content found in email")
        except Exception as e:
            logger.error(f"{self.user} Error formatting email: {e}")
            raise

    def __del__(self):
        """Ensure IMAP connection is closed."""
        if self.imap and self.authed:
            try:
                self.imap.logout()
            except Exception as e:
                logger.error(f"{self.user} Error during IMAP logout: {e}")
