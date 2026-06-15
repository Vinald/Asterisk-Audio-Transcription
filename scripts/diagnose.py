#!/usr/bin/env python3
"""
Diagnostic tool for troubleshooting STT-TTS Pipeline connectivity.
Usage: python scripts/diagnose.py
"""

import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

AUTH_TOKEN = os.getenv("AUTH_TOKEN")
HEADERS = {
    "accept": "application/json",
    "Authorization": f"Bearer {AUTH_TOKEN}",
}

ENDPOINTS = {
    "stt": "https://api.sunbird.ai/tasks/modal/stt",
    "tts": "https://api.sunbird.ai/tasks/modal/tts",
    "language_id": "https://api.sunbird.ai/tasks/language_id",
}


def test_endpoint(name, url, timeout=10):
    print(f"\nTesting {name}...")
    start = time.time()
    try:
        if name == "language_id":
            response = requests.post(
                url,
                headers={**HEADERS, "Content-Type": "application/json"},
                json={"text": "test"},
                timeout=timeout,
            )
        else:
            response = requests.head(url, headers=HEADERS, timeout=timeout)

        elapsed = time.time() - start
        status = "✓" if response.ok else "⚠"
        print(f"  {status} Status: {response.status_code}")
        print(f"  {status} Response time: {elapsed:.2f}s")
        return True
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        print(f"  ✗ TIMEOUT after {elapsed:.2f}s")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"  ✗ CONNECTION ERROR: {e}")
        return False
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False


def test_api_local():
    print("\nTesting local API...")
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        if response.ok:
            data = response.json()
            print(f"  ✓ API is running")
            print(f"  ✓ Status: {data.get('status')}")
            print(
                f"  ✓ Heartbeat: {'running' if data.get('heartbeat_running') else 'NOT running'}"
            )

            endpoints = data.get("endpoints", {})
            for name, status in endpoints.items():
                symbol = "✓" if status == "ok" else "⚠" if "error" in status else "?"
                print(f"  {symbol} {name}: {status}")
            return True
        else:
            print(f"  ✗ API returned: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Cannot connect to API on localhost:8000")
        print(
            f"    Is the service running? sudo systemctl start stt-tts-pipeline.service"
        )
        return False
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return False


def main():
    print("=" * 60)
    print("STT-TTS Pipeline Diagnostic Tool")
    print("=" * 60)

    if not AUTH_TOKEN:
        print("\n✗ AUTH_TOKEN not set in .env file")
        print("  Please set: AUTH_TOKEN=your_token")
        return

    print("\n[1/4] Checking AUTH_TOKEN...")
    print(f"  ✓ AUTH_TOKEN is set (length: {len(AUTH_TOKEN)})")

    print("\n[2/4] Testing local API...")
    api_ok = test_api_local()

    if not api_ok:
        print("\n✗ Local API is not responding")
        print("  Try: sudo systemctl restart stt-tts-pipeline.service")
        return

    print("\n[3/4] Testing Sunbird endpoints...")
    results = {}
    for name, url in ENDPOINTS.items():
        results[name] = test_endpoint(name, url)

    print("\n[4/4] Summary")
    print("-" * 60)

    ok_count = sum(1 for v in results.values() if v)
    print(f"\nEndpoints responding: {ok_count}/{len(ENDPOINTS)}")

    if ok_count < len(ENDPOINTS):
        print("\n⚠ Some endpoints are timing out!")
        print("  Solutions:")
        print("    1. Check internet connection: ping api.sunbird.ai")
        print("    2. Heartbeat should be pinging every 1 minute")
        print("    3. Check if AUTH_TOKEN is valid: https://api.sunbird.ai")
        print("    4. Increase retry attempts in app/pipeline.py")
    else:
        print("\n✓ All endpoints are responding!")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
