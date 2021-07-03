String p;
void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  delay(2000);
  Serial.write('+');
  delay(20);
  Serial.write('+'  );
  delay(20);
  Serial.write('+');
  delay(20);
}

void loop() {
  // put your main code here, to run repeatedly:
  if(Serial.available()){
    p = Serial.read();
    Serial.println(p);
  }
}
