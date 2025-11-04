

const int MQ3_PIN = A0;    // MQ-3 sensor analog output connected to A0
const int RELAY_PIN = 8;   // Relay input connected to digital pin 8
int sensorValue = 0;

void setup() {
  Serial.begin(9600);       // Serial communication with Raspberry Pi
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH); // Keep relay OFF (assuming active LOW)
  delay(2000);
  Serial.println("Alcohol Detection System Initialized");
}

void loop() {
  sensorValue = analogRead(MQ3_PIN);
  float voltage = (sensorValue / 1023.0) * 5.0;

  Serial.print("MQ3 Value: ");
  Serial.println(sensorValue);

  // --- Alcohol detection threshold ---
  if (sensorValue > 400) {  
    // Alcohol detected
    digitalWrite(RELAY_PIN, LOW);  // Activate relay (lock car or turn ON LED)
    Serial.println("ALCOHOL DETECTED");
  } else {
    // No alcohol
    digitalWrite(RELAY_PIN, HIGH); // Turn relay OFF
    Serial.println("SAFE - No Alcohol");
  }

  delay(1000); // Wait 1 second before next reading
}


