#include <SoftwareSerial.h>
// for arduino ethernet board
#include <SPI.h>
#include <Ethernet.h>
#include <EthernetClient.h>
#include <EthernetServer.h>
#include <EthernetUdp.h>
#include <TimerOne.h>

#include <util.h>

SoftwareSerial debug(7,8);

#include "controller.h"
#include "protocol.h"

byte MAC[] = {0x90, 0xA2, 0xDA, 0x00, 0x6A, 0xAA};
byte  IP[] = {192, 168, 0, 24};
const unsigned int port = 35353;

Controller control;
Protocol protocol;
EthernetUDP u;
void setup(void) {
  debug.begin(115200);
  Serial.begin(1200);
  // 2 stop bits and odd parity
  UCSR0C |= 0b00111000;

  Timer1.stop();
  debug.println("RESTART");
  Timer1.resume();
  protocol.begin(MAC, IP, port, &control);
  control.begin();
}

void loop(void) {
  control.tick();
  protocol.tick();
}
