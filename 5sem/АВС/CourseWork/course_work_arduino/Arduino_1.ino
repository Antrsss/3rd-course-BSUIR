const int pinJoyX = A0;
const int pinJoyY = A1;
const int pinJoyBtn = 2;    // Спецатака
const int btn1Pin = 5;      // Выстрел
const int btn2Pin = 6;      // Аптечка

// Светодиоды
const int ledGreen = 3;     // Аптечка готова
const int ledBlue = 4;      // Спецатака

// Пищалка
const int buzzerGame = 10;

// Переменные для обнаружения отключения
unsigned long lastConnectionCheck = 0;
const unsigned long CONNECTION_CHECK_INTERVAL = 1000; // Проверка каждую секунду
bool wasDisconnected = false; // Флаг предыдущего состояния

// Переменные
String inputString = "";
bool stringComplete = false;
bool specialReady = true;
bool medkitReady = true;
bool hasMedkits = false;

void setup() {
  Serial.begin(9600);
  
  pinMode(pinJoyBtn, INPUT_PULLUP);
  pinMode(btn1Pin, INPUT_PULLUP);
  pinMode(btn2Pin, INPUT_PULLUP);
  
  pinMode(ledGreen, OUTPUT);
  pinMode(ledBlue, OUTPUT);
  
  pinMode(buzzerGame, OUTPUT);
}

void loop() {
  int joyX = analogRead(pinJoyX);
  int joyY = analogRead(pinJoyY);
  bool joyBtn = !digitalRead(pinJoyBtn);
  bool btn1 = !digitalRead(btn1Pin);
  bool btn2 = !digitalRead(btn2Pin);
  
  Serial.print(joyX);
  Serial.print(",");
  Serial.print(joyY);
  Serial.print(",");
  Serial.print(btn1);
  Serial.print(",");
  Serial.print(btn2); 
  Serial.print(",");
  Serial.println(joyBtn);
  
  // ПРОВЕРКА ОТКЛЮЧЕНИЯ ДЖОЙСТИКА
  checkJoystickDisconnection();
  
  if (stringComplete) {
    processCommand(inputString);
    inputString = "";
    stringComplete = false;
  }
  
  // Зеленый горит если аптечка готова И есть в инвентаре
  if (medkitReady && hasMedkits) {
    digitalWrite(ledGreen, (millis() / 500) % 2);
  } else {
    digitalWrite(ledGreen, LOW);
  }
  
  // Синий мигает если спецатака готова
  if (specialReady) {
    digitalWrite(ledBlue, (millis() / 700) % 2);
  } else {
    digitalWrite(ledBlue, LOW);
  }
  
  delay(50);
}

bool isJoystickDisconnected() {
  static int disconnectCount = 0;
  const int CONFIRM_COUNT = 3;
  
  int joyX = analogRead(pinJoyX);
  int joyY = analogRead(pinJoyY);
  
  bool currentlyDisconnected = (joyX <= 5 || joyX >= 1018) && 
                              (joyY <= 5 || joyY >= 1018);
  
  if (currentlyDisconnected) {
    disconnectCount++;
    if (disconnectCount >= CONFIRM_COUNT) {
      return true;
    }
  } else {
    disconnectCount = 0;
  }
  
  return false;
}

void checkJoystickDisconnection() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastConnectionCheck >= CONNECTION_CHECK_INTERVAL) {
    lastConnectionCheck = currentTime;
    
    bool isDisconnected = isJoystickDisconnected();
    
    if (isDisconnected && !wasDisconnected) {
      // Джойстик только что отключили
      tone(buzzerGame, 300, 2000); // Низкий длинный звук 2 секунды
      Serial.println("JOYSTICK_DISCONNECTED - Power cable removed!");
      wasDisconnected = true;
      
      // Визуальная индикация - мигаем светодиодами
      for (int i = 0; i < 3; i++) {
        digitalWrite(ledGreen, HIGH);
        digitalWrite(ledBlue, HIGH);
        delay(200);
        digitalWrite(ledGreen, LOW);
        digitalWrite(ledBlue, LOW);
        delay(200);
      }
    } 
    else if (!isDisconnected && wasDisconnected) {
      // Джойстик снова подключили
      tone(buzzerGame, 800, 300); // Короткий высокий звук
      Serial.println("JOYSTICK_RECONNECTED - Power cable connected!");
      wasDisconnected = false;
    }
    
    // Отладочная информация
    Serial.print("DISCONNECTION_CHECK: Disconnected=");
    Serial.println(isDisconnected);
  }
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}

void processCommand(String command) {
  command.trim();
  
  if (command == "FIRE") {
    tone(buzzerGame, 800, 100);
  }
  else if (command == "SPECIAL") {
    tone(buzzerGame, 1200, 300);
    specialReady = false;
  }
  else if (command == "SPECIAL_READY") {
    specialReady = true;
    tone(buzzerGame, 1500, 100);
  }
  else if (command == "MEDKIT") {
    tone(buzzerGame, 600, 200);
    medkitReady = false;
  }
  else if (command == "MEDKIT_READY") {
    medkitReady = true;
    tone(buzzerGame, 800, 150);
  }
  else if (command == "MEDKIT_GET") {
    hasMedkits = true;
    tone(buzzerGame, 1000, 100);
  }
  else if (command == "HEAL") {
    tone(buzzerGame, 700, 250);
  }
  else if (command == "HIT") {
    tone(buzzerGame, 1500, 150);
  }
  else if (command == "CRASH") {
    tone(buzzerGame, 150, 800);
  }
  else if (command == "NO_MEDKITS") {
    hasMedkits = false;
  }
}