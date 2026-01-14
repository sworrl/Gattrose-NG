#ifndef DEBUG_H
#define DEBUG_H

// Uncomment to enable debug output on Serial (USB)
#define DEBUG

#ifdef DEBUG
    #define DEBUG_SER_PRINT(...) Serial.print(__VA_ARGS__)
    #define DEBUG_SER_PRINTLN(...) Serial.println(__VA_ARGS__)
#else
    #define DEBUG_SER_PRINT(...)
    #define DEBUG_SER_PRINTLN(...)
#endif

#endif
