"""Per-cell publish records shared between publish-oci and publish-site.

A record captures everything publish-site needs to merge one (app, arch) push
into the static OCI index, without re-running skopeo against the registry:
the OCI labels, digest, ref, registry URL, image name, and the channel tag.

Records live under ``<records-dir>/<app-id>-<arch>/``. publish-oci writes one
per cell; publish-site iterates the tree in any order.
"""

import dataclasses
import json
import pathlib
from collections.abc import Iterator


@dataclasses.dataclass(frozen=True)
class Record:
    """Immutable snapshot of one published (app, arch) cell.

    Carries the OCI coordinates (registry, name, digest, tag), the Flatpak ref,
    and the channel branch — everything publish-site needs without re-querying
    the registry.
    """

    app_id: str
    arch: str
    branch: str
    name: str
    registry: str
    digest: str
    ref: str
    tag: str

    def __post_init__(self) -> None:
        if not self.app_id or not self.arch:
            raise ValueError("Record requires app-id and arch")
        # Defense in depth: cell_dir builds a path from these fields, so reject
        # separators and traversal segments even though plan.py's validate()
        # should already have caught them upstream.
        for name, value in (("app_id", self.app_id), ("arch", self.arch)):
            if "/" in value or "\\" in value or value in ("..", "."):
                raise ValueError(f"Record {name!r} must not contain path separators or traversal segments")

    def cell_dir(self, root: pathlib.Path) -> pathlib.Path:
        """Return the cell directory path for this record under *root*.

        :param root: records root directory.
        :returns: ``root/<app_id>-<arch>``.
        """
        return root / f"{self.app_id}-{self.arch}"


def write_record(
    root: pathlib.Path,
    record: Record,
    *,
    labels: dict[str, str],
) -> pathlib.Path:
    """Write *record* and *labels* into their cell directory under *root*.

    Creates the cell directory if it does not exist. Overwrites any existing
    ``record.json`` / ``labels.json`` in place.

    :param root: records root directory.
    :param record: the record to persist.
    :param labels: OCI label dict to write as ``labels.json``.
    :returns: the cell directory path.
    """
    cell = record.cell_dir(root)
    cell.mkdir(parents=True, exist_ok=True)
    payload = {
        "app-id": record.app_id,
        "arch": record.arch,
        "branch": record.branch,
        "name": record.name,
        "registry": record.registry,
        "digest": record.digest,
        "ref": record.ref,
        "tag": record.tag,
    }
    (cell / "record.json").write_text(json.dumps(payload, indent=2) + "\n")
    (cell / "labels.json").write_text(json.dumps(labels, indent=2) + "\n")
    return cell


def iter_records(
    root: pathlib.Path,
) -> Iterator[tuple[Record, dict[str, str]]]:
    """Yield ``(Record, labels)`` for every complete cell under *root*.

    Iterates cells in sorted order so callers get deterministic output.
    Returns immediately if *root* is not a directory. Silently skips any
    subdirectory missing ``record.json`` or ``labels.json`` — partial cells
    from interrupted publish-oci runs are not an error.

    :param root: records root directory to scan.
    :returns: generator of ``(Record, labels dict)`` tuples.
    """
    if not root.is_dir():
        return
    for cell in sorted(p for p in root.iterdir() if p.is_dir()):
        rec_path = cell / "record.json"
        lbl_path = cell / "labels.json"
        if not rec_path.is_file() or not lbl_path.is_file():
            continue
        rec_data = json.loads(rec_path.read_text())
        labels = json.loads(lbl_path.read_text())
        yield (
            Record(
                app_id=rec_data["app-id"],
                arch=rec_data["arch"],
                branch=rec_data["branch"],
                name=rec_data["name"],
                registry=rec_data["registry"],
                digest=rec_data["digest"],
                ref=rec_data["ref"],
                tag=rec_data["tag"],
            ),
            labels,
        )
