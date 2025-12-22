"""
i2c-Cont-Read-Atlas-devices.py

Cleaned and hardened data-logging script for Atlas I2C devices.
- Robust parsing of sensor responses
- Skips bad timesteps by marking errors in the CSV and continuing
- Adds ErrorFlag and ErrorDetail columns to the CSV
- K1.0 sensor removed from logging (only logs K0.1 #1, K0.1 #2, K0.1 #3)
- Adds resistivity (MΩ·cm) output for each conductivity measurement:
    Resistivity (MΩ·cm) = 1 / Conductivity (µS/cm)
"""

import csv
import datetime
from time import time

from Atlas_I2C_Driver_JQ import Config_AtlasI2C, read_recieve_all


def parse_sensor_value(resp: str):
    """
    Parse an Atlas I2C response into a float.

    Returns (value, err) where:
      - value is float or None
      - err is None or a short error string

    Expected response formats from Atlas_I2C_Driver_JQ read():
      - 'Success <device info>: <number>'
      - 'Error <device info>: <code>'
    """
    try:
        if resp is None:
            return None, "no_response"

        # Clean stray nulls and whitespace
        resp = resp.replace("\x00", "").strip()

        # Device reported error
        if resp.startswith("Error"):
            return None, resp  # keep entire message for context

        # Extract numeric payload after the first colon
        parts = resp.split(":", 1)
        if len(parts) < 2:
            return None, f"bad_format:{resp!r}"

        rhs = parts[1].strip()
        # If units/tokens follow, take the first token for float conversion
        token = rhs.split()[0]

        return float(token), None

    except ValueError:
        return None, f"value_error:rhs={rhs!r}"
    except Exception as e:
        return None, f"exception:{type(e).__name__}:{e}"


def to_resistivity_mohm(cond_us_cm: float):
    """
    Convert conductivity (µS/cm) to resistivity (MΩ·cm).
    Resistivity (MΩ·cm) = 1 / Conductivity (µS/cm)

    Returns float or None if input is invalid (None or <= 0).
    """
    try:
        if cond_us_cm is None or cond_us_cm <= 0:
            return None
        return 1.0 / cond_us_cm
    except Exception:
        return None


def main():
    # Output filename
    filename_s = input("Enter Name for Datalog File: ").strip()
    filename = f"{filename_s}.csv" if filename_s else "datalog.csv"

    # Discover devices on I2C
    device_list = Config_AtlasI2C.get_devices()
    if not device_list:
        print("No I2C devices found. Exiting.")
        return

    # Initialize CSV with extended header (K1.0 removed, resistivity added)
    with open(filename, "w", newline="") as data_csv:
        csv_writer = csv.writer(data_csv, delimiter=";")
        csv_writer.writerow([
            "Time (Y-M-D-H-M-S)",
            "Time from Start (Seconds)",
            "Loop Time (Seconds)",
            "K0.1 #1 Conductivity (µS/cm)",
            "K0.1 #1 Resistivity (MΩ·cm)",
            "K0.1 #2 Conductivity (µS/cm)",
            "K0.1 #2 Resistivity (MΩ·cm)",
            "K0.1 #3 Conductivity (µS/cm)",
            "K0.1 #3 Resistivity (MΩ·cm)",
            "ErrorFlag",
            "ErrorDetail"
        ])

    # Start timing
    time_elapsed_start = time()

    try:
        while True:
            loop_time_start = time()
            now = datetime.datetime.now()

            # Read from all devices
            readings = read_recieve_all(device_list)

            # Guard: ensure we have at least 3 responses for the three K0.1 channels
            if not isinstance(readings, list) or len(readings) < 3:
                time_elapsed_overall = time() - time_elapsed_start
                loop_time = time() - loop_time_start
                with open(filename, "a", newline="") as data_csv:
                    csv_writer = csv.writer(data_csv, delimiter=";")
                    csv_writer.writerow([
                        now.strftime("%Y-%m-%d %H:%M:%S"),
                        time_elapsed_overall,
                        loop_time,
                        "", "", "", "", "", "",
                        1,
                        "insufficient_readings"
                    ])
                continue

            # Map indices to channels (adjust if your device order differs)
            # 0 -> K0.1 #1 Conductivity
            # 1 -> K0.1 #2 Conductivity
            # 2 -> K0.1 #3 Conductivity
            val_k01_1, err_k01_1 = parse_sensor_value(readings[0])
            val_k01_2, err_k01_2 = parse_sensor_value(readings[1])
            val_k01_3, err_k01_3 = parse_sensor_value(readings[2])

            errors = [e for e in [err_k01_1, err_k01_2, err_k01_3] if e]
            have_error = len(errors) > 0

            time_elapsed_overall = time() - time_elapsed_start
            loop_time = time() - loop_time_start

            # Compute resistivities (only if not in error)
            if not have_error:
                res_k01_1 = to_resistivity_mohm(val_k01_1)
                res_k01_2 = to_resistivity_mohm(val_k01_2)
                res_k01_3 = to_resistivity_mohm(val_k01_3)
            else:
                res_k01_1 = res_k01_2 = res_k01_3 = None

            # Write CSV row
            with open(filename, "a", newline="") as data_csv:
                csv_writer = csv.writer(data_csv, delimiter=";")
                if have_error:
                    csv_writer.writerow([
                        now.strftime("%Y-%m-%d %H:%M:%S"),
                        time_elapsed_overall,
                        loop_time,
                        "", "", "", "", "", "",
                        1,
                        "; ".join(errors)
                    ])
                    # Skip this iteration; try again next timestep
                    continue
                else:
                    csv_writer.writerow([
                        now.strftime("%Y-%m-%d %H:%M:%S"),
                        time_elapsed_overall,
                        loop_time,
                        val_k01_1,
                        "" if res_k01_1 is None else res_k01_1,
                        val_k01_2,
                        "" if res_k01_2 is None else res_k01_2,
                        val_k01_3,
                        "" if res_k01_3 is None else res_k01_3,
                        0,
                        ""
                    ])

            # Optional console output for monitoring
            def fmt(v):
                return "N/A" if v is None else f"{v}"

            print(
                f"{now.strftime('%H:%M:%S')} | "
                f"t={time_elapsed_overall:.1f}s | loop={loop_time:.3f}s | "
                f"K0.1#1={fmt(val_k01_1)} µS/cm (R={fmt(res_k01_1)} MΩ·cm), "
                f"K0.1#2={fmt(val_k01_2)} µS/cm (R={fmt(res_k01_2)} MΩ·cm), "
                f"K0.1#3={fmt(val_k01_3)} µS/cm (R={fmt(res_k01_3)} MΩ·cm)"
            )

    except KeyboardInterrupt:
        print("Data Logging Stopped By User")


if __name__ == "__main__":
    main()
