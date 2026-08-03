/**
 * SmartVision Bird Deterrence System - Microcontroller Controller
 * 
 * Sweeps pan/tilt servo coordinates in scanning patterns to survey the area.
 * Listens for serial triggers over 9600 baud:
 *   - "BIRD"  : Locked mode. Halts sweeping search and activates deterrent laser.
 *   - "CLEAR" : Scan mode. Deactivates deterrent laser and resumes sweeping search.
 */

#include <Servo.h>

// Physical Board Output Pins
const int PIN_SERVO_PAN  = 9;
const int PIN_SERVO_TILT = 10;
const int PIN_LASER_OUT  = 11;

// Motor Safety Angle Constraints
const int PAN_ANGLE_MIN  = 15;
const int PAN_ANGLE_MAX  = 165;
const int TILT_ANGLE_MIN = 90;
const int TILT_ANGLE_MAX = 135;

// Scanning Sweeper Resolution (Step Size)
const float VAL_PAN_STEP  = 0.6;
const float VAL_TILT_STEP = 0.3;

// Sweep Frame rate configurations (in milliseconds)
const unsigned long SWEEP_TICK_INTERVAL  = 75;
const unsigned long DETERRENT_HOLD_TIME  = 3000;

// Dynamic Sweep State variables
float currentPanAngle  = 90.0;
float currentTiltAngle = 90.0;
int panMoveDirection   = 1;
int tiltMoveDirection  = 1;

Servo panAxisServo;
Servo tiltAxisServo;

// Alarm Control State Machine
bool isTargetSpotted     = false;
bool isDeterrentLocked   = false;
unsigned long lockStartMillis  = 0;
unsigned long lastTickMillis   = 0;

void setup() {
  Serial.begin(9600);
  
  panAxisServo.attach(PIN_SERVO_PAN);
  tiltAxisServo.attach(PIN_SERVO_TILT);
  
  pinMode(PIN_LASER_OUT, OUTPUT);
  digitalWrite(PIN_LASER_OUT, LOW);
  
  // Set default initial tracking targets (Centered)
  panAxisServo.write(static_cast<int>(currentPanAngle));
  tiltAxisServo.write(static_cast<int>(currentTiltAngle));
  
  Serial.println("SYSTEM: CONTROLLER_BOOT_OK");
}

void loop() {
  const unsigned long currentMillis = millis();

  // 1. Process Hardware commands via PySerial Interface
  if (Serial.available() > 0) {
    String incomingCmd = Serial.readStringUntil('\n');
    incomingCmd.trim();

    if (incomingCmd == "BIRD") {
      isTargetSpotted = true;
      if (!isDeterrentLocked) {
        isDeterrentLocked = true;
        lockStartMillis = currentMillis;
        Serial.println("EVENT: DETERRENT_LOCKED");
      }
    } 
    else if (incomingCmd == "CLEAR") {
      isTargetSpotted = false;
      Serial.println("EVENT: STANDBY_TRIGGERED");
    }
  }

  // 2. State Machine Logic: Target Deterrence State
  if (isDeterrentLocked) {
    digitalWrite(PIN_LASER_OUT, HIGH);
    panAxisServo.write(static_cast<int>(currentPanAngle));
    tiltAxisServo.write(static_cast<int>(currentTiltAngle));

    if (currentMillis - lockStartMillis >= DETERRENT_HOLD_TIME) {
      if (isTargetSpotted) {
        lockStartMillis = currentMillis;  // Target still detected: extend lock window
      } else {
        isDeterrentLocked = false;
        digitalWrite(PIN_LASER_OUT, LOW);
        Serial.println("EVENT: DYNAMIC_SCAN_RESUMED");
      }
    }
    return; // Fast path: skip scanning calculations
  }

  // 3. State Machine Logic: Normal Searching/Sweeping State
  digitalWrite(PIN_LASER_OUT, LOW);

  if (currentMillis - lastTickMillis >= SWEEP_TICK_INTERVAL) {
    lastTickMillis = currentMillis;

    // Pan Axis Increments
    currentPanAngle += panMoveDirection * VAL_PAN_STEP;
    if (currentPanAngle >= PAN_ANGLE_MAX) {
      currentPanAngle = PAN_ANGLE_MAX;
      panMoveDirection = -1;
    } else if (currentPanAngle <= PAN_ANGLE_MIN) {
      currentPanAngle = PAN_ANGLE_MIN;
      panMoveDirection = 1;
    }

    // Tilt Axis Increments
    currentTiltAngle += tiltMoveDirection * VAL_TILT_STEP;
    if (currentTiltAngle >= TILT_ANGLE_MAX) {
      currentTiltAngle = TILT_ANGLE_MAX;
      tiltMoveDirection = -1;
    } else if (currentTiltAngle <= TILT_ANGLE_MIN) {
      currentTiltAngle = TILT_ANGLE_MIN;
      tiltMoveDirection = 1;
    }

    panAxisServo.write(static_cast<int>(currentPanAngle));
    tiltAxisServo.write(static_cast<int>(currentTiltAngle));
  }
}
