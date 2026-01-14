#!/bin/bash
#
# Gattrose-NG Flipper App - Build Script
#
# Usage:
#   ./build_gattrose.sh                    # Build with cached/default firmware
#   ./build_gattrose.sh -d                 # Build and deploy to Flipper
#   ./build_gattrose.sh -f momentum -v dev # Specify firmware type and version
#   ./build_gattrose.sh -c                 # Clean build
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Defaults - Momentum dev
FIRMWARE_TYPE="momentum"
SELECTED_VERSION="dev"
AUTO_DEPLOY=false
CLEAN_BUILD=false

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--deploy) AUTO_DEPLOY=true; shift ;;
        -f|--firmware) FIRMWARE_TYPE="$2"; shift 2 ;;
        -v|--version) SELECTED_VERSION="$2"; shift 2 ;;
        -c|--clean) CLEAN_BUILD=true; shift ;;
        -h|--help)
            echo "Gattrose-NG Flipper Build Script"
            echo ""
            echo "Usage:"
            echo "  ./build_gattrose.sh              # Build with Momentum dev"
            echo "  ./build_gattrose.sh -d           # Build and deploy"
            echo "  ./build_gattrose.sh -c           # Clean build"
            echo ""
            echo "Flags:"
            echo "  -d, --deploy     Deploy to Flipper if mounted"
            echo "  -f, --firmware   Firmware type: momentum, unleashed, official"
            echo "  -v, --version    Version (e.g., dev, mntm-005)"
            echo "  -c, --clean      Clean build"
            exit 0
            ;;
        *) echo -e "${RED}Unknown: $1${NC}"; exit 1 ;;
    esac
done

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Gattrose-NG Flipper App Builder${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/flipper_build"
OUTPUT_DIR="$SCRIPT_DIR/output"
VERSION_FILE="$BUILD_DIR/.current_fw_version"
TYPE_FILE="$BUILD_DIR/.current_fw_type"

# Firmware repos
declare -A FIRMWARE_REPOS=(
    ["official"]="https://github.com/flipperdevices/flipperzero-firmware.git"
    ["momentum"]="https://github.com/Next-Flip/Momentum-Firmware.git"
    ["unleashed"]="https://github.com/DarkFlippers/unleashed-firmware.git"
)

echo -e "${CYAN}Configuration:${NC}"
echo "  Firmware: $FIRMWARE_TYPE @ $SELECTED_VERSION"
echo "  Build dir: $BUILD_DIR"
echo ""

# Create build dir
mkdir -p "$BUILD_DIR"

# Firmware directory
FIRMWARE_DIR="$BUILD_DIR/$FIRMWARE_TYPE-firmware"
FIRMWARE_REPO="${FIRMWARE_REPOS[$FIRMWARE_TYPE]}"

if [ -z "$FIRMWARE_REPO" ]; then
    echo -e "${RED}ERROR: Unknown firmware type: $FIRMWARE_TYPE${NC}"
    exit 1
fi

# Check if firmware needs download
NEEDS_DOWNLOAD=false

if [ -d "$FIRMWARE_DIR" ]; then
    if [ -f "$TYPE_FILE" ] && [ -f "$VERSION_FILE" ]; then
        CURRENT_TYPE=$(cat "$TYPE_FILE")
        CURRENT_VERSION=$(cat "$VERSION_FILE")

        if [ "$CURRENT_TYPE" == "$FIRMWARE_TYPE" ] && [ "$CURRENT_VERSION" == "$SELECTED_VERSION" ]; then
            echo -e "${GREEN}Firmware already cached!${NC}"
        else
            echo -e "${YELLOW}Firmware version mismatch, re-downloading...${NC}"
            NEEDS_DOWNLOAD=true
        fi
    else
        NEEDS_DOWNLOAD=true
    fi
else
    NEEDS_DOWNLOAD=true
fi

# Download firmware if needed
if [ "$NEEDS_DOWNLOAD" = true ]; then
    echo -e "${YELLOW}Downloading $FIRMWARE_TYPE firmware...${NC}"
    echo -e "${YELLOW}(This takes a while on first run)${NC}"

    if [ -d "$FIRMWARE_DIR" ]; then
        rm -rf "$FIRMWARE_DIR"
    fi

    git clone "$FIRMWARE_REPO" "$FIRMWARE_DIR"
    cd "$FIRMWARE_DIR"

    if [ "$SELECTED_VERSION" == "dev" ]; then
        git checkout dev
        git pull origin dev
    else
        git checkout "$SELECTED_VERSION"
    fi

    git submodule update --init --recursive

    echo "$SELECTED_VERSION" > "$VERSION_FILE"
    echo "$FIRMWARE_TYPE" > "$TYPE_FILE"

    echo -e "${GREEN}Firmware downloaded!${NC}"
fi

cd "$FIRMWARE_DIR"
echo ""

# Copy app to firmware
echo -e "${BLUE}Installing Gattrose-NG app...${NC}"

mkdir -p "$FIRMWARE_DIR/applications_user"

if [ -d "$FIRMWARE_DIR/applications_user/gattrose_ng" ]; then
    rm -rf "$FIRMWARE_DIR/applications_user/gattrose_ng"
fi

mkdir -p "$FIRMWARE_DIR/applications_user/gattrose_ng"

cp "$SCRIPT_DIR/gattrose_ng.c" "$FIRMWARE_DIR/applications_user/gattrose_ng/"
cp "$SCRIPT_DIR/application.fam" "$FIRMWARE_DIR/applications_user/gattrose_ng/"
cp "$SCRIPT_DIR/gattrose_10x10.png" "$FIRMWARE_DIR/applications_user/gattrose_ng/"

echo -e "${GREEN}App installed!${NC}"
echo ""

# Build
echo -e "${BLUE}Building Gattrose-NG FAP...${NC}"
echo ""

if [ "$CLEAN_BUILD" = true ]; then
    echo "Cleaning..."
    ./fbt -c fap_gattrose_ng 2>&1 || true
fi

./fbt fap_gattrose_ng 2>&1

BUILD_EXIT_CODE=$?

if [ $BUILD_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Build successful!${NC}"

# Find and copy output
mkdir -p "$OUTPUT_DIR"

FAP_FILE=$(find "$FIRMWARE_DIR/build" -name "gattrose_ng.fap" -type f 2>/dev/null | head -n 1)

if [ -z "$FAP_FILE" ]; then
    echo -e "${RED}ERROR: Cannot find gattrose_ng.fap in build output${NC}"
    find "$FIRMWARE_DIR/build" -name "*.fap" -type f 2>/dev/null || true
    exit 1
fi

cp "$FAP_FILE" "$OUTPUT_DIR/gattrose-ng.fap"
FAP_SIZE=$(du -h "$OUTPUT_DIR/gattrose-ng.fap" | cut -f1)

echo ""
echo -e "${GREEN}Output: $OUTPUT_DIR/gattrose-ng.fap ($FAP_SIZE)${NC}"

# Deploy if requested
if [ "$AUTO_DEPLOY" = true ]; then
    FLIPPER_PATH=""

    for path in /run/media/$USER/Flipper*/apps/GPIO /media/$USER/Flipper*/apps/GPIO /mnt/Flipper*/apps/GPIO; do
        if [ -d "$path" ]; then
            FLIPPER_PATH="$path"
            break
        fi
    done

    if [ -n "$FLIPPER_PATH" ]; then
        echo -e "${YELLOW}Deploying to Flipper at $FLIPPER_PATH...${NC}"
        cp "$OUTPUT_DIR/gattrose-ng.fap" "$FLIPPER_PATH/"
        sync
        echo -e "${GREEN}Deployed! Run: Apps -> GPIO -> Gattrose-NG${NC}"
    else
        echo -e "${YELLOW}Flipper not mounted, skipping deploy${NC}"
    fi
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  BUILD COMPLETE!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Output: $OUTPUT_DIR/gattrose-ng.fap"
echo ""
echo "To install manually:"
echo "  Copy to: SD:/apps/GPIO/gattrose-ng.fap"
echo ""
