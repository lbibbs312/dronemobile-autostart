"""
start_my_car.py
================

This script uses the `drone_mobile` Python package to authenticate with the
DroneMobile API and issue a remote start command for the first vehicle on the
account.  It is designed to be run in a GitHub Actions workflow where the
credentials are provided via environment variables.  The script performs
basic error checking and prints a JSON‑serialisable response from the API.

Environment variables expected:

* ``DRONEMOBILE_USERNAME`` – The e‑mail address used to log in to
  DroneMobile.
* ``DRONEMOBILE_PASSWORD`` – The corresponding account password.

Usage:

    python start_my_car.py

If authentication fails, no vehicles are found, or the response does not
contain a usable device key, the script will print an error message and exit
with a non‑zero status code.  Any unhandled exceptions will also cause a
non‑zero exit status, which will surface in the GitHub Actions run logs.
"""

import json
import os
import sys
from typing import Any, Dict, List

try:
    from drone_mobile import Vehicle
except ImportError as exc:  # pragma: no cover
    # Fail fast if the dependency is missing.  GitHub Actions will install it
    # before running this script.
    print("Error: The 'drone_mobile' package is not installed. Did you forget to\n"
          "install the dependency?", file=sys.stderr)
    raise


def get_device_key(vehicle_info: Dict[str, Any]) -> str:
    """Extract the device key from a vehicle record.

    The DroneMobile API has used both ``device_key`` and ``deviceKey`` as
    attribute names.  This helper normalises the lookup and raises a
    ``KeyError`` if neither field is present.

    Parameters
    ----------
    vehicle_info:
        A dictionary representing a single vehicle returned from
        ``Vehicle.getAllVehicles()``.

    Returns
    -------
    str
        The device key used to issue commands to the vehicle.
    """
    for key in ("device_key", "deviceKey", "deviceID", "device_id"):
        if key in vehicle_info and vehicle_info[key]:
            return vehicle_info[key]
    raise KeyError("Device key not found in vehicle info: %s" % list(vehicle_info.keys()))


def main() -> None:
    """Authenticate with DroneMobile, find the first vehicle and issue a start.

    The function prints the parsed response from the API on success.  If any
    error occurs, a descriptive message is printed to stderr and the process
    exits with a non‑zero status.  The exit status can be used by a CI
    workflow to determine success or failure.
    """
    username = os.environ.get("DRONEMOBILE_USERNAME")
    password = os.environ.get("DRONEMOBILE_PASSWORD")
    if not username or not password:
        print(
            "Error: Both DRONEMOBILE_USERNAME and DRONEMOBILE_PASSWORD must be set as environment variables.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        vehicle_client = Vehicle(username, password)
        # Authenticate and obtain tokens.  This raises requests.exceptions.HTTPError
        # if credentials are invalid.
        vehicle_client.auth()
        vehicles: List[Dict[str, Any]] = vehicle_client.getAllVehicles() or []
    except Exception as exc:
        print(f"Error during authentication or vehicle retrieval: {exc}", file=sys.stderr)
        sys.exit(1)

    if not vehicles:
        print("Error: No vehicles were found on your DroneMobile account.", file=sys.stderr)
        sys.exit(1)

    # Use the first vehicle for simplicity.  If you have multiple vehicles and
    # need finer control, modify this logic as needed.
    first_vehicle = vehicles[0]
    try:
        device_key = get_device_key(first_vehicle)
    except KeyError as exc:
        print(f"Error extracting device key: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        response: Dict[str, Any] = vehicle_client.start(device_key)
    except Exception as exc:
        print(f"Error issuing remote start command: {exc}", file=sys.stderr)
        sys.exit(1)

    # Pretty‑print the parsed response for visibility.
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
