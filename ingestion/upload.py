"""Upload the bronze Parquet files to the ADLS Gen2 data lake.

Files are immutable (the run id is part of the name), so a file that is already
in the lake with the same size is skipped and the upload can be repeated safely.
It uses the signed-in Azure CLI identity (az login); no keys are stored.
"""

import argparse
import os
from pathlib import Path

from azure.identity import AzureCliCredential
from azure.storage.filedatalake import DataLakeServiceClient, FileSystemClient

DEFAULT_SOURCE = Path(__file__).parent / "out" / "bronze"


def upload(source: Path, filesystem: FileSystemClient) -> tuple[int, int]:
    uploaded = skipped = 0
    for path in sorted(source.rglob("*.parquet")):
        remote = path.relative_to(source).as_posix()
        file_client = filesystem.get_file_client(remote)
        if file_client.exists() and file_client.get_file_properties().size == path.stat().st_size:
            skipped += 1
            continue
        with path.open("rb") as f:
            file_client.upload_data(f, overwrite=True)
        uploaded += 1
        print(f"  uploaded {remote}")
    return uploaded, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload bronze Parquet files to ADLS Gen2.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--account", default=os.getenv("AZURE_STORAGE_ACCOUNT"))
    parser.add_argument("--filesystem", default="bronze")
    args = parser.parse_args()

    if not args.account:
        parser.error("storage account name required (--account or AZURE_STORAGE_ACCOUNT)")
    if not args.source.is_dir():
        parser.error(f"source folder not found: {args.source}")

    service = DataLakeServiceClient(
        account_url=f"https://{args.account}.dfs.core.windows.net",
        credential=AzureCliCredential(),
    )
    filesystem = service.get_file_system_client(args.filesystem)

    print(f"{args.source} -> {args.account}/{args.filesystem}")
    uploaded, skipped = upload(args.source, filesystem)
    print(f"done: {uploaded} uploaded, {skipped} already in the lake")


if __name__ == "__main__":
    main()
