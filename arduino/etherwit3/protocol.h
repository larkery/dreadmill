#include "Arduino.h"

#define BUFFER_SIZE (5)

byte broadcast_address[] = {
  0xFF, 0xFF, 0xFF, 0xFF};
const unsigned int status_interval = 5000;//5s
const unsigned int ether_watch_time = 8000;//8s

class Protocol {
public:
  void begin(uint8_t *MAC, uint8_t *IP, const unsigned int p, Controller *c) {
    Ethernet.begin(MAC, IP);
    delay(1000);
    port = p;
    udp.begin(port);
    zero_buffer();
    control = c;
    send_status_packet();
  }

  void tick(void) {
    int packet_size = udp.parsePacket();
    if (packet_size) {
      e_stop_time = millis() + ether_watch_time;
      udp.read(buffer, BUFFER_SIZE);
      if ((buffer[0] == 'T') && (buffer[1] == 'C')) {
        switch (buffer[2]) {
        case 'h':
          control->set_target_speed(0);
          debug.println("Halting");
          break;
        case 's':
          control->set_target_speed(buffer[3]);
          debug.println("Speeding up:");
          debug.write((byte) 254);
          debug.write('b');
          debug.write((byte)16);
          debug.write((byte)0);
          break;
        case 'p':
        default:
          break;
        }

        send_status_packet();
        next_status_time = millis() + status_interval;
      }
    } else {
      if (control->get_current_speed()) {
        // check for ethernet death
        if (millis() > e_stop_time) {
          // we may have a problem
          // todo insert reset code.
          debug.println("Emergency stop");
//          debug.print(e_stop_time); debug.print('<'); debug.println(millis());
          speed_adjustment_interval *= 16;
          speed_adjustment_interval = 500;
          control->set_target_speed(0);
          while (control->get_current_speed()) {
            control->tick();
          }
          debug.println("Stopped");
          speed_adjustment_interval /= 16;
        }
      }
    }

    unsigned long time = millis();

    if (control->has_speed_just_changed() || (time >= next_status_time) ||
      ((unsigned long) (next_status_time - time) > status_interval))
    {
      send_status_packet();
      next_status_time = millis() + status_interval;
    }
  }

private:
  void send_status_packet() {
    buffer[0] = 'T';
    buffer[1] = 'S';
    buffer[2] = control->get_current_speed();
    buffer[3] = control->get_target_speed();

    udp.beginPacket(broadcast_address, port);
    udp.write(buffer, BUFFER_SIZE);
    udp.endPacket();
  }
  void zero_buffer() {
    for (byte i = 0; i<BUFFER_SIZE; i++) buffer[i] = 0;
  }

  unsigned int port;

  unsigned long next_status_time;
  unsigned long e_stop_time;
  byte buffer[BUFFER_SIZE];
  Controller *control;
  EthernetUDP udp;

};


