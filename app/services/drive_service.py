"""Сведения о локальных накопителях и файловой системе."""

from __future__ import annotations

from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class DriveInfo:
    device: str
    mountpoint: str
    fstype: str
    total: int
    used: int
    free: int
    ready: bool

    @property
    def percent_used(self) -> float:
        return (self.used / self.total * 100) if self.total else 0.0


def list_drives() -> list[DriveInfo]:
    drives: list[DriveInfo] = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            # диск может быть не готов (например, пустой привод)
            drives.append(
                DriveInfo(part.device, part.mountpoint, part.fstype, 0, 0, 0, ready=False)
            )
            continue
        drives.append(
            DriveInfo(
                device=part.device,
                mountpoint=part.mountpoint,
                fstype=part.fstype,
                total=usage.total,
                used=usage.used,
                free=usage.free,
                ready=True,
            )
        )
    return drives
