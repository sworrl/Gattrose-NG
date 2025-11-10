#!/bin/bash

BASE_URL="http://localhost:5555"

echo "========================================="
echo "  Gattrose-NG API Test Suite"
echo "========================================="
echo

echo "[1/10] Getting API documentation..."
curl -s $BASE_URL/api/docs | jq -r '.message, .version'
echo

echo "[2/10] Getting GPS status..."
curl -s $BASE_URL/api/gui/gps/status | jq '.data | {has_fix, latitude, longitude, source, fix_quality}'
echo

echo "[3/10] Getting GUI state..."
curl -s $BASE_URL/api/gui/state | jq '.data | {theme, tabs, gps: {has_fix: .gps.has_fix, source: .gps.source}}'
echo

echo "[4/10] Getting statistics..."
curl -s $BASE_URL/api/gui/stats | jq '.data'
echo

echo "[5/10] Switching to mapping tab..."
curl -s -X POST $BASE_URL/api/gui/tab \
  -H "Content-Type: application/json" \
  -d '{"tab": "mapping"}' | jq '{success, message}'
sleep 1
echo

echo "[6/10] Getting scan status..."
curl -s $BASE_URL/api/gui/scan/status | jq '.data'
echo

echo "[7/10] Getting networks count..."
NETWORK_COUNT=$(curl -s $BASE_URL/api/gui/networks | jq '.count')
echo "Networks found: $NETWORK_COUNT"
echo

echo "[8/10] Getting clients count..."
CLIENT_COUNT=$(curl -s $BASE_URL/api/gui/clients | jq '.count')
echo "Clients found: $CLIENT_COUNT"
echo

echo "[9/10] Testing GPS location update..."
curl -s -X POST $BASE_URL/api/gui/gps/location \
  -H "Content-Type: application/json" \
  -d '{"latitude": 39.005509, "longitude": -90.741686}' | jq '{success, message}'
echo

echo "[10/10] Switching back to dashboard tab..."
curl -s -X POST $BASE_URL/api/gui/tab \
  -H "Content-Type: application/json" \
  -d '{"tab": "dashboard"}' | jq '{success, message}'
echo

echo "========================================="
echo "  All tests complete!"
echo "========================================="
echo
echo "To test theme changes, run:"
echo "  curl -X POST $BASE_URL/api/gui/theme -H 'Content-Type: application/json' -d '{\"theme\": \"hacker\"}' | jq"
echo
echo "Available themes: sonic, hacker, midnight, ocean, forest, sunset, neon, stealth"
echo
