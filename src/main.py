# src/main.py
from __future__ import annotations

from src.settings import load_settings
from src.seats_aero.client import SeatsAeroClient, SeatsAeroAPIError


def main() -> int:
    settings = load_settings()

    print("\n=== Seats.aero Notifier (Step 2: API client smoke test) ===")
    print(f"Config file: {settings.watch_path}")
    print(f"State file : {settings.state_path}")
    print(f"API key    : {'FOUND' if settings.api_key_present else 'MISSING'}")

    w = settings.watch
    print("\n--- Watch config ---")
    print(f"Route      : {w.origin} -> {w.destination}")
    if w.date_mode == "single":
        print(f"Date       : {w.start_date} (single)")
    else:
        print(f"Date range : {w.start_date} .. {w.end_date}")
    print(f"Sources    : {', '.join(w.sources)}")
    print(f"Cabin      : {w.cabin}")
    print(f"Filters    : {w.filters}")
    print(f"Notify     : {w.notification}")
    print(f"State entries: {len(settings.state)}")

    # ---- Step 2: build client + smoke test ----
    client = SeatsAeroClient(api_key=settings.api_key)

    # Use the first configured source for the smoke test
    test_source = w.sources[0]

    try:
        data = client.get("routes", params={"source": test_source})

        # Basic validation: /routes should return a list
        if not isinstance(data, list):
            raise SeatsAeroAPIError(
                status_code=0,
                message="Unexpected /routes response type (expected list)",
                response_text=str(type(data)),
            )

        print(f"✅ API call OK. Returned {len(data)} routes.")

    except SeatsAeroAPIError as e:
        print("❌ API call failed.")
        print(str(e))
        return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
