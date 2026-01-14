/**
 * @file gattrose_ng.c
 * @brief Gattrose-NG: RTL8720 Dual-Band WiFi Auditing Suite for Flipper Zero
 *
 * Full-featured WiFi auditing with client tracking, deauth, evil twin, beacons.
 * Based on delfyRTL protocol for BW16/RTL8720DN modules.
 *
 * Wiring (Flipper -> RTL8720):
 *   TX (Pin 13) -> RX1
 *   RX (Pin 14) -> TX1
 *   5V (Pin 1)  -> 5V
 *   GND (Pin 8) -> GND
 */

#include <furi.h>
#include <furi_hal.h>
#include <furi_hal_serial.h>
#include <furi_hal_power.h>
#include <furi_hal_random.h>
#include <expansion/expansion.h>
#include <gui/gui.h>
#include <gui/view_dispatcher.h>
#include <gui/scene_manager.h>
#include <gui/modules/menu.h>
#include <gui/modules/submenu.h>
#include <gui/modules/text_box.h>
#include <gui/modules/text_input.h>
#include <gui/modules/loading.h>
#include <gui/modules/variable_item_list.h>
#include <gui/modules/popup.h>
#include <gui/modules/widget.h>
#include <gui/modules/byte_input.h>
#include <notification/notification_messages.h>
#include <storage/storage.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#define TAG "GattroseNG"

// Version
#define APP_VERSION "4.0.0"
#define APP_CODENAME "Full Arsenal"
#define APP_BUILD_DATE __DATE__
#define APP_BUILD_TIME __TIME__

// Paths
#define GATTROSE_DATA_PATH EXT_PATH("apps_data/gattrose-ng")
#define LOG_FILE_PATH GATTROSE_DATA_PATH "/debug.log"

// UART Config
#define UART_BAUD 115200
#define UART_ID FuriHalSerialIdUsart
#define RX_BUF_SIZE 2048

// Protocol framing (STX/ETX binary protocol)
#define PROTO_STX 0x02
#define PROTO_ETX 0x03
#define PROTO_SEP 0x1D

// Response types from BW16
#define RESP_READY   'r'
#define RESP_SCAN    's'
#define RESP_NETWORK 'n'
#define RESP_CLIENT  'c'
#define RESP_BLE     'l'
#define RESP_CREDS   'C'
#define RESP_INFO    'i'
#define RESP_ERROR   'e'
#define RESP_DEAUTH  'd'
#define RESP_WIFI    'w'
#define RESP_BEACON  'b'
#define RESP_MONITOR 'm'
#define RESP_STOP    'x'
#define RESP_PORTAL  'p'
#define RESP_APCONF  'a'
#define RESP_LED     'r'   // LED control response
#define RESP_KICK    'k'   // Client-only attack response

// Limits
#define MAX_NETWORKS 64
#define MAX_CLIENTS 128
#define MAX_CLIENTS_PER_AP 16
#define MAX_SSID_LEN 33
#define MAX_BSSID_LEN 18
#define MAC_LENGTH 6

// Security flags
#define WEP_ENABLED    0x0001
#define TKIP_ENABLED   0x0002
#define AES_ENABLED    0x0004
#define SHARED_ENABLED 0x00008000
#define WPA_SECURITY   0x00200000
#define WPA2_SECURITY  0x00400000
#define WPA3_SECURITY  0x00800000

// ============================================================================
// Views
// ============================================================================

typedef enum {
    ViewIdSplash,
    ViewIdMenu,
    ViewIdLoading,
    ViewIdNetworkList,
    ViewIdNetworkInfo,
    ViewIdClientList,
    ViewIdAttackConfig,
    ViewIdMacInput,
    ViewIdBeaconMenu,
    ViewIdBeaconSsidInput,
    ViewIdBeaconActive,
    ViewIdCreateAp,
    ViewIdApSsidInput,
    ViewIdApPasswordInput,
    ViewIdEvilPortal,
    ViewIdClientSniff,
    ViewIdBleMenu,
    ViewIdBleList,
    ViewIdLedMenu,
    ViewIdConsoleMenu,
    ViewIdConsoleOutput,
    ViewIdConsoleSend,
    ViewIdLog,
    ViewIdAbout,
    ViewIdAdvancedMenu,     // Advanced attacks submenu
} ViewId;

typedef enum {
    MenuIndexScan,
    MenuIndexNetworks,
    MenuIndexClientSniff,
    MenuIndexBeacon,
    MenuIndexCreateAp,
    MenuIndexAdvanced,      // New: Advanced attacks submenu
    MenuIndexBle,
    MenuIndexLed,
    MenuIndexStopAll,
    MenuIndexConsole,
    MenuIndexAbout,
    MenuIndexExit,
} MenuIndex;

// Advanced attack menu indices
typedef enum {
    AdvMenuIndexJammer,     // WiFi Jammer (all networks)
    AdvMenuIndexProbeLog,   // Probe Logger
    AdvMenuIndexKarma,      // Karma Attack
    AdvMenuIndexPMKID,      // PMKID Capture
    AdvMenuIndexHandshake,  // Handshake Capture
    AdvMenuIndexRogueBase,  // Set Rogue AP Baseline
    AdvMenuIndexRogueMon,   // Rogue AP Monitor
    AdvMenuIndexBack,
} AdvMenuIndex;

// ============================================================================
// Data Types
// ============================================================================

typedef struct {
    char mac[MAX_BSSID_LEN];
    int rssi;
    int ap_index;
} Client;

typedef struct {
    int id;
    char ssid[MAX_SSID_LEN];
    char bssid[MAX_BSSID_LEN];
    int channel;
    int rssi;
    int security;           // Legacy: integer security flags
    bool is_5ghz;
    bool deauth_active;
    int client_count;
    int client_indices[MAX_CLIENTS_PER_AP];
    char security_str[16];  // "Open", "WEP", "WPA", "WPA2", "WPA3"
    bool has_pmf;           // PMF enabled - deauth won't work
    bool hidden;            // Hidden SSID
} Network;

// BLE device structure
#define MAX_BLE_DEVICES 32
typedef struct {
    char address[MAX_BSSID_LEN];
    char name[64];
    int rssi;
} BleDevice;

// ============================================================================
// Firmware Detection
// ============================================================================

typedef enum {
    FirmwareUnknown = 0,
    FirmwareGattrose,      // Custom Gattrose-NG firmware
    FirmwareEvilBW16,      // Evil-BW16 / delfyRTL
    FirmwarePingequa,      // Original Pingequa firmware
    FirmwareMarauder,      // ESP32 Marauder (if connected wrong device)
    FirmwareGeneric,       // Generic AT command firmware
} FirmwareType;

typedef struct {
    bool wifi_scan;
    bool wifi_scan_5ghz;
    bool client_detection;
    bool targeted_deauth;
    bool broadcast_deauth;
    bool beacon_spam;
    bool evil_twin;
    bool ble_scan;
    bool ble_spam;
    bool channel_hop;
    bool monitor_mode;
    bool eapol_capture;
} FirmwareCapabilities;

static const char* firmware_names[] = {
    "Unknown",
    "Gattrose-NG",
    "Evil-BW16",
    "Pingequa",
    "Marauder",
    "Generic AT",
};

// Default capabilities for each firmware type
static const FirmwareCapabilities firmware_caps[] = {
    // Unknown - assume minimal
    {true, false, false, false, true, false, false, false, false, false, false, false},
    // Gattrose-NG - full features
    {true, true, true, true, true, true, true, true, true, true, true, true},
    // Evil-BW16 - WiFi only, no client detection
    {true, true, false, false, true, true, true, false, false, true, false, true},
    // Pingequa - unknown, assume basic
    {true, false, false, false, true, false, false, false, false, false, false, false},
    // Marauder - ESP32, different protocol
    {true, false, false, false, true, true, false, true, true, false, false, false},
    // Generic AT - minimal
    {true, false, false, false, false, false, false, false, false, false, false, false},
};

// Captive portal types (matches Gattrose-NG firmware w0-w7)
#define PORTAL_COUNT 8
static const char* const portal_names[PORTAL_COUNT] = {
    "Stop", "Default", "Google", "Facebook", "Amazon", "Apple", "Netflix", "Microsoft"
};

// Deauth reasons
#define REASON_COUNT 25
static const char* const deauth_reasons[REASON_COUNT] = {
    "Reserved", "Unspecified", "Auth no longer valid", "Leaving BSS",
    "Inactivity", "AP overloaded", "Class 2 error", "Class 3 error",
    "Disassoc leaving", "Not authenticated", "Power Cap invalid",
    "Channels invalid", "BSS Transition", "Invalid element", "MIC failure",
    "4-Way timeout", "Group Key timeout", "4-Way mismatch", "Invalid group",
    "Invalid pairwise", "Invalid AKMP", "Bad RSNE version", "Invalid RSNE",
    "802.1X auth fail", "Cipher rejected"
};

// MAC type options
#define MAC_TYPE_COUNT 4
static const char* const mac_types[MAC_TYPE_COUNT] = {
    "Default", "Random", "Custom", "Same as AP"
};

// Security types
static const char* const security_types[2] = {"OPEN", "WPA"};

// Channel list (2.4GHz + 5GHz)
#define CHANNEL_COUNT 59
static const char* const channel_list[CHANNEL_COUNT] = {
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14",
    "36", "38", "40", "42", "44", "46", "48", "50", "52", "54", "56", "58",
    "60", "62", "64", "100", "102", "104", "106", "108", "110", "112", "114",
    "116", "118", "120", "122", "124", "126", "128", "132", "134", "136",
    "138", "140", "142", "144", "149", "151", "153", "155", "157", "159", "161", "165"
};

typedef struct {
    // Core
    Gui* gui;
    ViewDispatcher* view_dispatcher;
    NotificationApp* notifications;
    Storage* storage;
    Expansion* expansion;

    // Views
    Widget* splash;
    Menu* menu;
    Loading* loading;
    Submenu* network_list;
    Widget* network_info;
    Submenu* client_list;
    Submenu* client_sniff;     // Client sniff menu
    Submenu* ble_menu;         // BLE menu
    Submenu* ble_list;         // BLE device list
    Submenu* led_menu;         // LED control menu
    VariableItemList* attack_config;
    ByteInput* mac_input;
    Submenu* beacon_menu;
    TextInput* text_input;
    Widget* beacon_active;
    VariableItemList* create_ap;
    Widget* evil_portal;
    Submenu* console_menu;
    Submenu* advanced_menu;  // Advanced attacks menu
    TextBox* log_view;
    Popup* about_popup;

    // UART
    FuriHalSerialHandle* serial;
    FuriStreamBuffer* rx_stream;
    FuriThread* rx_thread;
    FuriMutex* mutex;
    volatile bool uart_running;
    bool connected;

    // Networks & Clients
    Network networks[MAX_NETWORKS];
    int network_count;
    Client clients[MAX_CLIENTS];
    int client_count;
    int selected_network;
    int menu_index;

    // BLE devices
    BleDevice ble_devices[MAX_BLE_DEVICES];
    int ble_count;

    // Monitor mode
    bool monitor_active;

    // Attack config
    int deauth_reason;
    int portal_type;
    int mac_type;
    char custom_mac[MAX_BSSID_LEN];
    uint8_t mac_bytes[MAC_LENGTH];

    // Create AP config
    char ap_ssid[MAX_SSID_LEN];
    char ap_password[64];
    int ap_security;
    int ap_channel;

    // Beacon
    char beacon_ssid[MAX_SSID_LEN];
    int beacon_type; // 0=custom, 1=random, 2=rickroll

    // Credentials captured
    char credentials[512];

    // State
    volatile bool scan_finished;
    bool scanning;
    bool show_all_networks;  // false = only show APs with clients

    // Buffers
    char rx_line[256];
    size_t rx_pos;
    char log_buffer[2048];
    char console_buffer[2048];
    char console_cmd[64];
    bool console_mode;

    // Stats
    uint32_t bytes_rx;
    uint32_t bytes_tx;

    // Firmware detection
    FirmwareType firmware_type;
    FirmwareCapabilities caps;
    char firmware_version[32];
    char firmware_response[128];
    volatile bool detection_done;
    volatile bool got_pong;
    volatile bool got_info;
    volatile bool got_help;

    // Device status (from 'i' command)
    int device_channel;
    int device_deauth_count;
    bool device_beacon_active;
    bool device_ap_active;
    int device_ble_count;

    // Advanced attack state
    bool jammer_active;
    bool probe_log_active;
    bool karma_active;
    bool pmkid_capture_active;
    bool handshake_capture_active;
    bool rogue_monitor_active;

    // Splash screen strings
    char splash_fw_status[48];
    char splash_caps[64];
} App;

// Splash screen input handling
typedef enum {
    SplashActionNone,
    SplashActionDismiss,
} SplashAction;

static volatile SplashAction splash_action = SplashActionNone;

static void splash_input_callback(const void* event, void* context) {
    UNUSED(context);
    const InputEvent* input_event = event;
    if(input_event->type == InputTypePress) {
        splash_action = SplashActionDismiss;
    }
}

// Forward declarations
static void uart_send(App* app, const char* cmd, size_t len);
static void detect_firmware(App* app);
static const char* get_firmware_name(App* app);
static void update_network_list(App* app);
static void update_about(App* app);
static void update_network_info(App* app);
static void update_client_list(App* app);
static void update_evil_portal(App* app);
static void setup_attack_config(App* app);
static void setup_create_ap(App* app);
static void network_list_callback(void* context, uint32_t index);
static void client_list_callback(void* context, uint32_t index);
static void beacon_ssid_input_callback(void* context);
static void ap_ssid_input_callback(void* context);
static void ap_password_input_callback(void* context);
static void console_send_callback(void* context);
static void update_console(App* app);

// ============================================================================
// Helpers
// ============================================================================

static const char* get_security_name(int security) {
    switch(security) {
        case 0: return "OPEN";
        case WEP_ENABLED: return "WEP";
        case (WEP_ENABLED | SHARED_ENABLED): return "WEP-S";
        case (WPA_SECURITY | TKIP_ENABLED): return "WPA-TKIP";
        case (WPA_SECURITY | AES_ENABLED): return "WPA-AES";
        case (WPA2_SECURITY | AES_ENABLED): return "WPA2-AES";
        case (WPA2_SECURITY | TKIP_ENABLED): return "WPA2-TKIP";
        case (WPA2_SECURITY | AES_ENABLED | TKIP_ENABLED): return "WPA2-MIX";
        case (WPA_SECURITY | WPA2_SECURITY): return "WPA/2";
        case (WPA3_SECURITY | AES_ENABLED): return "WPA3";
        case (WPA2_SECURITY | WPA3_SECURITY | AES_ENABLED): return "WPA2/3";
        default: return "???";
    }
}

// Token parser state (replacement for strtok which is disabled in Flipper API)
typedef struct {
    char* str;
    size_t pos;
} TokenState;

static void token_init(TokenState* state, char* str) {
    state->str = str;
    state->pos = 0;
}

static char* token_next(TokenState* state, char delim) {
    if(!state->str || state->str[state->pos] == '\0') return NULL;

    char* start = &state->str[state->pos];

    // Find delimiter or end
    while(state->str[state->pos] != '\0' && state->str[state->pos] != delim) {
        state->pos++;
    }

    // Null-terminate this token
    if(state->str[state->pos] == delim) {
        state->str[state->pos] = '\0';
        state->pos++;
    }

    return start;
}

static void generate_random_mac(uint8_t* mac) {
    furi_hal_random_fill_buf(mac, MAC_LENGTH);
    mac[0] &= 0xFE;  // Unicast
    mac[0] |= 0x02;  // Locally administered
}

static void mac_bytes_to_string(const uint8_t* bytes, char* str) {
    snprintf(str, MAX_BSSID_LEN, "%02X:%02X:%02X:%02X:%02X:%02X",
        bytes[0], bytes[1], bytes[2], bytes[3], bytes[4], bytes[5]);
}

static void mac_string_to_bytes(const char* str, uint8_t* bytes) {
    unsigned int b[6];
    if(sscanf(str, "%02X:%02X:%02X:%02X:%02X:%02X",
              &b[0], &b[1], &b[2], &b[3], &b[4], &b[5]) == 6) {
        for(int i = 0; i < 6; i++) bytes[i] = (uint8_t)b[i];
    }
}

// Sort networks: with clients first, then by signal strength (descending)
// Returns true if a should come before b
static bool network_should_swap(const Network* a, const Network* b) {
    // Networks with clients should come first
    if(a->client_count > 0 && b->client_count == 0) return false;  // a stays before b
    if(a->client_count == 0 && b->client_count > 0) return true;   // b should come first

    // Same category, sort by RSSI (stronger = less negative should come first)
    return a->rssi < b->rssi;  // swap if a has weaker signal
}

static void sort_networks(App* app) {
    // Bubble sort (no qsort in Flipper SDK)
    for(int i = 0; i < app->network_count - 1; i++) {
        for(int j = 0; j < app->network_count - i - 1; j++) {
            if(network_should_swap(&app->networks[j], &app->networks[j + 1])) {
                // Swap networks
                Network temp = app->networks[j];
                app->networks[j] = app->networks[j + 1];
                app->networks[j + 1] = temp;
            }
        }
    }

    // Update client AP indices after sort
    for(int c = 0; c < app->client_count; c++) {
        // Find the network with matching ID
        for(int n = 0; n < app->network_count; n++) {
            // Re-link clients to networks
            for(int ci = 0; ci < app->networks[n].client_count; ci++) {
                if(app->networks[n].client_indices[ci] == c) {
                    app->clients[c].ap_index = n;
                    break;
                }
            }
        }
    }
}

// ============================================================================
// Logging
// ============================================================================

static void ensure_app_dir(App* app) {
    storage_simply_mkdir(app->storage, GATTROSE_DATA_PATH);
}

static void app_log(App* app, const char* fmt, ...) {
    char msg[128];
    va_list args;
    va_start(args, fmt);
    vsnprintf(msg, sizeof(msg), fmt, args);
    va_end(args);

    FURI_LOG_I(TAG, "%s", msg);

    if(app->rx_thread && furi_thread_get_current_id() == furi_thread_get_id(app->rx_thread)) {
        return;
    }

    File* file = storage_file_alloc(app->storage);
    if(storage_file_open(file, LOG_FILE_PATH, FSAM_WRITE, FSOM_OPEN_APPEND)) {
        uint32_t tick = furi_get_tick();
        char line[160];
        snprintf(line, sizeof(line), "[%lu] %s\n", tick, msg);
        storage_file_write(file, line, strlen(line));
    }
    storage_file_close(file);
    storage_file_free(file);
}


// ============================================================================
// UART
// ============================================================================

static void uart_rx_callback(FuriHalSerialHandle* handle, FuriHalSerialRxEvent event, void* context) {
    App* app = context;
    if(event == FuriHalSerialRxEventData) {
        uint8_t data = furi_hal_serial_async_rx(handle);
        furi_stream_buffer_send(app->rx_stream, &data, 1, 0);
    }
}

static void process_rx_message(App* app, const char* msg, size_t len);
static void process_rx_line(App* app, const char* line);

static int32_t uart_rx_thread(void* context) {
    App* app = context;
    uint8_t data;
    bool in_message = false;  // Are we inside STX/ETX frame?

    while(app->uart_running) {
        size_t len = furi_stream_buffer_receive(app->rx_stream, &data, 1, 100);
        if(len > 0) {
            app->bytes_rx++;
            if(furi_mutex_acquire(app->mutex, 10) == FuriStatusOk) {
                // Handle STX/ETX binary framing
                if(data == PROTO_STX) {
                    // Start of new message
                    in_message = true;
                    app->rx_pos = 0;
                } else if(data == PROTO_ETX && in_message) {
                    // End of message - process it
                    app->rx_line[app->rx_pos] = '\0';
                    process_rx_message(app, app->rx_line, app->rx_pos);
                    app->rx_pos = 0;
                    in_message = false;
                } else if(in_message) {
                    // Inside STX/ETX frame - buffer the data
                    if(app->rx_pos < sizeof(app->rx_line) - 1) {
                        app->rx_line[app->rx_pos++] = data;
                    }
                } else {
                    // Legacy mode: handle newline-terminated text
                    if(data == '\n') {
                        if(app->rx_pos > 0) {
                            if(app->rx_line[app->rx_pos - 1] == '\r') app->rx_pos--;
                            app->rx_line[app->rx_pos] = '\0';
                            process_rx_line(app, app->rx_line);
                            app->rx_pos = 0;
                        }
                    } else if(data >= 0x20 || data == '\t') {
                        if(app->rx_pos < sizeof(app->rx_line) - 1) {
                            app->rx_line[app->rx_pos++] = data;
                        }
                    }
                }
                furi_mutex_release(app->mutex);
            }
        }
    }
    return 0;
}

static bool uart_init(App* app) {
    app_log(app, "Init UART %d baud", UART_BAUD);

    app->serial = furi_hal_serial_control_acquire(UART_ID);
    if(!app->serial) {
        app_log(app, "UART acquire failed");
        return false;
    }

    furi_hal_serial_init(app->serial, UART_BAUD);
    app->rx_stream = furi_stream_buffer_alloc(RX_BUF_SIZE, 1);
    furi_hal_serial_async_rx_start(app->serial, uart_rx_callback, app, false);

    app->uart_running = true;
    app->rx_thread = furi_thread_alloc_ex("GattroseRX", 2048, uart_rx_thread, app);
    furi_thread_start(app->rx_thread);

    app->connected = true;
    return true;
}

static void uart_deinit(App* app) {
    if(!app->uart_running) return;
    app->uart_running = false;

    if(app->rx_thread) {
        furi_thread_join(app->rx_thread);
        furi_thread_free(app->rx_thread);
        app->rx_thread = NULL;
    }
    if(app->serial) {
        furi_hal_serial_async_rx_stop(app->serial);
        furi_hal_serial_deinit(app->serial);
        furi_hal_serial_control_release(app->serial);
        app->serial = NULL;
    }
    if(app->rx_stream) {
        furi_stream_buffer_free(app->rx_stream);
        app->rx_stream = NULL;
    }
    app->connected = false;
}

// Send command with STX/ETX binary framing
// Format: [STX][cmd][args...][ETX]
static void uart_send(App* app, const char* cmd, size_t len) {
    if(!app->serial || !app->uart_running) return;
    if(len == 0) len = strlen(cmd);
    FURI_LOG_I(TAG, "TX: %s", cmd);

    // Send STX + command + ETX
    uint8_t stx = PROTO_STX;
    uint8_t etx = PROTO_ETX;
    furi_hal_serial_tx(app->serial, &stx, 1);
    furi_hal_serial_tx(app->serial, (uint8_t*)cmd, len);
    furi_hal_serial_tx(app->serial, &etx, 1);
    app->bytes_tx += len + 2;
}

// Send legacy command (no framing, for older firmware)
static void uart_send_legacy(App* app, const char* cmd, size_t len) {
    if(!app->serial || !app->uart_running) return;
    if(len == 0) len = strlen(cmd);
    FURI_LOG_I(TAG, "TX(legacy): %s", cmd);
    furi_hal_serial_tx(app->serial, (uint8_t*)cmd, len);
    furi_hal_serial_tx(app->serial, (uint8_t*)"\n", 1);
    app->bytes_tx += len + 1;
}

// ============================================================================
// Firmware Detection
// ============================================================================

static void detect_firmware(App* app) {
    if(!app->connected) return;

    app_log(app, "Detecting firmware...");

    // Reset detection state
    app->firmware_type = FirmwareUnknown;
    app->firmware_version[0] = '\0';
    app->firmware_response[0] = '\0';
    app->detection_done = false;
    app->got_pong = false;
    app->got_info = false;
    app->got_help = false;

    // Wait briefly for boot message (firmware sends 'r' response on boot)
    furi_delay_ms(500);

    // If we got the ready message from boot, we're done
    if(app->detection_done && app->firmware_type == FirmwareGattrose) {
        app_log(app, "Detected Gattrose-NG from boot message");
        goto detection_complete;
    }

    // Phase 1: Try new protocol - send 'i' (info) command
    uart_send(app, "i", 0);
    furi_delay_ms(500);

    if(app->detection_done || app->got_info) {
        if(app->firmware_type == FirmwareUnknown && app->got_info) {
            app->firmware_type = FirmwareGattrose;
        }
        goto detection_complete;
    }

    // Phase 2: Try legacy protocol - send INFO command
    uart_send_legacy(app, "INFO", 0);
    furi_delay_ms(500);

    if(app->detection_done) {
        goto detection_complete;
    }

    // Phase 3: Try legacy PING command
    uart_send_legacy(app, "PING", 0);
    furi_delay_ms(300);

    if(app->got_pong) {
        app_log(app, "Got PONG - likely Evil-BW16");
        app->firmware_type = FirmwareEvilBW16;
    }

    // Phase 4: Try HELP command for legacy firmware
    if(app->firmware_type == FirmwareUnknown) {
        uart_send_legacy(app, "HELP", 0);
        furi_delay_ms(500);
    }

    // Phase 5: Try AT command for generic firmware
    if(app->firmware_type == FirmwareUnknown) {
        uart_send_legacy(app, "AT", 0);
        furi_delay_ms(300);
    }

detection_complete:
    // Copy capabilities from firmware type
    if(app->firmware_type < sizeof(firmware_caps) / sizeof(firmware_caps[0])) {
        app->caps = firmware_caps[app->firmware_type];
    } else {
        app->caps = firmware_caps[0];  // Unknown defaults
    }

    // Log detection result
    app_log(app, "Firmware: %s", firmware_names[app->firmware_type]);

    if(app->firmware_version[0]) {
        app_log(app, "Version: %s", app->firmware_version);
    }

    // Log capabilities
    app_log(app, "Caps: scan=%d 5G=%d cli=%d tgt=%d ble=%d",
        app->caps.wifi_scan,
        app->caps.wifi_scan_5ghz,
        app->caps.client_detection,
        app->caps.targeted_deauth,
        app->caps.ble_scan);
}

static const char* get_firmware_name(App* app) {
    if(app->firmware_type < sizeof(firmware_names) / sizeof(firmware_names[0])) {
        return firmware_names[app->firmware_type];
    }
    return "Unknown";
}

// ============================================================================
// Protocol Parsing
// ============================================================================

static void console_append(App* app, const char* line);

// ============================================================================
// Binary Protocol Parser (STX/ETX framed messages)
// ============================================================================

// Parse network from binary message: n<idx>|<ssid>|<bssid>|<ch>|<rssi>|<band>|<clients>|<security>
static void parse_network_message(App* app, const char* data) {
    size_t data_len = strlen(data);
    FURI_LOG_I(TAG, "parse_network: len=%d first5=[%02X %02X %02X %02X %02X]",
        (int)data_len,
        data_len > 0 ? (uint8_t)data[0] : 0,
        data_len > 1 ? (uint8_t)data[1] : 0,
        data_len > 2 ? (uint8_t)data[2] : 0,
        data_len > 3 ? (uint8_t)data[3] : 0,
        data_len > 4 ? (uint8_t)data[4] : 0);

    if(app->network_count >= MAX_NETWORKS) {
        FURI_LOG_W(TAG, "Max networks reached");
        return;
    }

    char buffer[128];
    strncpy(buffer, data, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';

    // Replace PROTO_SEP with pipe for easier parsing
    int sep_count = 0;
    for(size_t i = 0; i < strlen(buffer); i++) {
        if(buffer[i] == PROTO_SEP) {
            buffer[i] = '|';
            sep_count++;
        }
    }
    FURI_LOG_I(TAG, "After SEP replace: sep_count=%d buf=[%.40s]", sep_count, buffer);

    Network* net = &app->networks[app->network_count];
    memset(net, 0, sizeof(Network));
    // Initialize client_indices to -1 (0 would be valid index)
    for(int i = 0; i < MAX_CLIENTS_PER_AP; i++) {
        net->client_indices[i] = -1;
    }

    TokenState ts;
    token_init(&ts, buffer);

    char* token = token_next(&ts, '|');
    if(!token) {
        FURI_LOG_E(TAG, "No index token");
        return;
    }
    net->id = atoi(token);
    FURI_LOG_I(TAG, "Got id=%d", net->id);

    token = token_next(&ts, '|'); if(!token) return;
    strncpy(net->ssid, token, MAX_SSID_LEN - 1);

    token = token_next(&ts, '|'); if(!token) return;
    strncpy(net->bssid, token, MAX_BSSID_LEN - 1);

    token = token_next(&ts, '|'); if(!token) return;
    net->channel = atoi(token);

    token = token_next(&ts, '|'); if(!token) return;
    net->rssi = atoi(token);

    token = token_next(&ts, '|');  // Band: 2 or 5
    if(token) {
        net->is_5ghz = (atoi(token) == 5);
    }

    token = token_next(&ts, '|');  // Client count
    if(token) {
        net->client_count = atoi(token);
        FURI_LOG_I(TAG, "Client count from firmware: %d", net->client_count);
    }

    token = token_next(&ts, '|');  // Security string
    if(token) {
        strncpy(net->security_str, token, sizeof(net->security_str) - 1);
    } else {
        strncpy(net->security_str, "???", sizeof(net->security_str) - 1);
    }

    token = token_next(&ts, '|');  // PMF (0 or 1)
    if(token) {
        net->has_pmf = (atoi(token) == 1);
    }

    token = token_next(&ts, '|');  // Hidden (0 or 1)
    if(token) {
        net->hidden = (atoi(token) == 1);
    }

    app->network_count++;
    FURI_LOG_I(TAG, "Added net #%d: %s ch%d", net->id, net->ssid, net->channel);
}

// Parse client from binary message: c<ap_idx>|<mac>|<rssi>
static void parse_client_message(App* app, const char* data) {
    if(app->client_count >= MAX_CLIENTS) return;

    char buffer[64];
    strncpy(buffer, data, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';

    // Replace PROTO_SEP with pipe
    for(size_t i = 0; i < strlen(buffer); i++) {
        if(buffer[i] == PROTO_SEP) buffer[i] = '|';
    }

    TokenState ts;
    token_init(&ts, buffer);

    char* token = token_next(&ts, '|');
    if(!token) return;
    int ap_idx = atoi(token);

    token = token_next(&ts, '|'); if(!token) return;
    char* client_mac = token;

    token = token_next(&ts, '|');
    int rssi = token ? atoi(token) : -80;

    // Check if client already exists
    for(int i = 0; i < app->client_count; i++) {
        if(strcmp(app->clients[i].mac, client_mac) == 0) return;
    }

    // Validate AP index
    if(ap_idx < 0 || ap_idx >= app->network_count) return;

    Client* client = &app->clients[app->client_count];
    strncpy(client->mac, client_mac, MAX_BSSID_LEN - 1);
    client->rssi = rssi;
    client->ap_index = ap_idx;

    // Add to AP's client list
    // Count how many indices we've actually added (ignore firmware's client_count)
    Network* net = &app->networks[ap_idx];
    int actual_count = 0;
    for(int i = 0; i < MAX_CLIENTS_PER_AP; i++) {
        if(net->client_indices[i] >= 0) actual_count++;
        else break;
    }
    if(actual_count < MAX_CLIENTS_PER_AP) {
        net->client_indices[actual_count] = app->client_count;
        // Update the actual client count for display
        if(actual_count + 1 > net->client_count) {
            net->client_count = actual_count + 1;
        }
    }
    app->client_count++;
}

// Parse BLE device from binary message: l<addr>|<name>|<rssi>
static void parse_ble_message(App* app, const char* data) {
    if(app->ble_count >= MAX_BLE_DEVICES) return;

    char buffer[128];
    strncpy(buffer, data, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';

    // Replace PROTO_SEP with pipe
    for(size_t i = 0; i < strlen(buffer); i++) {
        if(buffer[i] == PROTO_SEP) buffer[i] = '|';
    }

    BleDevice* dev = &app->ble_devices[app->ble_count];
    memset(dev, 0, sizeof(BleDevice));

    TokenState ts;
    token_init(&ts, buffer);

    char* token = token_next(&ts, '|');
    if(!token) return;
    strncpy(dev->address, token, MAX_BSSID_LEN - 1);

    token = token_next(&ts, '|');
    if(token) {
        strncpy(dev->name, token, sizeof(dev->name) - 1);
    } else {
        strncpy(dev->name, "Unknown", sizeof(dev->name) - 1);
    }

    token = token_next(&ts, '|');
    dev->rssi = token ? atoi(token) : -80;

    app->ble_count++;
}

// Parse credentials: C<user>|<pass>
static void parse_credential_message(App* app, const char* data) {
    char buffer[256];
    strncpy(buffer, data, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';

    // Replace PROTO_SEP with |
    for(size_t i = 0; i < strlen(buffer); i++) {
        if(buffer[i] == PROTO_SEP) buffer[i] = '|';
    }

    // Append to credentials buffer
    size_t current_len = strlen(app->credentials);
    size_t new_len = strlen(buffer);
    size_t space = sizeof(app->credentials) - current_len - 2;

    if(new_len < space) {
        memcpy(app->credentials + current_len, buffer, new_len);
        app->credentials[current_len + new_len] = '\n';
        app->credentials[current_len + new_len + 1] = '\0';
    }

    // Vibrate on credential capture
    if(app->notifications) {
        notification_message(app->notifications, &sequence_success);
    }

    FURI_LOG_I(TAG, "CRED: %s", buffer);
}

// Process binary protocol message (after STX/ETX framing stripped)
static void process_rx_message(App* app, const char* msg, size_t len) {
    if(len < 1) return;

    char resp_type = msg[0];
    const char* data = (len > 1) ? &msg[1] : "";

    // Log to console buffer for debugging
    char log_line[128];
    snprintf(log_line, sizeof(log_line), "[%c] %s", resp_type, data);
    console_append(app, log_line);

    switch(resp_type) {
        case RESP_READY:  // r - Boot/ready message OR LED response
            // LED responses: LED_OFF, LED_EFFECT:N, LED:R,G,B
            if(strncmp(data, "LED", 3) == 0) {
                FURI_LOG_I(TAG, "LED: %s", data);
                break;
            }
            // Boot/ready message (e.g., "GATTROSE-NG:2.0")
            app->firmware_type = FirmwareGattrose;
            strncpy(app->firmware_response, data, sizeof(app->firmware_response) - 1);
            if(strstr(data, ":")) {
                // Extract version after colon
                const char* ver = strstr(data, ":");
                if(ver) {
                    strncpy(app->firmware_version, ver + 1, sizeof(app->firmware_version) - 1);
                }
            }
            app->detection_done = true;
            FURI_LOG_I(TAG, "Gattrose-NG ready: %s", data);
            break;

        case RESP_SCAN:  // s - Scan status (SCANNING, DONE:N)
            if(strncmp(data, "DONE:", 5) == 0) {
                app->scan_finished = true;
                FURI_LOG_I(TAG, "Scan done: %s networks", data + 5);
            } else if(strcmp(data, "SCANNING") == 0) {
                app->scanning = true;
            }
            break;

        case RESP_NETWORK:  // n - Network entry
            parse_network_message(app, data);
            break;

        case RESP_CLIENT:  // c - Client entry
            FURI_LOG_I(TAG, "Client: %s", data);
            parse_client_message(app, data);
            break;

        case RESP_BLE:  // l - BLE device or BLE status
            if(strncmp(data, "SCAN_DONE:", 10) == 0) {
                FURI_LOG_I(TAG, "BLE scan done: %s devices", data + 10);
            } else if(strcmp(data, "BLE_SCANNING") == 0) {
                // BLE scan started
            } else if(strcmp(data, "BLE_SPAM_ON") == 0) {
                notification_message(app->notifications, &sequence_blink_start_magenta);
            } else if(strcmp(data, "BLE_STOP") == 0) {
                notification_message(app->notifications, &sequence_blink_stop);
            } else {
                // BLE device entry
                parse_ble_message(app, data);
            }
            break;

        case RESP_CREDS:  // C - Captured credentials
            parse_credential_message(app, data);
            break;

        case RESP_INFO:  // i - Info or count
            // Could be count (just a number) or full info string
            if(data[0] >= '0' && data[0] <= '9' && strlen(data) < 5) {
                // Just a count - e.g., "i15" for network count
                FURI_LOG_I(TAG, "Count: %s", data);
            } else {
                // Full info: V:2.1|N:64|C:8|CH:6|D:2|B:1|W:0|BLE:0
                FURI_LOG_I(TAG, "Info: %s", data);
                strncpy(app->firmware_response, data, sizeof(app->firmware_response) - 1);

                // Parse extended info
                char* p = strstr(data, "V:");
                if(p) {
                    char* end = strchr(p, '|');
                    if(end) {
                        size_t len = end - (p + 2);
                        if(len < sizeof(app->firmware_version) - 1) {
                            strncpy(app->firmware_version, p + 2, len);
                            app->firmware_version[len] = '\0';
                        }
                    }
                }
                p = strstr(data, "CH:");
                if(p) app->device_channel = atoi(p + 3);

                p = strstr(data, "D:");
                if(p) app->device_deauth_count = atoi(p + 2);

                p = strstr(data, "B:");
                if(p) app->device_beacon_active = (atoi(p + 2) == 1);

                p = strstr(data, "W:");
                if(p) app->device_ap_active = (atoi(p + 2) == 1);

                p = strstr(data, "BLE:");
                if(p) app->device_ble_count = atoi(p + 4);
            }
            app->got_info = true;
            break;

        case RESP_ERROR:  // e - Error message
            FURI_LOG_E(TAG, "Error: %s", data);
            break;

        case RESP_DEAUTH:  // d - Deauth status
            if(strncmp(data, "DEAUTH:", 6) == 0) {
                notification_message(app->notifications, &sequence_blink_start_red);
                FURI_LOG_I(TAG, "Deauth started: %s", data + 6);
            } else if(strcmp(data, "STOPPED") == 0) {
                notification_message(app->notifications, &sequence_blink_stop);
            }
            break;

        case RESP_WIFI:  // w - WiFi AP status
            if(strncmp(data, "AP_ON:", 6) == 0) {
                notification_message(app->notifications, &sequence_blink_start_blue);
                FURI_LOG_I(TAG, "AP started with portal %s", data + 6);
            } else if(strcmp(data, "AP_OFF") == 0) {
                notification_message(app->notifications, &sequence_blink_stop);
            }
            break;

        case RESP_BEACON:  // b - Beacon status
            if(strstr(data, "BEACON_RANDOM") || strstr(data, "BEACON_RICKROLL") ||
               strstr(data, "BEACON_CUSTOM")) {
                notification_message(app->notifications, &sequence_blink_start_green);
            } else if(strcmp(data, "BEACON_STOP") == 0) {
                notification_message(app->notifications, &sequence_blink_stop);
            }
            break;

        case RESP_MONITOR:  // m - Monitor mode status
            if(strstr(data, "ON") != NULL || strstr(data, "MONITOR_ON") != NULL) {
                app->monitor_active = true;
                FURI_LOG_I(TAG, "Monitor ON");
                notification_message(app->notifications, &sequence_blink_start_yellow);
            } else if(strstr(data, "OFF") != NULL || strstr(data, "MONITOR_OFF") != NULL) {
                app->monitor_active = false;
                FURI_LOG_I(TAG, "Monitor OFF");
                notification_message(app->notifications, &sequence_blink_stop);
            } else {
                FURI_LOG_I(TAG, "Monitor response: %s", data);
            }
            break;

        case RESP_STOP:  // x - Stop all confirmation
            notification_message(app->notifications, &sequence_blink_stop);
            app->monitor_active = false;
            for(int i = 0; i < app->network_count; i++) {
                app->networks[i].deauth_active = false;
            }
            FURI_LOG_I(TAG, "All stopped");
            break;

        case RESP_PORTAL:  // p - Portal changed
            if(strncmp(data, "PORTAL:", 7) == 0) {
                FURI_LOG_I(TAG, "Portal changed to %s", data + 7);
            }
            break;

        case RESP_APCONF:  // a - AP config set
            FURI_LOG_I(TAG, "AP config: %s", data);
            break;

        // Note: RESP_LED ('r') uses same char as RESP_READY - handled in RESP_READY case above

        case RESP_KICK:  // k - Client-only attack response
            if(strncmp(data, "CLIENT_DEAUTH:", 14) == 0) {
                FURI_LOG_I(TAG, "Client kick started: %s", data + 14);
                notification_message(app->notifications, &sequence_blink_start_red);
            } else if(strcmp(data, "CLIENT_NOT_FOUND") == 0) {
                FURI_LOG_W(TAG, "Client not found in detected list");
            }
            break;

        default:
            FURI_LOG_W(TAG, "Unknown response type '%c': %s", resp_type, data);
            break;
    }
}

static void console_append(App* app, const char* line) {
    size_t current_len = strlen(app->console_buffer);
    size_t line_len = strlen(line);
    size_t max_len = sizeof(app->console_buffer) - 2;

    // If buffer would overflow, remove first half
    if(current_len + line_len + 2 > max_len) {
        char* half = app->console_buffer + (max_len / 2);
        char* newline = strchr(half, '\n');
        if(newline) {
            memmove(app->console_buffer, newline + 1, strlen(newline + 1) + 1);
        } else {
            app->console_buffer[0] = '\0';
        }
        current_len = strlen(app->console_buffer);
    }

    // Append line manually (no strncat in Flipper SDK)
    size_t space = max_len - current_len;
    size_t to_copy = (line_len < space) ? line_len : space;
    memcpy(app->console_buffer + current_len, line, to_copy);
    current_len += to_copy;

    // Append newline
    if(current_len < max_len) {
        app->console_buffer[current_len++] = '\n';
    }
    app->console_buffer[current_len] = '\0';
}

static void process_rx_line(App* app, const char* line) {
    // Always log to console buffer for debugging
    console_append(app, line);

    if(strlen(line) < 2) return;

    // AP:|<id>|<ssid>|<bssid>|<channel>|<security>|<rssi>[|<client_count>]
    if(strncmp(line, "AP:", 3) == 0) {
        if(app->network_count >= MAX_NETWORKS) return;

        char buffer[128];
        strncpy(buffer, line, sizeof(buffer) - 1);
        buffer[sizeof(buffer) - 1] = '\0';

        // Replace colons with pipes for uniform parsing
        for(size_t i = 0; i < strlen(buffer); i++) {
            if(buffer[i] == ':') buffer[i] = '|';
        }

        TokenState ts;
        token_init(&ts, buffer);

        char* token = token_next(&ts, '|');  // "AP"
        if(!token) return;

        Network* net = &app->networks[app->network_count];
        memset(net, 0, sizeof(Network));
        for(int i = 0; i < MAX_CLIENTS_PER_AP; i++) net->client_indices[i] = -1;

        token = token_next(&ts, '|'); if(!token) return;
        net->id = atoi(token);

        token = token_next(&ts, '|'); if(!token) return;
        strncpy(net->ssid, token, MAX_SSID_LEN - 1);

        token = token_next(&ts, '|'); if(!token) return;
        strncpy(net->bssid, token, MAX_BSSID_LEN - 1);

        token = token_next(&ts, '|'); if(!token) return;
        net->channel = atoi(token);

        token = token_next(&ts, '|'); if(!token) return;
        net->security = atoi(token);

        token = token_next(&ts, '|'); if(!token) return;
        net->rssi = atoi(token);

        // Optional: client_count from custom firmware
        token = token_next(&ts, '|');
        net->client_count = token ? atoi(token) : 0;

        net->is_5ghz = (net->channel >= 36);
        app->network_count++;
    }
    // CLIENT:|<ap_id>|<client_mac>|<rssi> or CLIENT:NEW:|<ap_id>|<mac>|<rssi>
    else if(strncmp(line, "CLIENT:", 7) == 0 || strncmp(line, "STA:", 4) == 0) {
        if(app->client_count >= MAX_CLIENTS) return;

        char buffer[64];
        strncpy(buffer, line, sizeof(buffer) - 1);
        buffer[sizeof(buffer) - 1] = '\0';

        // Replace colons with pipes
        for(size_t i = 0; i < strlen(buffer); i++) {
            if(buffer[i] == ':') buffer[i] = '|';
        }

        TokenState ts;
        token_init(&ts, buffer);

        char* token = token_next(&ts, '|');  // "CLIENT" or "STA"
        if(!token) return;

        // Skip "NEW" if present (CLIENT|NEW|...)
        token = token_next(&ts, '|'); if(!token) return;
        if(strcmp(token, "NEW") == 0) {
            token = token_next(&ts, '|'); if(!token) return;
        }
        int ap_id = atoi(token);

        token = token_next(&ts, '|'); if(!token) return;
        char* client_mac = token;

        token = token_next(&ts, '|');
        int rssi = token ? atoi(token) : -80;

        // Find AP by ID
        int ap_index = -1;
        for(int i = 0; i < app->network_count; i++) {
            if(app->networks[i].id == ap_id) {
                ap_index = i;
                break;
            }
        }
        if(ap_index < 0) return;

        // Check if client already exists
        for(int i = 0; i < app->client_count; i++) {
            if(strcmp(app->clients[i].mac, client_mac) == 0) return;
        }

        Client* client = &app->clients[app->client_count];
        strncpy(client->mac, client_mac, MAX_BSSID_LEN - 1);
        client->rssi = rssi;
        client->ap_index = ap_index;

        // Add to AP's client list
        Network* net = &app->networks[ap_index];
        if(net->client_count < MAX_CLIENTS_PER_AP) {
            net->client_indices[net->client_count++] = app->client_count;
        }
        app->client_count++;
    }
    else if(strncmp(line, "SCAN:OK", 7) == 0) {
        app->scan_finished = true;
    }
    else if(strncmp(line, "EV:", 3) == 0) {
        // Captured credential - log and store
        const char* cred = line + 3;
        size_t current_len = strlen(app->credentials);
        size_t cred_len = strlen(cred);
        size_t space = sizeof(app->credentials) - current_len - 2;

        if(cred_len < space) {
            memcpy(app->credentials + current_len, cred, cred_len);
            app->credentials[current_len + cred_len] = '\n';
            app->credentials[current_len + cred_len + 1] = '\0';
        }

        // Also log to console with timestamp
        char log_msg[128];
        snprintf(log_msg, sizeof(log_msg), "[CRED] %s", cred);
        console_append(app, log_msg);

        // Vibrate on credential capture
        if(app->notifications) {
            notification_message(app->notifications, &sequence_success);
        }
    }
    else if(strncmp(line, "ERROR:", 6) == 0) {
        FURI_LOG_E(TAG, "Device: %s", line + 6);
    }
    // Handle deauth status from custom firmware
    else if(strncmp(line, "DEAUTH:", 7) == 0) {
        if(strstr(line, "STARTING")) {
            if(app->notifications) {
                notification_message(app->notifications, &sequence_blink_start_red);
            }
        } else if(strstr(line, "STOPPED")) {
            if(app->notifications) {
                notification_message(app->notifications, &sequence_blink_stop);
            }
        }
    }
    // Handle beacon status from custom firmware
    else if(strncmp(line, "BEACON:", 7) == 0) {
        if(strstr(line, "STARTING")) {
            if(app->notifications) {
                notification_message(app->notifications, &sequence_blink_start_magenta);
            }
        } else if(strstr(line, "STOPPED")) {
            if(app->notifications) {
                notification_message(app->notifications, &sequence_blink_stop);
            }
        }
    }
    // Handle BLE scan results from custom firmware
    else if(strncmp(line, "BLE:|", 5) == 0) {
        // BLE:|<mac>|<rssi>|<name> - just log to console for now
        FURI_LOG_I(TAG, "BLE: %s", line + 5);
    }
    // Handle scan status updates
    else if(strncmp(line, "SCAN:", 5) == 0) {
        if(strstr(line, "CLIENTS_FOUND")) {
            // Custom firmware reports client count
        }
    }
    // ========== Firmware Detection Responses ==========
    // PONG response
    else if(strcmp(line, "PONG") == 0) {
        app->got_pong = true;
    }
    // Gattrose-NG firmware identification
    else if(strncmp(line, "GATTROSE-BW16:", 14) == 0) {
        app->firmware_type = FirmwareGattrose;
        strncpy(app->firmware_response, line, sizeof(app->firmware_response) - 1);
        app->detection_done = true;
    }
    // INFO response - used for detection
    else if(strncmp(line, "INFO:", 5) == 0) {
        app->got_info = true;
        // Check for Gattrose signature
        if(strstr(line, "Gattrose")) {
            app->firmware_type = FirmwareGattrose;
            // Extract version if present
            const char* ver = strstr(line, "v");
            if(ver) {
                strncpy(app->firmware_version, ver, sizeof(app->firmware_version) - 1);
            }
        }
        // Check for Evil-BW16 signature
        else if(strstr(line, "Evil") || strstr(line, "BW16")) {
            app->firmware_type = FirmwareEvilBW16;
        }
        strncpy(app->firmware_response, line, sizeof(app->firmware_response) - 1);
    }
    // HELP response - used for detection
    else if(strncmp(line, "HELP:", 5) == 0) {
        app->got_help = true;
        // Check for Gattrose commands
        if(strstr(line, "BLESCAN") || strstr(line, "CLIENTS")) {
            app->firmware_type = FirmwareGattrose;
        }
    }
    // Marauder detection
    else if(strstr(line, "Marauder") || strstr(line, "ESP32")) {
        app->firmware_type = FirmwareMarauder;
        strncpy(app->firmware_response, line, sizeof(app->firmware_response) - 1);
        app->detection_done = true;
    }
    // Generic AT response
    else if(strcmp(line, "OK") == 0 && !app->detection_done) {
        // Generic AT firmware responds with just "OK"
        if(app->firmware_type == FirmwareUnknown) {
            app->firmware_type = FirmwareGeneric;
        }
    }
    // AT error response
    else if(strncmp(line, "AT+", 3) == 0 || strncmp(line, "+", 1) == 0) {
        app->firmware_type = FirmwareGeneric;
    }
}

// ============================================================================
// Commands
// ============================================================================

static void send_attack_config(App* app) {
    char cmd[32];

    // Send MAC
    snprintf(cmd, sizeof(cmd), "APMAC %s", app->custom_mac);
    uart_send(app, cmd, 0);
    furi_delay_ms(100);

    // Send reason
    snprintf(cmd, sizeof(cmd), "REASON %d", app->deauth_reason);
    uart_send(app, cmd, 0);
    furi_delay_ms(100);

    // Send portal
    snprintf(cmd, sizeof(cmd), "PORTAL %d", app->portal_type);
    uart_send(app, cmd, 0);
    furi_delay_ms(100);
}

static void do_scan(App* app) {
    bool just_connected = false;
    if(!app->connected) {
        if(!uart_init(app)) return;
        just_connected = true;
    }

    // Detect firmware on first connection
    if(just_connected || app->firmware_type == FirmwareUnknown) {
        detect_firmware(app);
    }

    // Clear previous results
    app->network_count = 0;
    app->client_count = 0;
    app->scan_finished = false;
    app->scanning = true;

    app_log(app, "Starting scan...");
    FURI_LOG_I(TAG, "Scan: firmware_type=%d", app->firmware_type);
    notification_message(app->notifications, &sequence_blink_start_cyan);

    // Use new protocol for Gattrose-NG, legacy for others
    if(app->firmware_type == FirmwareGattrose) {
        // Set LED to WiFi scan effect (cyan-blue-green pulse)
        uart_send(app, "r1", 0);
        furi_delay_ms(50);
        // New protocol: 's' to scan, 'g' to get results
        uart_send(app, "s", 0);  // Start scan with default 5000ms
    } else {
        // Legacy protocol
        uart_send_legacy(app, "SCAN", 0);
    }

    // Wait for scan completion
    int times = 0;
    while(!app->scan_finished && times < 20) {
        furi_delay_ms(500);
        times++;
    }

    // Request network list
    FURI_LOG_I(TAG, "Requesting network list...");
    if(app->firmware_type == FirmwareGattrose) {
        uart_send(app, "g", 0);  // Get networks
    } else {
        uart_send_legacy(app, "LIST", 0);
    }
    furi_delay_ms(1500);
    FURI_LOG_I(TAG, "After 1.5s wait: network_count=%d", app->network_count);

    // Request client list (only if firmware supports client detection)
    if(app->caps.client_detection) {
        if(app->firmware_type == FirmwareGattrose) {
            uart_send(app, "c", 0);  // Get clients
        } else {
            uart_send_legacy(app, "CLIENTS", 0);
        }
        furi_delay_ms(500);
    }

    // Sort networks
    sort_networks(app);

    app->scanning = false;

    // Set LED to green (ready state)
    if(app->firmware_type == FirmwareGattrose) {
        uart_send(app, "r0,255,0", 0);  // Green = ready
    }

    notification_message(app->notifications, &sequence_blink_stop);
    notification_message(app->notifications, &sequence_success);

    app_log(app, "Found %d APs, %d clients", app->network_count, app->client_count);
}

static void do_deauth(App* app) {
    int idx = app->selected_network;
    if(!app->connected || idx < 0 || idx >= app->network_count) return;

    Network* net = &app->networks[idx];
    char cmd[64];

    if(net->deauth_active) {
        // Stop deauth
        if(app->firmware_type == FirmwareGattrose) {
            uart_send(app, "ds", 0);  // Stop all deauth
            uart_send(app, "r0,255,0", 0);  // Green = ready
        } else {
            snprintf(cmd, sizeof(cmd), "STOP %d", net->id);
            uart_send_legacy(app, cmd, 0);
        }
        net->deauth_active = false;
        notification_message(app->notifications, &sequence_blink_stop);
    } else {
        // Start deauth
        if(app->firmware_type == FirmwareGattrose) {
            // Set LED to attack effect (red-orange pulse)
            uart_send(app, "r3", 0);
            furi_delay_ms(50);
            // New protocol: d<idx>[-<reason>]
            if(app->deauth_reason != 2) {  // Non-default reason
                snprintf(cmd, sizeof(cmd), "d%d-%d", net->id, app->deauth_reason);
            } else {
                snprintf(cmd, sizeof(cmd), "d%d", net->id);
            }
            uart_send(app, cmd, 0);
        } else {
            // Legacy protocol
            send_attack_config(app);
            snprintf(cmd, sizeof(cmd), "DEAUTH %d", net->id);
            uart_send_legacy(app, cmd, 0);
        }
        net->deauth_active = true;
        notification_message(app->notifications, &sequence_blink_start_red);
    }
    update_network_info(app);
}

static void do_evil_twin(App* app) {
    int idx = app->selected_network;
    if(!app->connected || idx < 0 || idx >= app->network_count) return;

    Network* net = &app->networks[idx];
    char cmd[128];

    // Log to console
    console_append(app, "=== EVIL TWIN START ===");
    snprintf(cmd, sizeof(cmd), "Target: %s", net->ssid[0] ? net->ssid : "<hidden>");
    console_append(app, cmd);
    snprintf(cmd, sizeof(cmd), "BSSID: %s", net->bssid);
    console_append(app, cmd);
    snprintf(cmd, sizeof(cmd), "Channel: %d", net->channel);
    console_append(app, cmd);
    snprintf(cmd, sizeof(cmd), "Portal: %s", portal_names[app->portal_type]);
    console_append(app, cmd);

    // Clear credentials buffer safely
    memset(app->credentials, 0, sizeof(app->credentials));

    if(app->firmware_type == FirmwareGattrose) {
        // Set LED to attack effect
        uart_send(app, "r3", 0);
        furi_delay_ms(50);

        // First configure AP settings: a<ssid>|<password>|<channel>
        // Use target network's SSID and channel, empty password for open AP
        const char* ssid = net->ssid[0] ? net->ssid : "Free_WiFi";
        snprintf(cmd, sizeof(cmd), "a%s||%d", ssid, net->channel);
        uart_send(app, cmd, 0);
        furi_delay_ms(100);

        // Then start evil twin with portal: w<portal_type>
        // Portal types: 0=stop, 1-7=portals
        int portal = app->portal_type;
        if(portal == 0) portal = 1;  // Default portal if "Stop" selected
        snprintf(cmd, sizeof(cmd), "w%d", portal);
        uart_send(app, cmd, 0);
    } else {
        // Legacy protocol
        snprintf(cmd, sizeof(cmd), "MAC: %s", app->custom_mac);
        console_append(app, cmd);
        send_attack_config(app);
        snprintf(cmd, sizeof(cmd), "EVIL %d", net->id);
        console_append(app, cmd);
        uart_send_legacy(app, cmd, 0);
    }

    notification_message(app->notifications, &sequence_blink_start_magenta);
}

static void do_beacon(App* app, int type) {
    if(!app->connected && !uart_init(app)) return;

    app->beacon_type = type;

    if(app->firmware_type == FirmwareGattrose) {
        // New protocol: b<mode>[ssid]
        // bs=stop, br=random, bk=rickroll, bc<ssid>=custom
        char cmd[48];
        if(type == 1) {
            uart_send(app, "br", 0);  // Random
        } else if(type == 2) {
            uart_send(app, "bk", 0);  // RickRoll
        } else if(type == 0 && app->beacon_ssid[0]) {
            snprintf(cmd, sizeof(cmd), "bc%s", app->beacon_ssid);
            uart_send(app, cmd, 0);  // Custom
        }
    } else {
        // Legacy protocol
        if(type == 1) {
            uart_send_legacy(app, "RANDOM", 0);
        } else if(type == 2) {
            uart_send_legacy(app, "RICKROLL", 0);
        } else if(type == 0 && app->beacon_ssid[0]) {
            char cmd[48];
            snprintf(cmd, sizeof(cmd), "BSSID %s", app->beacon_ssid);
            uart_send_legacy(app, cmd, 0);
        }
    }

    notification_message(app->notifications, &sequence_blink_start_green);
}

static void do_stop_beacon(App* app) {
    if(app && app->connected) {
        if(app->firmware_type == FirmwareGattrose) {
            uart_send(app, "bs", 0);  // Beacon stop
        } else {
            uart_send_legacy(app, "STOP", 0);
        }
    }
    if(app && app->notifications) {
        notification_message(app->notifications, &sequence_blink_stop);
    }
}

static void do_create_ap(App* app) {
    if(!app->connected && !uart_init(app)) return;

    char cmd[128];
    // Clear credentials buffer safely
    memset(app->credentials, 0, sizeof(app->credentials));

    if(app->firmware_type == FirmwareGattrose) {
        // Set LED to attack effect
        uart_send(app, "r3", 0);
        furi_delay_ms(50);

        // New protocol: a<ssid>|<password>|<channel> to configure AP
        // Then w<portal> to start
        const char* pw = (app->ap_security == 1 && app->ap_password[0]) ? app->ap_password : "";
        snprintf(cmd, sizeof(cmd), "a%s|%s|%d",
            app->ap_ssid, pw, atoi(channel_list[app->ap_channel]));
        uart_send(app, cmd, 0);
        furi_delay_ms(200);

        // Start evil twin with portal
        int portal = app->portal_type;
        if(portal == 0) portal = 1;  // Default portal
        snprintf(cmd, sizeof(cmd), "w%d", portal);
        uart_send(app, cmd, 0);
    } else {
        // Legacy protocol
        // Set password if WPA
        if(app->ap_security == 1 && app->ap_password[0]) {
            snprintf(cmd, sizeof(cmd), "PASSWORD %s", app->ap_password);
            uart_send_legacy(app, cmd, 0);
            furi_delay_ms(100);
        }

        // Set MAC
        snprintf(cmd, sizeof(cmd), "APMAC %s", app->custom_mac);
        uart_send_legacy(app, cmd, 0);
        furi_delay_ms(100);

        // Set channel
        snprintf(cmd, sizeof(cmd), "CHANNEL %s", channel_list[app->ap_channel]);
        uart_send_legacy(app, cmd, 0);
        furi_delay_ms(100);

        // Set portal
        snprintf(cmd, sizeof(cmd), "PORTAL %d", app->portal_type);
        uart_send_legacy(app, cmd, 0);
        furi_delay_ms(100);

        // Start AP
        snprintf(cmd, sizeof(cmd), "APSTART %s", app->ap_ssid);
        uart_send_legacy(app, cmd, 0);
    }

    notification_message(app->notifications, &sequence_blink_start_blue);
}

static void do_stop_all(App* app) {
    if(!app) return;
    console_append(app, "=== STOPPING ALL ===");
    if(app->connected) {
        if(app->firmware_type == FirmwareGattrose) {
            uart_send(app, "x", 0);  // Stop all operations
        } else {
            uart_send_legacy(app, "STOP", 0);
        }
    }
    for(int i = 0; i < app->network_count; i++) {
        app->networks[i].deauth_active = false;
    }
    app->monitor_active = false;

    // Reset advanced attack states
    app->jammer_active = false;
    app->probe_log_active = false;
    app->karma_active = false;
    app->pmkid_capture_active = false;
    app->handshake_capture_active = false;
    app->rogue_monitor_active = false;

    if(app->notifications) {
        notification_message(app->notifications, &sequence_blink_stop);
    }
}

// Client-only attack - kick a client without knowing which AP they're on
static void do_kick_client(App* app, const char* mac) {
    if(!app->connected || !mac || strlen(mac) < 17) return;

    if(app->firmware_type == FirmwareGattrose) {
        // Set LED to attack effect (red-orange pulse)
        uart_send(app, "r3", 0);
        furi_delay_ms(50);
        // New protocol: k<mac>[-reason]
        char cmd[32];
        if(app->deauth_reason != 2) {
            snprintf(cmd, sizeof(cmd), "k%s-%d", mac, app->deauth_reason);
        } else {
            snprintf(cmd, sizeof(cmd), "k%s", mac);
        }
        uart_send(app, cmd, 0);
        // Brief attack effect, then back to green
        furi_delay_ms(1000);
        uart_send(app, "r0,255,0", 0);  // Green = ready
    }
    // Legacy firmware doesn't support client-only attack
}

// LED control - use uart_send(app, "r<N>", 0) for effects:
//   r0 = off, r1 = WiFi scan, r2 = BLE scan, r3 = attack
//   r<R>,<G>,<B> = static color (e.g., "r255,0,0" for red)

// ============================================================================
// View Updates
// ============================================================================

static void update_network_list(App* app) {
    submenu_reset(app->network_list);

    // Count networks with clients
    int with_clients = 0;
    for(int i = 0; i < app->network_count; i++) {
        if(app->networks[i].client_count > 0) with_clients++;
    }

    // Show firmware and network count in header
    char header[48];
    if(app->show_all_networks) {
        snprintf(header, sizeof(header), "All APs (%d)", app->network_count);
    } else {
        snprintf(header, sizeof(header), "APs w/Clients (%d)", with_clients);
    }
    submenu_set_header(app->network_list, header);

    if(app->network_count == 0) {
        submenu_add_item(app->network_list, ">> Tap to Scan <<", 999, network_list_callback, app);
        return;
    }

    // Add toggle option at top
    if(app->show_all_networks) {
        submenu_add_item(app->network_list, "[Show Only w/Clients]", 998, network_list_callback, app);
    } else {
        submenu_add_item(app->network_list, "[Show All Networks]", 998, network_list_callback, app);
    }

    for(int i = 0; i < app->network_count; i++) {
        Network* net = &app->networks[i];

        // Skip networks without clients unless showing all
        if(!app->show_all_networks && net->client_count == 0) continue;

        char label[64];

        const char* prefix = net->deauth_active ? "D|" : "";
        const char* band = net->is_5ghz ? "5G" : "2G";

        // Handle *hidden* as hidden SSID (firmware sends this for empty SSIDs)
        bool is_hidden = (net->ssid[0] == '\0' ||
                          strcmp(net->ssid, "*hidden*") == 0 ||
                          net->hidden);
        const char* display_ssid = is_hidden ? "<hidden>" : net->ssid;

        if(net->client_count > 0) {
            snprintf(label, sizeof(label), "%s%s|%d|%s %ddB",
                prefix, band, net->client_count,
                display_ssid,
                net->rssi);
        } else {
            snprintf(label, sizeof(label), "%s%s|%s %ddB",
                prefix, band,
                display_ssid,
                net->rssi);
        }

        // Truncate if needed
        if(strlen(label) > 32) {
            label[29] = '.';
            label[30] = '.';
            label[31] = '\0';
        }

        submenu_add_item(app->network_list, label, i, network_list_callback, app);
    }

    submenu_set_selected_item(app->network_list, app->selected_network);
}

static void deauth_button_cb(GuiButtonType result, InputType type, void* context) {
    UNUSED(result);
    if(type == InputTypeShort) {
        App* app = context;
        do_deauth(app);
    }
}

static void evil_button_cb(GuiButtonType result, InputType type, void* context) {
    UNUSED(result);
    if(type == InputTypeShort) {
        App* app = context;
        do_evil_twin(app);
        update_evil_portal(app);
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdEvilPortal);
    }
}

static void config_button_cb(GuiButtonType result, InputType type, void* context) {
    UNUSED(result);
    if(type == InputTypeShort) {
        App* app = context;
        setup_attack_config(app);
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdAttackConfig);
    }
}

static void clients_button_cb(GuiButtonType result, InputType type, void* context) {
    UNUSED(result);
    if(type == InputTypeShort) {
        App* app = context;
        update_client_list(app);
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdClientList);
    }
}

static void update_network_info(App* app) {
    widget_reset(app->network_info);

    if(app->selected_network < 0 || app->selected_network >= app->network_count) {
        widget_add_string_element(
            app->network_info, 64, 32, AlignCenter, AlignCenter, FontPrimary, "No network");
        return;
    }

    Network* net = &app->networks[app->selected_network];

    // Use security_str if set (new protocol), otherwise use old integer method
    const char* sec_str = net->security_str[0] ? net->security_str : get_security_name(net->security);

    // Build info string with PMF warning if applicable
    char info[160];
    char flags[32] = "";

    // Build flags string using snprintf (strcat disabled in Flipper API)
    if(net->has_pmf && net->hidden) {
        snprintf(flags, sizeof(flags), " [PMF][HID]");
    } else if(net->has_pmf) {
        snprintf(flags, sizeof(flags), " [PMF]");
    } else if(net->hidden) {
        snprintf(flags, sizeof(flags), " [HID]");
    }

    snprintf(info, sizeof(info),
        "%s\n%s%s\nCh:%d %s %ddB\n%s\nClients: %d",
        net->ssid[0] ? net->ssid : "<hidden>",
        sec_str,
        flags,
        net->channel,
        net->is_5ghz ? "5GHz" : "2.4GHz",
        net->rssi,
        net->bssid,
        net->client_count);

    widget_add_string_multiline_element(
        app->network_info, 64, 40, AlignCenter, AlignBottom, FontSecondary, info);

    // Deauth button - show warning if PMF enabled
    if(net->deauth_active) {
        widget_add_button_element(app->network_info, GuiButtonTypeCenter, "Stop", deauth_button_cb, app);
    } else if(net->has_pmf) {
        // PMF enabled - deauth won't work, but still allow trying
        widget_add_button_element(app->network_info, GuiButtonTypeCenter, "Deauth!", deauth_button_cb, app);
    } else {
        widget_add_button_element(app->network_info, GuiButtonTypeCenter, "Deauth", deauth_button_cb, app);
    }

    // Evil twin button
    widget_add_button_element(app->network_info, GuiButtonTypeRight, "Evil", evil_button_cb, app);

    // Config / Clients button
    if(net->client_count > 0) {
        widget_add_button_element(app->network_info, GuiButtonTypeLeft, "Clients", clients_button_cb, app);
    } else {
        widget_add_button_element(app->network_info, GuiButtonTypeLeft, "Config", config_button_cb, app);
    }
}

static void update_client_list(App* app) {
    submenu_reset(app->client_list);

    if(app->selected_network < 0 || app->selected_network >= app->network_count) {
        submenu_set_header(app->client_list, "No AP selected");
        return;
    }

    Network* net = &app->networks[app->selected_network];
    char header[48];
    snprintf(header, sizeof(header), "%s (%d)",
        net->ssid[0] ? net->ssid : "<hidden>", net->client_count);
    submenu_set_header(app->client_list, header);

    if(net->client_count == 0) {
        submenu_add_item(app->client_list, "[No clients]", 0, NULL, NULL);
        return;
    }

    for(int i = 0; i < net->client_count; i++) {
        int ci = net->client_indices[i];
        if(ci >= 0 && ci < app->client_count) {
            Client* client = &app->clients[ci];
            char label[32];
            snprintf(label, sizeof(label), "%s %ddB", client->mac, client->rssi);
            submenu_add_item(app->client_list, label, i, client_list_callback, app);
        }
    }
}

static void update_evil_portal(App* app) {
    if(!app || !app->evil_portal) return;

    widget_reset(app->evil_portal);

    // Use static buffers to avoid potential memory issues
    static char ssid_display[MAX_SSID_LEN + 1];
    static char creds_display[520];

    // Safely copy SSID
    ssid_display[0] = '\0';
    if(app->selected_network >= 0 && app->selected_network < app->network_count) {
        Network* net = &app->networks[app->selected_network];
        if(net->ssid[0]) {
            strncpy(ssid_display, net->ssid, MAX_SSID_LEN);
            ssid_display[MAX_SSID_LEN] = '\0';
        }
    }

    // Safely copy credentials
    if(app->credentials[0]) {
        strncpy(creds_display, app->credentials, sizeof(creds_display) - 1);
        creds_display[sizeof(creds_display) - 1] = '\0';
    } else {
        strcpy(creds_display, "Waiting for credentials...");
    }

    widget_add_string_element(app->evil_portal, 64, 5, AlignCenter, AlignTop,
        FontPrimary, "Evil Twin Active");

    if(ssid_display[0]) {
        widget_add_string_element(app->evil_portal, 64, 18, AlignCenter, AlignTop,
            FontSecondary, ssid_display);
    }

    widget_add_text_scroll_element(app->evil_portal, 0, 28, 128, 36, creds_display);
}

static void update_beacon_active(App* app) {
    if(!app || !app->beacon_active) return;
    widget_reset(app->beacon_active);

    const char* type_str = "Custom";
    if(app->beacon_type == 1) type_str = "Random";
    else if(app->beacon_type == 2) type_str = "RickRoll";

    widget_add_string_element(app->beacon_active, 64, 10, AlignCenter, AlignTop,
        FontPrimary, type_str);

    if(app->beacon_type == 0) {
        widget_add_string_element(app->beacon_active, 64, 28, AlignCenter, AlignTop,
            FontSecondary, app->beacon_ssid);
    }

    widget_add_string_element(app->beacon_active, 64, 50, AlignCenter, AlignBottom,
        FontSecondary, "Press BACK to stop");
}

// ============================================================================
// Attack Config View
// ============================================================================

static void reason_change_cb(VariableItem* item) {
    App* app = variable_item_get_context(item);
    app->deauth_reason = variable_item_get_current_value_index(item);
    variable_item_set_current_value_text(item, deauth_reasons[app->deauth_reason]);
}

static void portal_change_cb(VariableItem* item) {
    App* app = variable_item_get_context(item);
    app->portal_type = variable_item_get_current_value_index(item);
    variable_item_set_current_value_text(item, portal_names[app->portal_type]);
}

static void mac_type_change_cb(VariableItem* item) {
    App* app = variable_item_get_context(item);
    app->mac_type = variable_item_get_current_value_index(item);
    variable_item_set_current_value_text(item, mac_types[app->mac_type]);

    if(app->mac_type == 0) {
        // Default
        strncpy(app->custom_mac, "00:E0:4C:01:02:03", MAX_BSSID_LEN);
    } else if(app->mac_type == 1) {
        // Random
        uint8_t mac[6];
        generate_random_mac(mac);
        mac_bytes_to_string(mac, app->custom_mac);
    } else if(app->mac_type == 3 && app->selected_network >= 0) {
        // Same as AP
        strncpy(app->custom_mac, app->networks[app->selected_network].bssid, MAX_BSSID_LEN);
    }
    mac_string_to_bytes(app->custom_mac, app->mac_bytes);
}

static void attack_config_enter_cb(void* context, uint32_t index) {
    App* app = context;
    if(index == 3) {
        // Custom MAC - open byte input
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdMacInput);
    }
}

static void setup_attack_config(App* app) {
    variable_item_list_reset(app->attack_config);

    VariableItem* item;

    item = variable_item_list_add(app->attack_config, "Deauth Reason", REASON_COUNT, reason_change_cb, app);
    variable_item_set_current_value_index(item, app->deauth_reason);
    variable_item_set_current_value_text(item, deauth_reasons[app->deauth_reason]);

    item = variable_item_list_add(app->attack_config, "Portal Type", PORTAL_COUNT, portal_change_cb, app);
    variable_item_set_current_value_index(item, app->portal_type);
    variable_item_set_current_value_text(item, portal_names[app->portal_type]);

    item = variable_item_list_add(app->attack_config, "MAC Type", MAC_TYPE_COUNT, mac_type_change_cb, app);
    variable_item_set_current_value_index(item, app->mac_type);
    variable_item_set_current_value_text(item, mac_types[app->mac_type]);

    if(app->mac_type == 2) {
        item = variable_item_list_add(app->attack_config, app->custom_mac, 0, NULL, NULL);
    }

    variable_item_list_set_enter_callback(app->attack_config, attack_config_enter_cb, app);
}

// ============================================================================
// Create AP View
// ============================================================================

static void ap_security_change_cb(VariableItem* item) {
    App* app = variable_item_get_context(item);
    app->ap_security = variable_item_get_current_value_index(item);
    variable_item_set_current_value_text(item, security_types[app->ap_security]);
}

static void ap_channel_change_cb(VariableItem* item) {
    App* app = variable_item_get_context(item);
    app->ap_channel = variable_item_get_current_value_index(item);
    variable_item_set_current_value_text(item, channel_list[app->ap_channel]);
}

static void ap_portal_change_cb(VariableItem* item) {
    App* app = variable_item_get_context(item);
    app->portal_type = variable_item_get_current_value_index(item);
    variable_item_set_current_value_text(item, portal_names[app->portal_type]);
}

static void create_ap_enter_cb(void* context, uint32_t index) {
    App* app = context;

    if(index == 0) {
        // SSID input
        text_input_reset(app->text_input);
        text_input_set_header_text(app->text_input, "AP Name");
        text_input_set_result_callback(app->text_input,
            ap_ssid_input_callback,
            app, app->ap_ssid, MAX_SSID_LEN, true);
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdApSsidInput);
    } else if(index == 2 && app->ap_security == 1) {
        // Password input
        text_input_reset(app->text_input);
        text_input_set_header_text(app->text_input, "AP Password");
        text_input_set_result_callback(app->text_input,
            ap_password_input_callback,
            app, app->ap_password, 63, true);
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdApPasswordInput);
    } else if((app->ap_security == 0 && index == 4) || (app->ap_security == 1 && index == 5)) {
        // Start button
        do_create_ap(app);
        update_evil_portal(app);
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdEvilPortal);
    }
}

static void setup_create_ap(App* app) {
    variable_item_list_reset(app->create_ap);
    VariableItem* item;

    // SSID
    item = variable_item_list_add(app->create_ap, "AP Name", 1, NULL, NULL);
    variable_item_set_current_value_text(item, app->ap_ssid[0] ? app->ap_ssid : "<set>");

    // Security
    item = variable_item_list_add(app->create_ap, "Security", 2, ap_security_change_cb, app);
    variable_item_set_current_value_index(item, app->ap_security);
    variable_item_set_current_value_text(item, security_types[app->ap_security]);

    // Password (if WPA)
    if(app->ap_security == 1) {
        item = variable_item_list_add(app->create_ap, "Password", 1, NULL, NULL);
        variable_item_set_current_value_text(item, app->ap_password[0] ? app->ap_password : "<set>");
    }

    // Channel
    item = variable_item_list_add(app->create_ap, "Channel", CHANNEL_COUNT, ap_channel_change_cb, app);
    variable_item_set_current_value_index(item, app->ap_channel);
    variable_item_set_current_value_text(item, channel_list[app->ap_channel]);

    // Portal
    item = variable_item_list_add(app->create_ap, "Portal", PORTAL_COUNT, ap_portal_change_cb, app);
    variable_item_set_current_value_index(item, app->portal_type);
    variable_item_set_current_value_text(item, portal_names[app->portal_type]);

    // Start button
    item = variable_item_list_add(app->create_ap, ">> Start AP <<", 1, NULL, app);

    variable_item_list_set_enter_callback(app->create_ap, create_ap_enter_cb, app);
}

// ============================================================================
// Client Sniff Functions
// ============================================================================

static void do_toggle_monitor(App* app) {
    if(!app->connected && !uart_init(app)) return;

    if(app->firmware_type == FirmwareGattrose) {
        if(app->monitor_active) {
            uart_send(app, "m0", 0);  // Disable monitor
            uart_send(app, "r0,255,0", 0);  // Green = ready
        } else {
            // Set LED to cyan pulse for monitor mode
            uart_send(app, "r1", 0);  // WiFi scan effect = monitor active
            furi_delay_ms(50);
            uart_send(app, "m1", 0);  // Enable monitor
        }
    } else {
        // Legacy: toggle sniff mode
        if(app->monitor_active) {
            uart_send_legacy(app, "SNIFFOFF", 0);
            app->monitor_active = false;
        } else {
            uart_send_legacy(app, "SNIFF", 0);
            app->monitor_active = true;
        }
    }
}

static void update_client_sniff_view(App* app);

static void client_sniff_callback(void* context, uint32_t index) {
    App* app = context;

    if(index == 0) {
        // Toggle monitor mode
        do_toggle_monitor(app);
        furi_delay_ms(300);
        update_client_sniff_view(app);
    } else if(index == 1) {
        // Refresh client list
        if(app->firmware_type == FirmwareGattrose) {
            uart_send(app, "c", 0);  // Get clients
        } else {
            uart_send_legacy(app, "CLIENTS", 0);
        }
        furi_delay_ms(500);
        update_client_sniff_view(app);
    } else if(index >= 200 && index < 200 + MAX_CLIENTS) {
        // Client selected - kick them
        int ci = index - 200;
        if(ci >= 0 && ci < app->client_count) {
            Client* client = &app->clients[ci];
            do_kick_client(app, client->mac);
        }
    }
}

// ============================================================================
// BLE Functions
// ============================================================================

static void do_ble_scan(App* app) {
    if(!app->connected && !uart_init(app)) return;
    app->ble_count = 0;

    if(app->firmware_type == FirmwareGattrose) {
        // Set LED to BLE scan effect (purple-magenta pulse)
        uart_send(app, "r2", 0);
        furi_delay_ms(50);
        uart_send(app, "ls", 0);  // BLE scan start
    } else {
        uart_send_legacy(app, "BLESCAN", 0);
    }
}

static void do_ble_get_list(App* app) {
    if(!app->connected) return;

    if(app->firmware_type == FirmwareGattrose) {
        uart_send(app, "lg", 0);  // Get BLE device list
    }
}

static void do_ble_stop(App* app) {
    if(!app->connected) return;

    if(app->firmware_type == FirmwareGattrose) {
        uart_send(app, "lx", 0);  // Stop BLE
    } else {
        uart_send_legacy(app, "BLESTOP", 0);
    }
    notification_message(app->notifications, &sequence_blink_stop);
}

static void update_ble_list(App* app);

static void ble_menu_callback(void* context, uint32_t index) {
    App* app = context;

    switch(index) {
        case 0:  // Scan
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdLoading);
            do_ble_scan(app);
            furi_delay_ms(6000);  // Wait for scan
            do_ble_get_list(app);
            furi_delay_ms(1000);
            // Set LED to green (ready state)
            if(app->firmware_type == FirmwareGattrose) {
                uart_send(app, "r0,255,0", 0);  // Green = ready
            }
            update_ble_list(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdBleList);
            break;

        case 1:  // View devices
            update_ble_list(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdBleList);
            break;

        case 2:  // BLE Spam - All types
            if(!app->connected && !uart_init(app)) break;
            uart_send(app, "lp4", 0);  // 4 = all types
            console_append(app, "BLE Spam: All types");
            break;

        case 3:  // Stop
            do_ble_stop(app);
            break;

        case 10:  // FastPair (Android)
            if(!app->connected && !uart_init(app)) break;
            uart_send(app, "lp1", 0);
            console_append(app, "BLE Spam: FastPair");
            break;

        case 11:  // SwiftPair (Windows)
            if(!app->connected && !uart_init(app)) break;
            uart_send(app, "lp2", 0);
            console_append(app, "BLE Spam: SwiftPair");
            break;

        case 12:  // AirTag
            if(!app->connected && !uart_init(app)) break;
            uart_send(app, "lp3", 0);
            console_append(app, "BLE Spam: AirTag");
            break;

        case 13:  // Random names
            if(!app->connected && !uart_init(app)) break;
            uart_send(app, "lp0", 0);
            console_append(app, "BLE Spam: Random");
            break;
    }
}

// ============================================================================
// LED Control
// ============================================================================

static void led_menu_callback(void* context, uint32_t index) {
    App* app = context;
    if(!app->connected) return;

    char cmd[16];

    switch(index) {
        case 0:  // LED Off
            uart_send(app, "r0", 0);
            console_append(app, "LED: Off");
            break;

        case 1:  // WiFi scan effect
            uart_send(app, "r1", 0);
            console_append(app, "LED: WiFi effect");
            break;

        case 2:  // BLE scan effect
            uart_send(app, "r2", 0);
            console_append(app, "LED: BLE effect");
            break;

        case 3:  // Attack effect
            uart_send(app, "r3", 0);
            console_append(app, "LED: Attack effect");
            break;

        case 4:  // Red
            uart_send(app, "r255,0,0", 0);
            console_append(app, "LED: Red");
            break;

        case 5:  // Green
            uart_send(app, "r0,255,0", 0);
            console_append(app, "LED: Green");
            break;

        case 6:  // Blue
            uart_send(app, "r0,0,255", 0);
            console_append(app, "LED: Blue");
            break;

        case 7:  // Cyan
            uart_send(app, "r0,255,255", 0);
            console_append(app, "LED: Cyan");
            break;

        case 8:  // Magenta
            uart_send(app, "r255,0,255", 0);
            console_append(app, "LED: Magenta");
            break;

        case 9:  // White
            uart_send(app, "r255,255,255", 0);
            console_append(app, "LED: White");
            break;
    }
    (void)cmd;  // Suppress unused warning
}

// Advanced attacks menu callback
static void advanced_menu_callback(void* context, uint32_t index) {
    App* app = context;
    if(!app->connected && !uart_init(app)) return;

    switch(index) {
        case AdvMenuIndexJammer:
            if(!app->jammer_active) {
                uart_send(app, "J1", 0);
                app->jammer_active = true;
                console_append(app, "Jammer: ON");
                // Set LED to attack mode
                uart_send(app, "r3", 0);
            } else {
                uart_send(app, "J0", 0);
                app->jammer_active = false;
                console_append(app, "Jammer: OFF");
                uart_send(app, "r0,255,0", 0);
            }
            break;

        case AdvMenuIndexProbeLog:
            if(!app->probe_log_active) {
                uart_send(app, "P1", 0);
                app->probe_log_active = true;
                console_append(app, "Probe Log: ON");
            } else {
                uart_send(app, "P0", 0);
                app->probe_log_active = false;
                console_append(app, "Probe Log: OFF");
            }
            break;

        case AdvMenuIndexKarma:
            if(!app->karma_active) {
                uart_send(app, "K1", 0);
                app->karma_active = true;
                console_append(app, "Karma: ON");
                uart_send(app, "r3", 0);
            } else {
                uart_send(app, "K0", 0);
                app->karma_active = false;
                console_append(app, "Karma: OFF");
                uart_send(app, "r0,255,0", 0);
            }
            break;

        case AdvMenuIndexPMKID:
            if(!app->pmkid_capture_active) {
                uart_send(app, "h1", 0);
                app->pmkid_capture_active = true;
                console_append(app, "PMKID Capture: ON");
            } else {
                uart_send(app, "hg", 0);  // Get captured PMKIDs
                furi_delay_ms(500);
                uart_send(app, "h0", 0);
                app->pmkid_capture_active = false;
                console_append(app, "PMKID Capture: OFF");
            }
            break;

        case AdvMenuIndexHandshake:
            if(!app->handshake_capture_active) {
                uart_send(app, "H1", 0);
                app->handshake_capture_active = true;
                console_append(app, "Handshake Capture: ON");
            } else {
                uart_send(app, "Hg", 0);  // Get captured handshakes
                furi_delay_ms(500);
                uart_send(app, "H0", 0);
                app->handshake_capture_active = false;
                console_append(app, "Handshake Capture: OFF");
            }
            break;

        case AdvMenuIndexRogueBase:
            uart_send(app, "R1", 0);  // Set baseline
            console_append(app, "Rogue AP baseline set");
            break;

        case AdvMenuIndexRogueMon:
            if(!app->rogue_monitor_active) {
                uart_send(app, "R2", 0);
                app->rogue_monitor_active = true;
                console_append(app, "Rogue Monitor: ON");
            } else {
                uart_send(app, "R0", 0);
                app->rogue_monitor_active = false;
                console_append(app, "Rogue Monitor: OFF");
            }
            break;

        case AdvMenuIndexBack:
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdMenu);
            break;
    }
}

// Navigation callback for advanced menu
static uint32_t nav_advanced_menu(void* context) {
    UNUSED(context);
    return ViewIdMenu;
}

// ============================================================================
// Callbacks
// ============================================================================

static void menu_callback(void* context, uint32_t index) {
    App* app = context;
    app->menu_index = index;

    switch(index) {
        case MenuIndexScan:
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdLoading);
            do_scan(app);
            update_network_list(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdNetworkList);
            break;

        case MenuIndexNetworks:
            update_network_list(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdNetworkList);
            break;

        case MenuIndexClientSniff:
            if(!app->connected && !uart_init(app)) break;
            update_client_sniff_view(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdClientSniff);
            break;

        case MenuIndexBeacon:
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdBeaconMenu);
            break;

        case MenuIndexCreateAp:
            setup_create_ap(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdCreateAp);
            break;

        case MenuIndexAdvanced:
            if(!app->connected && !uart_init(app)) break;
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdAdvancedMenu);
            break;

        case MenuIndexBle:
            if(!app->caps.ble_scan) {
                // BLE not supported on this firmware
                break;
            }
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdBleMenu);
            break;

        case MenuIndexLed:
            if(!app->connected && !uart_init(app)) break;
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdLedMenu);
            break;

        case MenuIndexStopAll:
            do_stop_all(app);
            // Set LED to green (ready state)
            if(app->connected && app->firmware_type == FirmwareGattrose) {
                uart_send(app, "r0,255,0", 0);  // Green = ready
            }
            break;

        case MenuIndexConsole:
            if(!app->connected && !uart_init(app)) break;
            app->console_mode = true;
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdConsoleMenu);
            break;

        case MenuIndexAbout:
            // Request device info to show status
            if(app->connected && app->firmware_type == FirmwareGattrose) {
                uart_send(app, "i", 0);
                furi_delay_ms(100);
            }
            update_about(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdAbout);
            break;

        case MenuIndexExit:
            do_stop_all(app);
            view_dispatcher_stop(app->view_dispatcher);
            break;
    }
}

static void network_list_callback(void* context, uint32_t index) {
    App* app = context;

    // Index 999 = trigger scan
    if(index == 999) {
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdLoading);
        do_scan(app);
        update_network_list(app);
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdNetworkList);
        return;
    }

    // Index 998 = toggle show all/clients only filter
    if(index == 998) {
        app->show_all_networks = !app->show_all_networks;
        update_network_list(app);
        return;
    }

    app->selected_network = index;
    update_network_info(app);
    view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdNetworkInfo);
}

static void client_list_callback(void* context, uint32_t index) {
    App* app = context;

    // Get the selected client
    if(app->selected_network < 0 || app->selected_network >= app->network_count) return;
    Network* net = &app->networks[app->selected_network];

    if((int)index >= net->client_count) return;

    int ci = net->client_indices[index];
    if(ci < 0 || ci >= app->client_count) return;

    Client* client = &app->clients[ci];

    // Perform targeted deauth to this client
    if(app->firmware_type == FirmwareGattrose) {
        // New protocol: d<idx>-<reason>-<MAC>
        char cmd[64];
        snprintf(cmd, sizeof(cmd), "d%d-%d-%s",
            net->id, app->deauth_reason, client->mac);
        uart_send(app, cmd, 0);
    } else if(app->caps.targeted_deauth) {
        // Legacy: DEAUTH <idx> <MAC>
        char cmd[64];
        snprintf(cmd, sizeof(cmd), "DEAUTH %d %s", net->id, client->mac);
        uart_send_legacy(app, cmd, 0);
    } else {
        // Firmware doesn't support targeted deauth
        return;
    }

    notification_message(app->notifications, &sequence_blink_start_red);
    net->deauth_active = true;
}

static void beacon_menu_callback(void* context, uint32_t index) {
    App* app = context;

    if(index == 0) {
        // Custom SSID
        text_input_reset(app->text_input);
        text_input_set_header_text(app->text_input, "Beacon SSID");
        text_input_set_result_callback(app->text_input,
            beacon_ssid_input_callback,
            app, app->beacon_ssid, MAX_SSID_LEN, true);
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdBeaconSsidInput);
    } else if(index == 1) {
        // Random
        do_beacon(app, 1);
        update_beacon_active(app);
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdBeaconActive);
    } else if(index == 2) {
        // RickRoll
        do_beacon(app, 2);
        update_beacon_active(app);
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdBeaconActive);
    }
}

static void update_about(App* app) {
    popup_reset(app->about_popup);
    popup_set_header(app->about_popup, "Gattrose-NG", 64, 3, AlignCenter, AlignTop);

    static char about[256];  // Static to persist after function returns

    if(app->firmware_type != FirmwareUnknown) {
        // Show firmware info with device status
        char status[64] = "";
        if(app->firmware_type == FirmwareGattrose && app->firmware_version[0]) {
            // Show active attacks/features
            if(app->device_deauth_count > 0 || app->device_beacon_active || app->device_ap_active) {
                snprintf(status, sizeof(status), "\nActive: %s%s%s",
                    app->device_deauth_count > 0 ? "Deauth " : "",
                    app->device_beacon_active ? "Beacon " : "",
                    app->device_ap_active ? "AP " : "");
            }
        }

        snprintf(about, sizeof(about),
            "v%s \"%s\"\n"
            "FW: %s %s\n"
            "%s%s%s%s%s",
            APP_VERSION, APP_CODENAME,
            get_firmware_name(app),
            app->firmware_version[0] ? app->firmware_version : "",
            app->caps.wifi_scan_5ghz ? "5G " : "",
            app->caps.client_detection ? "CLI " : "",
            app->caps.ble_scan ? "BLE " : "",
            app->caps.targeted_deauth ? "TGT" : "",
            status);
    } else {
        snprintf(about, sizeof(about),
            "v%s \"%s\"\n"
            "RTL8720 Dual-Band\n"
            "WiFi Audit Suite\n\n"
            "Firmware: Not detected\n"
            "Scan to auto-detect",
            APP_VERSION, APP_CODENAME);
    }

    popup_set_text(app->about_popup, about, 64, 18, AlignCenter, AlignTop);
}

// Update client sniff view
static void update_client_sniff_view(App* app) {
    submenu_reset(app->client_sniff);

    char header[48];
    snprintf(header, sizeof(header), "Client Sniff (%d)", app->client_count);
    submenu_set_header(app->client_sniff, header);

    // Toggle monitor mode option
    if(app->monitor_active) {
        submenu_add_item(app->client_sniff, "[*] Monitor: ON", 0, client_sniff_callback, app);
    } else {
        submenu_add_item(app->client_sniff, "[ ] Monitor: OFF", 0, client_sniff_callback, app);
    }

    // Refresh clients option
    submenu_add_item(app->client_sniff, "Refresh Clients", 1, client_sniff_callback, app);

    // Show detected clients grouped by AP
    for(int n = 0; n < app->network_count; n++) {
        Network* net = &app->networks[n];
        if(net->client_count > 0) {
            // Add AP header
            char ap_label[64];
            snprintf(ap_label, sizeof(ap_label), "-- %s (%d) --",
                net->ssid[0] ? net->ssid : "<hidden>", net->client_count);
            submenu_add_item(app->client_sniff, ap_label, 100 + n, NULL, NULL);

            // Add clients for this AP - clicking kicks them
            for(int c = 0; c < net->client_count && c < MAX_CLIENTS_PER_AP; c++) {
                int ci = net->client_indices[c];
                if(ci >= 0 && ci < app->client_count) {
                    Client* client = &app->clients[ci];
                    char client_label[48];
                    snprintf(client_label, sizeof(client_label), "> %s %ddB",
                        client->mac, client->rssi);
                    submenu_add_item(app->client_sniff, client_label, 200 + ci, client_sniff_callback, app);
                }
            }
        }
    }

    if(app->client_count == 0) {
        submenu_add_item(app->client_sniff, "[No clients detected]", 999, NULL, NULL);
    }
}

// Update BLE device list
static void update_ble_list(App* app) {
    submenu_reset(app->ble_list);

    char header[48];
    snprintf(header, sizeof(header), "BLE Devices (%d)", app->ble_count);
    submenu_set_header(app->ble_list, header);

    if(app->ble_count == 0) {
        submenu_add_item(app->ble_list, "[No devices found]", 0, NULL, NULL);
        submenu_add_item(app->ble_list, ">> Scan to find devices <<", 999, NULL, NULL);
        return;
    }

    for(int i = 0; i < app->ble_count; i++) {
        BleDevice* dev = &app->ble_devices[i];
        char label[40];
        char name_trunc[24];

        if(dev->name[0] && strcmp(dev->name, "Unknown") != 0) {
            // Truncate name to prevent overflow
            strncpy(name_trunc, dev->name, sizeof(name_trunc) - 1);
            name_trunc[sizeof(name_trunc) - 1] = '\0';
            snprintf(label, sizeof(label), "%.20s %ddB", name_trunc, dev->rssi);
        } else {
            snprintf(label, sizeof(label), "%s %ddB", dev->address, dev->rssi);
        }
        submenu_add_item(app->ble_list, label, i, NULL, NULL);
    }
}

static void console_menu_callback(void* context, uint32_t index) {
    App* app = context;

    switch(index) {
        case 0: // View Output
            update_console(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdConsoleOutput);
            break;
        case 1: // Send Custom Command
            text_input_reset(app->text_input);
            text_input_set_header_text(app->text_input, "Command:");
            text_input_set_result_callback(app->text_input,
                console_send_callback, app, app->console_cmd, 63, false);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdConsoleSend);
            break;
        case 2: // help
            uart_send(app, "help", 0);
            console_append(app, "> help");
            update_console(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdConsoleOutput);
            break;
        case 3: // scan
            uart_send(app, "scan", 0);
            console_append(app, "> scan");
            update_console(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdConsoleOutput);
            break;
        case 4: // results / list
            uart_send(app, "results", 0);
            console_append(app, "> results");
            furi_delay_ms(200);
            uart_send(app, "list", 0);
            console_append(app, "> list");
            update_console(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdConsoleOutput);
            break;
        case 5: // info
            uart_send(app, "info", 0);
            console_append(app, "> info");
            update_console(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdConsoleOutput);
            break;
        case 6: // Clear buffer
            app->console_buffer[0] = '\0';
            update_console(app);
            break;
        case 7: // Detect Firmware
            console_append(app, "=== DETECTING FIRMWARE ===");
            detect_firmware(app);
            char fw_msg[64];
            snprintf(fw_msg, sizeof(fw_msg), "Detected: %s", get_firmware_name(app));
            console_append(app, fw_msg);
            update_console(app);
            view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdConsoleOutput);
            break;
    }
}

static void mac_input_callback(void* context) {
    App* app = context;
    mac_bytes_to_string(app->mac_bytes, app->custom_mac);
    view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdAttackConfig);
}

static void beacon_ssid_input_callback(void* context) {
    App* app = context;
    if(app->beacon_ssid[0]) {
        do_beacon(app, 0);
        update_beacon_active(app);
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdBeaconActive);
    } else {
        view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdBeaconMenu);
    }
}

static void ap_ssid_input_callback(void* context) {
    App* app = context;
    setup_create_ap(app);
    view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdCreateAp);
}

static void ap_password_input_callback(void* context) {
    App* app = context;
    setup_create_ap(app);
    view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdCreateAp);
}

static void console_send_callback(void* context) {
    App* app = context;
    if(app->console_cmd[0]) {
        // Echo command to console
        char echo[80];
        snprintf(echo, sizeof(echo), "> %s", app->console_cmd);
        console_append(app, echo);

        // Send to device
        uart_send(app, app->console_cmd, 0);
        app->console_cmd[0] = '\0';
    }
    // Update console view and return
    text_box_set_text(app->log_view, app->console_buffer);
    view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdConsoleOutput);
}

static void update_console(App* app) {
    text_box_set_text(app->log_view, app->console_buffer);
}

// Navigation callbacks
static uint32_t nav_menu(void* context) { UNUSED(context); return ViewIdMenu; }
static uint32_t nav_network_list(void* context) { UNUSED(context); return ViewIdNetworkList; }
static uint32_t nav_network_info(void* context) { UNUSED(context); return ViewIdNetworkInfo; }
static uint32_t nav_console_menu(void* context) { UNUSED(context); return ViewIdConsoleMenu; }
static uint32_t nav_exit(void* context) { UNUSED(context); return VIEW_NONE; }

static uint32_t nav_beacon_stop(void* context) {
    App* app = context;
    do_stop_beacon(app);
    return ViewIdBeaconMenu;
}

static uint32_t nav_evil_stop(void* context) {
    App* app = context;
    do_stop_all(app);
    // Set LED to green (ready state)
    if(app && app->connected && app->firmware_type == FirmwareGattrose) {
        uart_send(app, "r0,255,0", 0);  // Green = ready
    }
    // Return to menu if no valid network selected, otherwise network list
    if(!app || app->selected_network < 0 || app->selected_network >= app->network_count) {
        return ViewIdMenu;
    }
    return ViewIdNetworkList;
}

// ============================================================================
// App Lifecycle
// ============================================================================

static App* app_alloc(void) {
    App* app = malloc(sizeof(App));
    memset(app, 0, sizeof(App));

    // Disable expansion (uses UART)
    app->expansion = furi_record_open(RECORD_EXPANSION);
    expansion_disable(app->expansion);

    // Enable 5V
    if(!furi_hal_power_is_otg_enabled()) {
        furi_hal_power_enable_otg();
    }

    // Services
    app->gui = furi_record_open(RECORD_GUI);
    app->notifications = furi_record_open(RECORD_NOTIFICATION);
    app->storage = furi_record_open(RECORD_STORAGE);
    ensure_app_dir(app);

    app->mutex = furi_mutex_alloc(FuriMutexTypeNormal);

    // Defaults
    app->deauth_reason = 2;
    app->portal_type = 0;
    app->mac_type = 0;
    strncpy(app->custom_mac, "00:E0:4C:01:02:03", MAX_BSSID_LEN);
    mac_string_to_bytes(app->custom_mac, app->mac_bytes);
    strncpy(app->ap_ssid, "FreeWiFi", MAX_SSID_LEN);
    strncpy(app->ap_password, "password123", 63);
    app->ap_channel = 5;  // Channel 6

    // View dispatcher
    app->view_dispatcher = view_dispatcher_alloc();
    view_dispatcher_set_event_callback_context(app->view_dispatcher, app);
    view_dispatcher_attach_to_gui(app->view_dispatcher, app->gui, ViewDispatcherTypeFullscreen);

    // Splash screen
    app->splash = widget_alloc();
    view_dispatcher_add_view(app->view_dispatcher, ViewIdSplash, widget_get_view(app->splash));

    // Main menu - cleaner layout
    app->menu = menu_alloc();
    menu_add_item(app->menu, "Scan Networks", NULL, MenuIndexScan, menu_callback, app);
    menu_add_item(app->menu, "View Networks", NULL, MenuIndexNetworks, menu_callback, app);
    menu_add_item(app->menu, "Client Sniff", NULL, MenuIndexClientSniff, menu_callback, app);
    menu_add_item(app->menu, "Beacon Spam", NULL, MenuIndexBeacon, menu_callback, app);
    menu_add_item(app->menu, "Create AP", NULL, MenuIndexCreateAp, menu_callback, app);
    menu_add_item(app->menu, "Advanced Attacks", NULL, MenuIndexAdvanced, menu_callback, app);
    menu_add_item(app->menu, "BLE Tools", NULL, MenuIndexBle, menu_callback, app);
    menu_add_item(app->menu, "LED Control", NULL, MenuIndexLed, menu_callback, app);
    menu_add_item(app->menu, "Stop All", NULL, MenuIndexStopAll, menu_callback, app);
    menu_add_item(app->menu, "Serial Console", NULL, MenuIndexConsole, menu_callback, app);
    menu_add_item(app->menu, "About", NULL, MenuIndexAbout, menu_callback, app);
    menu_add_item(app->menu, "Exit", NULL, MenuIndexExit, menu_callback, app);
    view_set_previous_callback(menu_get_view(app->menu), nav_exit);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdMenu, menu_get_view(app->menu));

    // Loading
    app->loading = loading_alloc();
    view_dispatcher_add_view(app->view_dispatcher, ViewIdLoading, loading_get_view(app->loading));

    // Network list
    app->network_list = submenu_alloc();
    submenu_set_header(app->network_list, "Networks");
    view_set_previous_callback(submenu_get_view(app->network_list), nav_menu);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdNetworkList, submenu_get_view(app->network_list));

    // Network info
    app->network_info = widget_alloc();
    view_set_previous_callback(widget_get_view(app->network_info), nav_network_list);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdNetworkInfo, widget_get_view(app->network_info));

    // Client list
    app->client_list = submenu_alloc();
    view_set_previous_callback(submenu_get_view(app->client_list), nav_network_info);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdClientList, submenu_get_view(app->client_list));

    // Client sniff menu
    app->client_sniff = submenu_alloc();
    submenu_set_header(app->client_sniff, "Client Sniff");
    view_set_previous_callback(submenu_get_view(app->client_sniff), nav_menu);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdClientSniff, submenu_get_view(app->client_sniff));

    // BLE menu - expanded with spam types
    app->ble_menu = submenu_alloc();
    submenu_set_header(app->ble_menu, "BLE Tools");
    submenu_add_item(app->ble_menu, "Scan Devices", 0, ble_menu_callback, app);
    submenu_add_item(app->ble_menu, "View Devices", 1, ble_menu_callback, app);
    submenu_add_item(app->ble_menu, "Spam: All Types", 2, ble_menu_callback, app);
    submenu_add_item(app->ble_menu, "Spam: FastPair (Android)", 10, ble_menu_callback, app);
    submenu_add_item(app->ble_menu, "Spam: SwiftPair (Windows)", 11, ble_menu_callback, app);
    submenu_add_item(app->ble_menu, "Spam: AirTag", 12, ble_menu_callback, app);
    submenu_add_item(app->ble_menu, "Spam: Random Names", 13, ble_menu_callback, app);
    submenu_add_item(app->ble_menu, "Stop BLE", 3, ble_menu_callback, app);
    view_set_previous_callback(submenu_get_view(app->ble_menu), nav_menu);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdBleMenu, submenu_get_view(app->ble_menu));

    // BLE device list
    app->ble_list = submenu_alloc();
    submenu_set_header(app->ble_list, "BLE Devices");
    view_set_previous_callback(submenu_get_view(app->ble_list), nav_menu);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdBleList, submenu_get_view(app->ble_list));

    // LED control menu
    app->led_menu = submenu_alloc();
    submenu_set_header(app->led_menu, "LED Control");
    submenu_add_item(app->led_menu, "Off", 0, led_menu_callback, app);
    submenu_add_item(app->led_menu, "WiFi Scan Effect", 1, led_menu_callback, app);
    submenu_add_item(app->led_menu, "BLE Scan Effect", 2, led_menu_callback, app);
    submenu_add_item(app->led_menu, "Attack Effect", 3, led_menu_callback, app);
    submenu_add_item(app->led_menu, "Red", 4, led_menu_callback, app);
    submenu_add_item(app->led_menu, "Green", 5, led_menu_callback, app);
    submenu_add_item(app->led_menu, "Blue", 6, led_menu_callback, app);
    submenu_add_item(app->led_menu, "Cyan", 7, led_menu_callback, app);
    submenu_add_item(app->led_menu, "Magenta", 8, led_menu_callback, app);
    submenu_add_item(app->led_menu, "White", 9, led_menu_callback, app);
    view_set_previous_callback(submenu_get_view(app->led_menu), nav_menu);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdLedMenu, submenu_get_view(app->led_menu));

    // Attack config
    app->attack_config = variable_item_list_alloc();
    view_set_previous_callback(variable_item_list_get_view(app->attack_config), nav_network_info);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdAttackConfig, variable_item_list_get_view(app->attack_config));

    // MAC input
    app->mac_input = byte_input_alloc();
    byte_input_set_header_text(app->mac_input, "Custom MAC");
    byte_input_set_result_callback(app->mac_input, mac_input_callback, NULL, app, app->mac_bytes, MAC_LENGTH);
    view_set_previous_callback(byte_input_get_view(app->mac_input), nav_network_info);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdMacInput, byte_input_get_view(app->mac_input));

    // Beacon menu
    app->beacon_menu = submenu_alloc();
    submenu_set_header(app->beacon_menu, "Beacon Type");
    submenu_add_item(app->beacon_menu, "Custom SSID", 0, beacon_menu_callback, app);
    submenu_add_item(app->beacon_menu, "Random SSIDs", 1, beacon_menu_callback, app);
    submenu_add_item(app->beacon_menu, "RickRoll", 2, beacon_menu_callback, app);
    view_set_previous_callback(submenu_get_view(app->beacon_menu), nav_menu);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdBeaconMenu, submenu_get_view(app->beacon_menu));

    // Text input (shared)
    app->text_input = text_input_alloc();
    view_set_previous_callback(text_input_get_view(app->text_input), nav_menu);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdBeaconSsidInput, text_input_get_view(app->text_input));
    view_dispatcher_add_view(app->view_dispatcher, ViewIdApSsidInput, text_input_get_view(app->text_input));
    view_dispatcher_add_view(app->view_dispatcher, ViewIdApPasswordInput, text_input_get_view(app->text_input));

    // Beacon active
    app->beacon_active = widget_alloc();
    view_set_previous_callback(widget_get_view(app->beacon_active), nav_beacon_stop);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdBeaconActive, widget_get_view(app->beacon_active));

    // Create AP
    app->create_ap = variable_item_list_alloc();
    view_set_previous_callback(variable_item_list_get_view(app->create_ap), nav_menu);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdCreateAp, variable_item_list_get_view(app->create_ap));

    // Evil portal
    app->evil_portal = widget_alloc();
    view_set_previous_callback(widget_get_view(app->evil_portal), nav_evil_stop);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdEvilPortal, widget_get_view(app->evil_portal));

    // Console menu
    app->console_menu = submenu_alloc();
    submenu_set_header(app->console_menu, "Serial Console");
    submenu_add_item(app->console_menu, "View Output", 0, console_menu_callback, app);
    submenu_add_item(app->console_menu, "Send Command", 1, console_menu_callback, app);
    submenu_add_item(app->console_menu, "Send: help", 2, console_menu_callback, app);
    submenu_add_item(app->console_menu, "Send: scan", 3, console_menu_callback, app);
    submenu_add_item(app->console_menu, "Send: results", 4, console_menu_callback, app);
    submenu_add_item(app->console_menu, "Send: info", 5, console_menu_callback, app);
    submenu_add_item(app->console_menu, "Clear Buffer", 6, console_menu_callback, app);
    submenu_add_item(app->console_menu, "Detect Firmware", 7, console_menu_callback, app);
    view_set_previous_callback(submenu_get_view(app->console_menu), nav_menu);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdConsoleMenu, submenu_get_view(app->console_menu));

    // Advanced attacks menu
    app->advanced_menu = submenu_alloc();
    submenu_set_header(app->advanced_menu, "Advanced Attacks");
    submenu_add_item(app->advanced_menu, "WiFi Jammer", AdvMenuIndexJammer, advanced_menu_callback, app);
    submenu_add_item(app->advanced_menu, "Probe Logger", AdvMenuIndexProbeLog, advanced_menu_callback, app);
    submenu_add_item(app->advanced_menu, "Karma Attack", AdvMenuIndexKarma, advanced_menu_callback, app);
    submenu_add_item(app->advanced_menu, "PMKID Capture", AdvMenuIndexPMKID, advanced_menu_callback, app);
    submenu_add_item(app->advanced_menu, "Handshake Capture", AdvMenuIndexHandshake, advanced_menu_callback, app);
    submenu_add_item(app->advanced_menu, "Set Rogue Baseline", AdvMenuIndexRogueBase, advanced_menu_callback, app);
    submenu_add_item(app->advanced_menu, "Rogue AP Monitor", AdvMenuIndexRogueMon, advanced_menu_callback, app);
    view_set_previous_callback(submenu_get_view(app->advanced_menu), nav_advanced_menu);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdAdvancedMenu, submenu_get_view(app->advanced_menu));

    // Console output
    app->log_view = text_box_alloc();
    text_box_set_font(app->log_view, TextBoxFontText);
    view_set_previous_callback(text_box_get_view(app->log_view), nav_console_menu);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdConsoleOutput, text_box_get_view(app->log_view));
    view_dispatcher_add_view(app->view_dispatcher, ViewIdLog, text_box_get_view(app->log_view));

    // Console send input (shared text_input)
    view_dispatcher_add_view(app->view_dispatcher, ViewIdConsoleSend, text_input_get_view(app->text_input));

    // About
    app->about_popup = popup_alloc();
    popup_set_header(app->about_popup, "Gattrose-NG", 64, 5, AlignCenter, AlignTop);
    char about[128];
    snprintf(about, sizeof(about),
        "v%s \"%s\"\n\n"
        "RTL8720 Dual-Band\n"
        "WiFi Audit Suite\n\n"
        "2.4GHz + 5GHz",
        APP_VERSION, APP_CODENAME);
    popup_set_text(app->about_popup, about, 64, 20, AlignCenter, AlignTop);
    view_set_previous_callback(popup_get_view(app->about_popup), nav_menu);
    view_dispatcher_add_view(app->view_dispatcher, ViewIdAbout, popup_get_view(app->about_popup));

    // Initialize console buffer
    app->console_buffer[0] = '\0';
    snprintf(app->console_buffer, sizeof(app->console_buffer),
        "Gattrose-NG v%s\nSerial Console Ready\n---\n", APP_VERSION);

    // Start
    view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdMenu);
    app_log(app, "Gattrose-NG v%s started", APP_VERSION);

    return app;
}

static void app_free(App* app) {
    app_log(app, "Shutting down");

    do_stop_all(app);
    uart_deinit(app);

    view_dispatcher_remove_view(app->view_dispatcher, ViewIdSplash);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdMenu);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdLoading);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdNetworkList);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdNetworkInfo);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdClientList);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdClientSniff);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdBleMenu);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdBleList);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdLedMenu);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdAttackConfig);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdMacInput);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdBeaconMenu);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdBeaconSsidInput);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdApSsidInput);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdApPasswordInput);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdBeaconActive);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdCreateAp);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdEvilPortal);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdConsoleMenu);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdAdvancedMenu);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdConsoleOutput);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdConsoleSend);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdLog);
    view_dispatcher_remove_view(app->view_dispatcher, ViewIdAbout);

    widget_free(app->splash);
    menu_free(app->menu);
    loading_free(app->loading);
    submenu_free(app->network_list);
    widget_free(app->network_info);
    submenu_free(app->client_list);
    submenu_free(app->client_sniff);
    submenu_free(app->ble_menu);
    submenu_free(app->ble_list);
    submenu_free(app->led_menu);
    variable_item_list_free(app->attack_config);
    byte_input_free(app->mac_input);
    submenu_free(app->beacon_menu);
    text_input_free(app->text_input);
    widget_free(app->beacon_active);
    variable_item_list_free(app->create_ap);
    widget_free(app->evil_portal);
    submenu_free(app->console_menu);
    submenu_free(app->advanced_menu);
    text_box_free(app->log_view);
    popup_free(app->about_popup);

    view_dispatcher_free(app->view_dispatcher);
    furi_mutex_free(app->mutex);

    furi_record_close(RECORD_GUI);
    furi_record_close(RECORD_NOTIFICATION);
    furi_record_close(RECORD_STORAGE);

    furi_hal_power_disable_otg();
    expansion_enable(app->expansion);
    furi_record_close(RECORD_EXPANSION);

    free(app);
}

// ============================================================================
// Splash Screen
// ============================================================================

static void update_splash(App* app, const char* fw_status) {
    widget_reset(app->splash);

    // App name (FontPrimary, centered)
    widget_add_string_element(
        app->splash, 64, 4, AlignCenter, AlignTop, FontPrimary, "Gattrose-NG");

    // Codename (FontSecondary, centered)
    widget_add_string_element(
        app->splash, 64, 16, AlignCenter, AlignTop, FontSecondary, APP_CODENAME);

    // Version (FontSecondary, centered)
    static char version_str[32];
    snprintf(version_str, sizeof(version_str), "v%s", APP_VERSION);
    widget_add_string_element(
        app->splash, 64, 26, AlignCenter, AlignTop, FontSecondary, version_str);

    // Firmware status (FontSecondary, centered)
    strncpy(app->splash_fw_status, fw_status, sizeof(app->splash_fw_status) - 1);
    widget_add_string_element(
        app->splash, 64, 38, AlignCenter, AlignTop, FontSecondary, app->splash_fw_status);

    // Build date/time (FontSecondary, centered)
    static char build_str[32];
    snprintf(build_str, sizeof(build_str), "%s %s", APP_BUILD_DATE, APP_BUILD_TIME);
    widget_add_string_element(
        app->splash, 64, 50, AlignCenter, AlignTop, FontSecondary, build_str);
}

// ============================================================================
// Entry Point
// ============================================================================

int32_t gattrose_ng_app(void* p) {
    UNUSED(p);

    FURI_LOG_I(TAG, "Gattrose-NG v%s starting (built %s %s)", APP_VERSION, APP_BUILD_DATE, APP_BUILD_TIME);

    App* app = app_alloc();

    if(!app) {
        FURI_LOG_E(TAG, "Failed to allocate app");
        return -1;
    }

    // Show initial splash screen
    update_splash(app, "Initializing...");
    view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdSplash);

    // Subscribe to input events for early dismissal
    FuriPubSub* input_events = furi_record_open(RECORD_INPUT_EVENTS);
    FuriPubSubSubscription* input_subscription =
        furi_pubsub_subscribe(input_events, splash_input_callback, NULL);
    splash_action = SplashActionNone;

    // Small delay to let splash render
    furi_delay_ms(100);

    // Initialize UART and detect firmware
    update_splash(app, "Connecting to BW16...");
    furi_delay_ms(200);

    if(uart_init(app)) {
        update_splash(app, "Detecting firmware...");
        furi_delay_ms(300);

        // Run firmware detection
        detect_firmware(app);

        // Show detected firmware
        if(app->firmware_type != FirmwareUnknown) {
            snprintf(app->splash_fw_status, sizeof(app->splash_fw_status),
                "FW: %s", get_firmware_name(app));

            // Build capabilities string
            snprintf(app->splash_caps, sizeof(app->splash_caps), "%s%s%s%s",
                app->caps.wifi_scan_5ghz ? "5GHz " : "",
                app->caps.client_detection ? "CLI " : "",
                app->caps.ble_scan ? "BLE " : "",
                app->caps.targeted_deauth ? "TGT" : "");

            update_splash(app, app->splash_fw_status);
        } else {
            update_splash(app, "FW: Unknown");
        }
    } else {
        update_splash(app, "No device detected");
    }

    // Wait up to 2 seconds OR until user presses a key
    uint32_t start_tick = furi_get_tick();
    while(splash_action == SplashActionNone) {
        uint32_t elapsed = furi_get_tick() - start_tick;
        if(elapsed >= 2000) break;
        furi_delay_ms(10);
    }

    // Unsubscribe from input events
    furi_pubsub_unsubscribe(input_events, input_subscription);
    furi_record_close(RECORD_INPUT_EVENTS);

    // Wait for input cycle to complete
    furi_delay_ms(100);

    // Switch to main menu
    view_dispatcher_switch_to_view(app->view_dispatcher, ViewIdMenu);

    app_log(app, "Gattrose-NG v%s started", APP_VERSION);

    // Run main loop
    view_dispatcher_run(app->view_dispatcher);

    app_free(app);

    FURI_LOG_I(TAG, "Gattrose-NG stopped");
    return 0;
}
