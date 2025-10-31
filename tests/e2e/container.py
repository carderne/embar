import subprocess
import time
from types import TracebackType
from typing import final

import psycopg

MAX_TRIES = 2


@final
class PostgresContainer:
    def __init__(self, image: str, port: int):
        self.image = image
        self.port = port
        self.username = "pg"
        self.password = "pw"
        self.dbname = "db"
        self._container_id: str | None = None

    def start(self, tries: int = 1) -> None:
        try:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "-p",
                    f"{self.port}:5432",
                    "-e",
                    f"POSTGRES_USER={self.username}",
                    "-e",
                    f"POSTGRES_PASSWORD={self.password}",
                    "-e",
                    f"POSTGRES_DB={self.dbname}",
                    self.image,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self._container_id = result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if tries < MAX_TRIES:
                self.port = self.port + 1
                self.start(tries + 1)
            else:
                raise e
        self._wait_until_ready()

    def _wait_until_ready(self, timeout: int = 30) -> None:
        start = time.time()
        assert isinstance(self._container_id, str)
        while time.time() - start < timeout:
            try:
                # Actually try to connect to verify the database is ready
                conn = psycopg.connect(self.get_connection_url(), connect_timeout=1)
                conn.close()
                return
            except (psycopg.OperationalError, psycopg.Error):
                time.sleep(0.1)
        raise TimeoutError("Postgres container failed to become ready")

    def stop(self) -> None:
        if self._container_id:
            subprocess.run(["docker", "stop", self._container_id], capture_output=True)
            self._container_id = None

    def __enter__(self) -> "PostgresContainer":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop()

    def __del__(self) -> None:
        try:
            self.stop()
        except Exception:
            pass

    def get_connection_url(self) -> str:
        return f"postgresql://{self.username}:{self.password}@localhost:{self.port}/{self.dbname}"

    def get_container_host_ip(self) -> str:
        return "localhost"

    def get_exposed_port(self, _: int) -> int:
        return self.port
