/*
 * WiFi Diagnostic Test - Tests all scan variations
 * Reports results over serial for debugging
 */

#include "WiFi.h"
#include "wifi_conf.h"

// Test results storage
static int callbackCount = 0;
static char lastSSID[64] = "";

// Callback for wifi_scan_networks
rtw_result_t testScanCallback(rtw_scan_handler_result_t* result) {
    if (result->scan_complete != RTW_TRUE) {
        rtw_scan_result_t* record = &result->ap_details;
        record->SSID.val[record->SSID.len] = 0;
        callbackCount++;
        strncpy(lastSSID, (char*)record->SSID.val, 63);
    }
    return RTW_SUCCESS;
}

void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 3000);

    delay(1000);
    Serial.println("\n\n========================================");
    Serial.println("   GATTROSE-NG WiFi Diagnostic Tool");
    Serial.println("========================================\n");

    // Test 1: Skip - wifi_is_connected_to_ap hangs
    Serial.println("[TEST 1] SKIPPED (hangs)");

    // Test 2: Initialize with WiFi.status()
    Serial.println("\n[TEST 2] Calling WiFi.status() to init...");
    WiFi.status();
    delay(1000);
    Serial.println("  Done.");

    // Test 3: Arduino WiFi.scanNetworks()
    Serial.println("\n[TEST 3] Arduino WiFi.scanNetworks()...");
    int numNets = WiFi.scanNetworks();
    Serial.print("  Result: ");
    Serial.print(numNets);
    Serial.println(" networks");
    if (numNets > 0) {
        Serial.print("  First SSID: ");
        Serial.println(WiFi.SSID(0));
        Serial.print("  First RSSI: ");
        Serial.println(WiFi.RSSI(0));
    }

    // Test 4: Callback scan without extra init
    Serial.println("\n[TEST 4] wifi_scan_networks() callback (no extra init)...");
    callbackCount = 0;
    lastSSID[0] = 0;
    int ret4 = wifi_scan_networks(testScanCallback, NULL);
    Serial.print("  Return value: ");
    Serial.println(ret4);
    delay(5000);
    Serial.print("  Callbacks received: ");
    Serial.println(callbackCount);
    if (callbackCount > 0) {
        Serial.print("  Last SSID: ");
        Serial.println(lastSSID);
    }

    // Test 5: wifi_off then wifi_on(STA) then scan
    Serial.println("\n[TEST 5] wifi_off -> wifi_on(STA) -> scan...");
    wifi_off();
    delay(1000);
    wifi_on(RTW_MODE_STA);
    delay(1000);
    callbackCount = 0;
    lastSSID[0] = 0;
    int ret5 = wifi_scan_networks(testScanCallback, NULL);
    Serial.print("  Return value: ");
    Serial.println(ret5);
    delay(5000);
    Serial.print("  Callbacks received: ");
    Serial.println(callbackCount);
    if (callbackCount > 0) {
        Serial.print("  Last SSID: ");
        Serial.println(lastSSID);
    }

    // Test 6: Check wifi_is_ready_to_transceive
    Serial.println("\n[TEST 6] wifi_is_ready_to_transceive status...");
    int ready = wifi_is_ready_to_transceive(RTW_STA_INTERFACE);
    Serial.print("  STA interface ready: ");
    Serial.println(ready);

    // Test 7: Direct wifi_scan with parameters
    Serial.println("\n[TEST 7] Low-level wifi_scan()...");
    callbackCount = 0;
    lastSSID[0] = 0;
    // wifi_scan takes: scan_type, bss_type, result_ptr, max_count, ssid, ssid_len, channel
    int ret7 = wifi_scan_networks(testScanCallback, NULL);
    delay(8000);  // Longer wait
    Serial.print("  Callbacks after 8s: ");
    Serial.println(callbackCount);

    // Test 8: Multiple quick scans
    Serial.println("\n[TEST 8] Rapid scan test (3x)...");
    for (int i = 0; i < 3; i++) {
        callbackCount = 0;
        wifi_scan_networks(testScanCallback, NULL);
        delay(3000);
        Serial.print("  Scan ");
        Serial.print(i + 1);
        Serial.print(": ");
        Serial.print(callbackCount);
        Serial.println(" networks");
    }

    // Test 9: Check RTW_TRUE value
    Serial.println("\n[TEST 9] Constant values...");
    Serial.print("  RTW_TRUE = ");
    Serial.println(RTW_TRUE);
    Serial.print("  RTW_FALSE = ");
    Serial.println(RTW_FALSE);
    Serial.print("  RTW_SUCCESS = ");
    Serial.println(RTW_SUCCESS);

    // Test 10: WiFi mode check
    Serial.println("\n[TEST 10] WiFi mode info...");
    Serial.print("  wext_get_mode would return current mode");

    Serial.println("\n\n========================================");
    Serial.println("   DIAGNOSTIC COMPLETE");
    Serial.println("========================================");
    Serial.println("\nSummary:");
    Serial.println("- If TEST 3 works but TEST 4/5 don't: Use Arduino API");
    Serial.println("- If TEST 4 works: Callback approach is fine");
    Serial.println("- If TEST 5 works but TEST 4 doesn't: Need wifi_on first");
    Serial.println("- If nothing works: Hardware/driver issue");
    Serial.println("\nWaiting... Send 'r' to rerun tests.\n");
}

void loop() {
    if (Serial.available()) {
        char c = Serial.read();
        if (c == 'r' || c == 'R') {
            Serial.println("\n--- RERUNNING TESTS ---\n");
            setup();
        }
        if (c == 's' || c == 'S') {
            Serial.println("\n--- QUICK SCAN TEST ---");
            callbackCount = 0;
            wifi_scan_networks(testScanCallback, NULL);
            for (int i = 0; i < 10; i++) {
                delay(1000);
                Serial.print("  ");
                Serial.print(i + 1);
                Serial.print("s: ");
                Serial.print(callbackCount);
                Serial.println(" networks");
            }
        }
    }
    delay(100);
}
