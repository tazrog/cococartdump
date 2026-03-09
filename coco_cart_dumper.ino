/*
  TRS-80 Color Computer (CoCo) cartridge dumper for Arduino Mega 2560

  Serial protocol:
    Host -> Arduino: D <start_hex> <size_hex>\n
  Example:
    D C000 4000\n   (dump 16 KiB from CoCo address window C000-FFFF)

  Arduino -> Host:
    BEGIN <size_decimal>\n
    <size raw bytes>
    END\n
  Notes:
  - This targets simple ROM cartridges (8K/16K) using /CTS and /SCS.
  - It does not implement bank-switch register writes for advanced carts.
*/

#include <Arduino.h>

// Address bus A0..A15 on Mega digital pins 22..37
const uint8_t ADDR_PINS[16] = {
  22, 23, 24, 25, 26, 27, 28, 29,
  30, 31, 32, 33, 34, 35, 36, 37
};

// Data bus D0..D7 on Mega digital pins 38..45
const uint8_t DATA_PINS[8] = {38, 39, 40, 41, 42, 43, 44, 45};

// Control signals
const uint8_t PIN_RW  = 46;  // CoCo R/W (HIGH = read)
const uint8_t PIN_CTS = 47;  // CoCo /CTS (active LOW)
const uint8_t PIN_SCS = 48;  // CoCo /SCS (inactive HIGH)

const uint16_t DEFAULT_START = 0xC000;
const uint16_t DEFAULT_SIZE  = 0x4000; // 16 KiB
const uint8_t ADDRESS_SETUP_US = 2;    // Increase to 3..4 if reads are still unstable
const uint8_t STROBE_SETTLE_US = 2;    // Increase to 3..4 for slow edge wiring

static String tokenAt(const String &line, uint8_t index) {
  int start = 0;
  int n = 0;
  while (start < line.length()) {
    while (start < line.length() && line.charAt(start) == ' ') {
      start++;
    }
    if (start >= line.length()) {
      break;
    }
    int end = line.indexOf(' ', start);
    if (end < 0) {
      end = line.length();
    }
    if (n == index) {
      return line.substring(start, end);
    }
    n++;
    start = end + 1;
  }
  return String("");
}

static void setAddress(uint16_t addr) {
  for (uint8_t i = 0; i < 16; i++) {
    digitalWrite(ADDR_PINS[i], (addr >> i) & 0x01);
  }
}

static uint8_t readDataBus() {
  uint8_t v = 0;
  for (uint8_t i = 0; i < 8; i++) {
    if (digitalRead(DATA_PINS[i])) {
      v |= (1U << i);
    }
  }
  return v;
}

static uint8_t cartRead(uint16_t addr) {
  setAddress(addr);
  delayMicroseconds(ADDRESS_SETUP_US);
  bool upper8k = (addr & 0x2000U) != 0;
  // Keep /CTS asserted for all reads; assert /SCS on upper 8K.
  // Some carts require /CTS even when the upper half is selected.
  digitalWrite(PIN_CTS, LOW);
  if (upper8k) {
    digitalWrite(PIN_SCS, LOW);
  }
  delayMicroseconds(STROBE_SETTLE_US);
  uint8_t v = readDataBus();
  digitalWrite(PIN_CTS, HIGH);
  digitalWrite(PIN_SCS, HIGH);
  return v;
}

void setup() {
  for (uint8_t i = 0; i < 16; i++) {
    pinMode(ADDR_PINS[i], OUTPUT);
    digitalWrite(ADDR_PINS[i], LOW);
  }

  for (uint8_t i = 0; i < 8; i++) {
    pinMode(DATA_PINS[i], INPUT);
  }

  pinMode(PIN_RW, OUTPUT);
  pinMode(PIN_CTS, OUTPUT);
  pinMode(PIN_SCS, OUTPUT);

  digitalWrite(PIN_RW, HIGH);   // Read cycle
  digitalWrite(PIN_CTS, HIGH);  // Inactive
  digitalWrite(PIN_SCS, HIGH);  // Inactive

  Serial.begin(115200);
  while (!Serial) {
    ;
  }

  Serial.println(F("CoCo cartridge dumper ready."));
  Serial.println(F("Commands: D <start_hex> <size_hex>"));
}

void loop() {
  if (!Serial.available()) {
    return;
  }
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) {
    return;
  }
  char cmd = line.charAt(0);
  if (cmd != 'D') {
    return;
  }

  uint16_t startAddr = 0;
  uint16_t sizeBytes = 0;

  String startTok = tokenAt(line, 1);
  String sizeTok = tokenAt(line, 2);
  if (startTok.length() == 0 || sizeTok.length() == 0) {
    startAddr = DEFAULT_START;
    sizeBytes = DEFAULT_SIZE;
  } else {
    unsigned long s = strtoul(startTok.c_str(), nullptr, 16);
    unsigned long n = strtoul(sizeTok.c_str(), nullptr, 16);
    if (n == 0 || n > 0x4000UL) {
      n = DEFAULT_SIZE;
    }
    startAddr = (uint16_t)(s & 0xFFFFU);
    sizeBytes = (uint16_t)(n & 0xFFFFU);
  }
  Serial.print(F("BEGIN "));
  Serial.println(sizeBytes);

  for (uint32_t i = 0; i < sizeBytes; i++) {
    uint16_t addr = (uint16_t)(startAddr + i);
    uint8_t b = cartRead(addr);
    Serial.write(b);
  }

  Serial.println();
  Serial.println(F("END"));
}
